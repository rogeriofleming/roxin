"""Anzol — o motor.

Tudo que não é HTTP mora aqui: a fila de trabalhos em memória, a conversa com o
yt-dlp e a tradução dos erros dele para português. As funções puras (formatação,
tradução, escolha do arquivo final) não tocam disco nem rede — são as testadas.
"""
from __future__ import annotations

import re
import shutil
import sys
import threading
import time
import uuid
from pathlib import Path

import yt_dlp

# ─────────────────────────────────────────────────────────── configuração ────


def _empacotado() -> bool:
    """True quando rodando como .exe do PyInstaller."""
    return getattr(sys, "frozen", False)


def _base_dir() -> Path:
    # Empacotado, `__file__` aponta para a pasta temporaria que o PyInstaller
    # extrai (_MEIPASS) — que some ao fechar o app. A pasta do executavel e a
    # unica estavel.
    if _empacotado():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _downloads_dir() -> Path:
    # No .exe os arquivos vao pra pasta do usuario: instalacao e coisa baixada
    # nao se misturam, e o Roger acha o video onde ele espera achar.
    # Rodando do codigo, mantem o comportamento original (./downloads).
    if _empacotado():
        return Path.home() / "Downloads" / "Anzol"
    return _base_dir() / "downloads"


BASE_DIR = _base_dir()
DOWNLOADS_DIR = _downloads_dir()

#: quanto tempo um trabalho terminado fica na memória antes de ser esquecido
VALIDADE_JOB_S = 30 * 60

#: o que cada opção da interface pede ao yt-dlp
MODOS: dict[str, dict] = {
    "video": {
        "rotulo": "Vídeo — melhor qualidade",
        "format": "bestvideo*+bestaudio/best",
        "merge_output_format": "mp4",
    },
    "video1080": {
        "rotulo": "Vídeo — até 1080p",
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "merge_output_format": "mp4",
    },
    "video720": {
        "rotulo": "Vídeo — até 720p",
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "merge_output_format": "mp4",
    },
    "video480": {
        "rotulo": "Vídeo — até 480p (leve)",
        "format": "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "merge_output_format": "mp4",
    },
    "mp3": {
        "rotulo": "Áudio — MP3 192kbps",
        "format": "bestaudio/best",
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ],
    },
    "m4a": {
        "rotulo": "Áudio — original, sem reconverter",
        "format": "bestaudio[ext=m4a]/bestaudio/best",
    },
}

#: modos que só entregam arquivo com o ffmpeg no PATH
MODOS_COM_FFMPEG = frozenset({"video", "video1080", "video720", "video480", "mp3"})


class CanceladoPeloUsuario(Exception):
    """Levantada dentro do gancho de progresso para abortar o download."""


# ──────────────────────────────────────────────────── funções puras (teste) ──

def formatar_bytes(n: float | None) -> str:
    """1536 → '1,5 KB'. Vazio quando o tamanho é desconhecido."""
    if not n or n < 0:
        return ""
    unidades = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    valor = float(n)
    while valor >= 1024 and i < len(unidades) - 1:
        valor /= 1024
        i += 1
    casas = 0 if i == 0 else 1
    return f"{valor:.{casas}f}".replace(".", ",") + f" {unidades[i]}"


def formatar_duracao(segundos: float | None) -> str:
    """3672 → '1:01:12'. Vazio quando não há duração (ao vivo, por exemplo)."""
    if not segundos or segundos < 0:
        return ""
    segundos = int(segundos)
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


#: erro cru do yt-dlp → frase que explica o que aconteceu
_TRADUCOES: tuple[tuple[str, str], ...] = (
    ("private video", "Vídeo privado — só quem tem convite do canal consegue baixar."),
    ("members-only", "Vídeo exclusivo para membros do canal."),
    ("sign in to confirm your age", "Vídeo com restrição de idade: o site exige login."),
    ("sign in to confirm", "O site pediu login para liberar este vídeo."),
    ("confirm you're not a bot", "O site pediu confirmação de que você não é um robô."),
    ("unavailable", "Vídeo indisponível — foi removido, ficou privado ou nunca existiu."),
    ("this video has been removed", "Vídeo removido pelo autor ou pelo site."),
    # o YouTube diz "The uploader has not made this video available in your country"
    ("available in your country", "Vídeo bloqueado no seu país."),
    ("geo restricted", "Vídeo bloqueado na sua região."),
    ("is not a valid url", "Isso não parece um link. Cole o endereço completo, com https://."),
    ("unsupported url", "Não conheço esse site — o yt-dlp não tem extrator para ele."),
    ("live event will begin", "A transmissão ainda não começou."),
    ("is live", "Transmissão ao vivo em andamento: espere terminar para baixar."),
    ("requested format is not available",
     "Essa qualidade não existe neste vídeo. Tente 'melhor qualidade'."),
    ("ffmpeg", "Faltou o ffmpeg. Instale e deixe no PATH para juntar vídeo e áudio."),
    ("unable to download webpage", "Não consegui abrir a página. Cheque a internet ou o link."),
    ("name or service not known", "Sem internet, ou o endereço do site não resolve."),
    ("timed out", "O site demorou demais para responder. Tente de novo."),
    ("http error 404", "Página não encontrada (404). O link provavelmente está errado."),
    ("http error 403", "O site recusou o acesso (403). Pode exigir login."),
    ("http error 429", "O site pediu para desacelerar (429). Espere alguns minutos."),
)


def traduzir_erro(bruto: str) -> str:
    """Transforma a mensagem técnica do yt-dlp numa frase útil em português.

    O que não está na tabela volta limpo: sem o prefixo `ERROR:` e sem os códigos
    de cor do terminal, que o yt-dlp injeta mesmo em modo silencioso.
    """
    texto = re.sub(r"\x1b\[[0-9;]*m", "", bruto or "").strip()
    texto = re.sub(r"^ERROR:\s*", "", texto, flags=re.IGNORECASE).strip()
    # `[youtube] BaW_jenozKc: This video is unavailable` → tira extrator e id
    texto = re.sub(r"^\[[\w.:-]+\]\s*", "", texto)
    texto = re.sub(r"^[\w-]{6,}:\s+", "", texto).strip()
    baixo = texto.lower()
    for agulha, frase in _TRADUCOES:
        if agulha in baixo:
            return frase
    return texto or "Falhou sem dizer por quê."


def arquivos_finais(info: dict) -> list[str]:
    """Os caminhos que o yt-dlp de fato entregou, na ordem em que baixou.

    Existe porque adivinhar pelo nome não funciona: num merge o yt-dlp deixa
    `<id>.f251.webm` e `<id>.f616.mp4` ao lado do `.mp4` final, e um `glob()`
    pode devolver o fragmento em vez do vídeo. O `requested_downloads` é a
    resposta do próprio yt-dlp sobre o que ficou pronto.
    """
    caminhos: list[str] = []

    def coletar(no: dict) -> None:
        for pedido in no.get("requested_downloads") or []:
            caminho = pedido.get("filepath") or pedido.get("_filename")
            if caminho:
                caminhos.append(caminho)
        for filho in no.get("entries") or []:
            if isinstance(filho, dict):
                coletar(filho)

    coletar(info or {})
    return caminhos


def eh_fragmento(nome: str) -> bool:
    """Sobra de download: fragmento de formato, `.part`, `.temp`, cache do ytdl."""
    baixo = nome.lower()
    return bool(
        re.search(r"\.f\d+\.[a-z0-9]+$", baixo)
        or re.search(r"\.(part|ytdl|temp)$", baixo)
        or ".temp." in baixo
        or ".part-" in baixo
    )


def nome_seguro(nome: str) -> str | None:
    """Devolve o nome se for um arquivo simples dentro de `downloads/`, senão None.

    Barra `..`, barras e caminho absoluto: quem chama usa isso antes de apagar.
    """
    nome = (nome or "").strip()
    if not nome or nome in (".", ".."):
        return None
    if "/" in nome or "\\" in nome or ":" in nome:
        return None
    return nome


def ffmpeg_disponivel() -> bool:
    return shutil.which("ffmpeg") is not None


# ────────────────────────────────────────────────────────────── os trabalhos ──

_JOBS: dict[str, dict] = {}
_CANCELADOS: set[str] = set()
_TRAVA = threading.Lock()


def _agora() -> float:
    return time.monotonic()


def _limpar_jobs_vencidos() -> None:
    """Esquece trabalhos terminados há mais de meia hora (chamar já com a trava)."""
    limite = _agora() - VALIDADE_JOB_S
    vencidos = [
        i for i, j in _JOBS.items()
        if j["terminou_em"] is not None and j["terminou_em"] < limite
    ]
    for i in vencidos:
        _JOBS.pop(i, None)
        _CANCELADOS.discard(i)


def criar_job(url: str, modo: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _TRAVA:
        _limpar_jobs_vencidos()
        _JOBS[job_id] = {
            "id": job_id,
            "url": url,
            "modo": modo,
            "status": "iniciando",
            "pct": 0.0,
            "titulo": None,
            "velocidade": None,
            "eta": None,
            "baixado": None,
            "total": None,
            "item": None,
            "itens": None,
            "arquivos": [],
            "erro": None,
            "terminou_em": None,
        }
    return job_id


def ler_job(job_id: str) -> dict | None:
    with _TRAVA:
        job = _JOBS.get(job_id)
        return dict(job) if job else None


def cancelar_job(job_id: str) -> bool:
    """Marca o trabalho para parar. False se ele já tinha terminado."""
    with _TRAVA:
        job = _JOBS.get(job_id)
        if not job or job["terminou_em"] is not None:
            return False
        _CANCELADOS.add(job_id)
        job["status"] = "cancelando"
    return True


def _atualizar(job_id: str, **campos) -> None:
    with _TRAVA:
        job = _JOBS.get(job_id)
        if job:
            job.update(campos)


def _gancho_progresso(job_id: str):
    def gancho(d: dict) -> None:
        with _TRAVA:
            if job_id in _CANCELADOS:
                raise CanceladoPeloUsuario
            job = _JOBS.get(job_id)
            if not job:
                return
            info = d.get("info_dict") or {}
            job["titulo"] = job["titulo"] or info.get("title")
            job["item"] = info.get("playlist_index") or job["item"]
            job["itens"] = info.get("n_entries") or info.get("playlist_count") or job["itens"]

            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                baixado = d.get("downloaded_bytes") or 0
                job["status"] = "baixando"
                job["baixado"] = baixado
                job["total"] = total
                job["velocidade"] = d.get("speed")
                job["eta"] = d.get("eta")
                if total:
                    job["pct"] = round(100 * baixado / total, 1)
            elif d["status"] == "finished":
                job["status"] = "processando"
                job["pct"] = 100.0
                job["velocidade"] = None
                job["eta"] = None

    return gancho


def _opcoes(job_id: str, modo: str, playlist: bool, pasta: Path) -> dict:
    receita = MODOS[modo]
    miolo = (
        "%(playlist_index&{} - |)s%(title).120s [%(id)s].%(ext)s"
        if playlist
        else "%(title).120s [%(id)s].%(ext)s"
    )
    opts = {
        "outtmpl": str(pasta / f"{job_id}.{miolo}"),
        "progress_hooks": [_gancho_progresso(job_id)],
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": not playlist,
        "ignoreerrors": playlist,  # numa playlist, um item quebrado não derruba o resto
        "retries": 5,
        "fragment_retries": 5,
        "windowsfilenames": True,
        "format": receita["format"],
    }
    if "merge_output_format" in receita:
        opts["merge_output_format"] = receita["merge_output_format"]
    if "postprocessors" in receita:
        opts["postprocessors"] = [dict(p) for p in receita["postprocessors"]]
    return opts


def _sem_prefixo(caminho: Path, job_id: str) -> Path:
    """Tira o `<job_id>.` do nome, achando um livre se já existir igual.

    O prefixo serve durante o download — é ele que deixa a varredura de sobras
    saber o que é deste trabalho e o que é de outro. Depois só atrapalha quem
    abre a pasta, então some.
    """
    if not caminho.name.startswith(f"{job_id}."):
        return caminho

    limpo = caminho.name[len(job_id) + 1:]
    alvo = caminho.with_name(limpo)
    if not alvo.exists():
        return alvo

    tronco, sufixo = alvo.stem, alvo.suffix
    for n in range(2, 1000):
        tentativa = alvo.with_name(f"{tronco} ({n}){sufixo}")
        if not tentativa.exists():
            return tentativa
    return caminho  # mil arquivos com o mesmo nome: desiste e mantém o prefixo


def _varrer_sobras(pasta: Path, job_id: str, guardar: set[str]) -> None:
    """Apaga fragmentos deste trabalho. Nunca toca em arquivo de outro job."""
    for caminho in pasta.glob(f"{job_id}.*"):
        if caminho.name in guardar or not caminho.is_file():
            continue
        if eh_fragmento(caminho.name):
            caminho.unlink(missing_ok=True)


def extrair_info(url: str) -> dict:
    """Prévia do link: título, duração, miniatura e se é uma playlist."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError("O site não devolveu nada sobre esse link.")

    playlist = None
    if info.get("_type") == "playlist" or "entries" in info:
        itens = [e for e in (info.get("entries") or []) if e]
        if not itens:
            raise ValueError("Playlist vazia — nenhum vídeo disponível nela.")
        playlist = {"titulo": info.get("title") or "(playlist sem nome)", "total": len(itens)}
        primeiro = itens[0]
        # com extract_flat o item vem raso: busca o completo só do primeiro, pra prévia
        if not primeiro.get("thumbnail") and primeiro.get("url"):
            try:
                with yt_dlp.YoutubeDL(
                    {"quiet": True, "no_warnings": True, "skip_download": True}
                ) as ydl2:
                    primeiro = ydl2.extract_info(primeiro["url"], download=False) or primeiro
            except Exception:  # noqa: BLE001 — prévia é enfeite, não derruba a busca
                pass
        info = primeiro

    return {
        "titulo": info.get("title") or "(sem título)",
        "duracao": info.get("duration"),
        "miniatura": info.get("thumbnail"),
        "site": info.get("extractor_key") or info.get("ie_key"),
        "aoVivo": bool(info.get("is_live")),
        "playlist": playlist,
    }


def rodar_download(
    job_id: str, url: str, modo: str, playlist: bool, pasta: Path | None = None
) -> None:
    """Baixa de verdade. Roda numa thread e escreve o resultado no job."""
    pasta = pasta or DOWNLOADS_DIR
    pasta.mkdir(parents=True, exist_ok=True)
    try:
        with yt_dlp.YoutubeDL(_opcoes(job_id, modo, playlist, pasta)) as ydl:
            info = ydl.extract_info(url, download=True)

        entregues = [Path(p) for p in arquivos_finais(info or {})]
        existentes = [p for p in entregues if p.exists()]
        _varrer_sobras(pasta, job_id, {p.name for p in existentes})

        if not existentes:
            _atualizar(
                job_id,
                status="erro",
                erro="O download terminou mas nenhum arquivo ficou pronto. "
                     "Numa playlist, isso quer dizer que todos os itens falharam.",
                terminou_em=_agora(),
            )
            return

        finais = []
        for p in existentes:
            destino = _sem_prefixo(p, job_id)
            if destino != p:
                p.rename(destino)
            finais.append(destino)

        _atualizar(
            job_id,
            status="concluido",
            pct=100.0,
            velocidade=None,
            eta=None,
            arquivos=[{"nome": p.name, "tamanho": p.stat().st_size} for p in finais],
            terminou_em=_agora(),
        )
    except CanceladoPeloUsuario:
        _varrer_sobras(pasta, job_id, set())
        _atualizar(job_id, status="cancelado", erro=None, terminou_em=_agora())
    except Exception as exc:  # noqa: BLE001 — qualquer falha do yt-dlp vira recado ao usuário
        if job_id in _CANCELADOS:  # o yt-dlp embrulha a exceção que veio do gancho
            _varrer_sobras(pasta, job_id, set())
            _atualizar(job_id, status="cancelado", erro=None, terminou_em=_agora())
        else:
            _atualizar(job_id, status="erro", erro=traduzir_erro(str(exc)), terminou_em=_agora())


def iniciar_download(url: str, modo: str, playlist: bool = False) -> str:
    job_id = criar_job(url, modo)
    threading.Thread(
        target=rodar_download, args=(job_id, url, modo, playlist), daemon=True
    ).start()
    return job_id
