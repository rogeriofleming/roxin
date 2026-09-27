# -*- coding: utf-8 -*-
"""Capas do Roxin.

Extrai a imagem embutida de cada musica de D:\Music e guarda uma miniatura
no cache (%LOCALAPPDATA%\Roxin\capas). O app le dali — nao mexe em tag nenhuma.

Rodar:  python capas.py            (so o que falta)
        python capas.py --forcar   (refaz tudo)
"""

import io, os, re, sys, hashlib

MUSICA = r"D:\Music"
LADO   = 512          # maior lado guardado: serve a lista, o rodape E a capa
                      # grande do modo "capa cheia". Imagem menor que isso e
                      # guardada como veio — ampliar no cache so borraria.


def pasta_cache():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    p = os.path.join(base, "Roxin", "capas")
    os.makedirs(p, exist_ok=True)
    return p


def chave(nome_arquivo):
    """Nome do arquivo de musica -> nome do arquivo de miniatura."""
    h = hashlib.md5(nome_arquivo.lower().encode("utf-8")).hexdigest()
    return h + ".png"


def arquivo_sem_capa():
    """Registro de quem JA foi verificado e nao tem imagem embutida."""
    return os.path.join(os.path.dirname(pasta_cache()), "sem_capa.json")


def _ler_sem_capa():
    try:
        import json
        with io.open(arquivo_sem_capa(), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _gravar_sem_capa(d):
    try:
        import json
        with io.open(arquivo_sem_capa(), "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception:
        pass          # e so cache: falhar aqui nao pode quebrar o app


def _carimbo(caminho):
    """mtime+tamanho: se o arquivo mudar, vale reverificar."""
    try:
        s = os.stat(caminho)
        return "%d:%d" % (int(s.st_mtime), s.st_size)
    except OSError:
        return ""


def quantas_no_cache():
    """Quantas miniaturas ja existem. Zero = maquina nova, precisa gerar."""
    try:
        return sum(1 for f in os.listdir(pasta_cache()) if f.endswith(".png"))
    except Exception:
        return 0


def imagem_embutida(caminho):
    """Bytes da imagem dentro da musica, ou None. Le ID3 APIC, MP4 covr e FLAC/OGG."""
    from mutagen import File as MF
    try:
        m = MF(caminho)
    except Exception:
        return None
    if m is None:
        return None
    tags = getattr(m, "tags", None)
    if tags is not None:
        try:
            for k in list(tags.keys()):
                if str(k).startswith("APIC"):
                    return bytes(tags[k].data)
            if "covr" in tags and tags["covr"]:
                return bytes(tags["covr"][0])
        except Exception:
            pass
    for p in (getattr(m, "pictures", None) or []):
        return bytes(p.data)
    return None


def gerar(forcar=False, quieto=False):
    """Gera as miniaturas que faltam. Devolve (com_capa, sem_capa, erros)."""
    from PySide6.QtGui import QImage
    from PySide6.QtCore import Qt

    cache = pasta_cache()
    com = sem = erro = pulou = 0
    # quem ja foi verificado e nao tem imagem embutida nao precisa ser relido
    registro = {} if forcar else _ler_sem_capa()
    mexeu = False
    for nome in sorted(os.listdir(MUSICA)):
        if os.path.splitext(nome)[1].lower() not in (".mp3", ".m4a"):
            continue
        destino = os.path.join(cache, chave(nome))
        if os.path.exists(destino) and not forcar:
            if nome.lower() in registro:
                registro.pop(nome.lower(), None)   # ganhou capa: sai do registro
                mexeu = True
            pulou += 1; com += 1
            continue
        caminho = os.path.join(MUSICA, nome)
        marca = registro.get(nome.lower())
        if marca and marca == _carimbo(caminho):
            sem += 1          # sem capa, e ja sabiamos: nao abre o arquivo
            continue
        dados = imagem_embutida(caminho)
        if not dados:
            registro[nome.lower()] = _carimbo(caminho)
            mexeu = True
            sem += 1
            continue
        if nome.lower() in registro:
            registro.pop(nome.lower(), None)   # ganhou capa: sai do registro
            mexeu = True
        img = QImage()
        if not img.loadFromData(dados):
            erro += 1
            if not quieto: print("  imagem ilegivel:", nome[:60])
            continue
        # cabe dentro de LADO x LADO mantendo a proporcao — nada de cortar.
        # So REDUZ: ampliar aqui nao cria detalhe, so peso e borrao.
        if img.width() > LADO or img.height() > LADO:
            img = img.scaled(LADO, LADO, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if img.save(destino, "PNG"):
            com += 1
        else:
            erro += 1
    if mexeu:
        _gravar_sem_capa(registro)
    if not quieto:
        print("cache: %s" % cache)
        print("com capa: %d (%d ja estavam)  |  sem capa: %d  |  ilegiveis: %d"
              % (com, pulou, sem, erro))
    return com, sem, erro


# ─────────────────────────────────────────── capa de quem veio do YouTube ──
# Musica baixada pelo Anzol nasce SEM imagem embutida: o yt-dlp so guarda a
# miniatura se mandarem, e o motor nao manda. Mas o nome do arquivo termina em
# `[<id>]`, e com o id a miniatura se busca direto. Aqui ela e CORTADA em
# quadrado (decisao do Roger em 24/09/2026): a moldura do app nao corta nada, e
# uma imagem 16:9 inteira ficaria com faixa vazia no meio das capas quadradas.
# Nada disso toca no arquivo de musica -- so escreve no cache de miniaturas.

#: `... [dQw4w9WgXcQ].m4a` -> o id. 11 caracteres e o formato do YouTube; de
#: outro site o sufixo nao casa, e ai nem se tenta.
RX_ID = re.compile(r"\[([A-Za-z0-9_-]{11})\]\.[^.]+$")

#: da maior para a menor. `maxres` e 1280x720 limpo mas nem todo video tem;
#: `mq` e 320x180, pequeno porem TAMBEM sem as tarjas pretas que `hq` e `sd`
#: trazem (elas virariam borda preta dentro da capa).
THUMBS = ("https://i.ytimg.com/vi/%s/maxresdefault.jpg",
          "https://i.ytimg.com/vi/%s/mqdefault.jpg")


def id_no_nome(nome_arquivo):
    m = RX_ID.search(nome_arquivo)
    return m.group(1) if m else None


def baixar_thumb(vid, timeout=12):
    """Bytes da melhor miniatura que existir, ou None. So leitura, sem chave."""
    import urllib.request, urllib.error
    for molde in THUMBS:
        try:
            req = urllib.request.Request(molde % vid, headers={"User-Agent": "Roxin"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if r.status == 200:
                    dados = r.read()
                    if len(dados) > 1024:      # 404 do ytimg vem como imagem minuscula
                        return dados
        except Exception:
            continue
    return None


def quadrado(dados, lado=LADO):
    """QImage quadrada, cortada do CENTRO. None se a imagem nao for legivel."""
    from PySide6.QtGui import QImage
    from PySide6.QtCore import Qt
    img = QImage()
    if not img.loadFromData(dados):
        return None
    l = min(img.width(), img.height())
    img = img.copy((img.width() - l) // 2, (img.height() - l) // 2, l, l)
    if img.width() > lado:
        img = img.scaled(lado, lado, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return img


def capa_do_youtube(nome_arquivo, forcar=False):
    """Poe no cache a capa da musica baixada do YouTube. True se gravou agora.

    Nao mexe no arquivo de musica. Quem ja tem capa (embutida ou aprovada) fica
    como esta, a nao ser com forcar=True.
    """
    destino = os.path.join(pasta_cache(), chave(nome_arquivo))
    if os.path.exists(destino) and not forcar:
        return False
    vid = id_no_nome(nome_arquivo)
    if not vid:
        return False
    dados = baixar_thumb(vid)
    if not dados:
        return False
    img = quadrado(dados)
    return bool(img and img.save(destino, "PNG"))


def varrer_youtube(forcar=False, quieto=False):
    """Passa em tudo que esta sem capa e tenta pelo id do nome."""
    feitas = tentadas = 0
    for nome in sorted(os.listdir(MUSICA)):
        if os.path.splitext(nome)[1].lower() not in (".mp3", ".m4a"):
            continue
        if not id_no_nome(nome):
            continue
        if os.path.exists(os.path.join(pasta_cache(), chave(nome))) and not forcar:
            continue
        tentadas += 1
        if capa_do_youtube(nome, forcar):
            feitas += 1
            if not quieto:
                print("  capa:", nome[:70])
        elif not quieto:
            print("  sem miniatura:", nome[:70])
    if not quieto:
        print("tentadas: %d  |  gravadas: %d" % (tentadas, feitas))
    return feitas, tentadas


# ---------------------------------------------------------------- acervo antigo
# O que o Anzol baixa hoje traz o id no NOME (`[<id>].mp3`), e `id_no_nome` acha.
# O acervo antigo do Roger -- baixado entre 2015 e 2018 por conversores de site --
# nao tem id no nome, mas guardou a URL da miniatura DENTRO da tag ID3
# (`WXXX:MP3-META Front Cover URL` = i1.ytimg.com/vi/<id>/default.jpg, e as vezes
# `WXXX:M3P-META Referrer URL` = youtu.be/<id>). Dai sai o mesmo id, 11 anos depois
# e depois de o arquivo ter passado por celular, dois notebooks e dois HDs.
#
# Isso importa porque a imagem que esses conversores EMBUTIRAM e a miniatura
# pequena -- tipicamente 400x225, 16:9, com tarja preta -- enquanto o YouTube ainda
# serve `maxresdefault` (1280x720) para o mesmo video. Medido em 25/09/2026: 487
# capas do acervo estavam abaixo de 512px.
RX_ID_TAG = re.compile(r"(?:ytimg\.com/vi/|youtu\.be/|watch\?v=)([A-Za-z0-9_-]{11})")


def id_nas_tags(caminho):
    """Id do video do YouTube guardado nas tags do arquivo, ou None."""
    from mutagen import File as MF
    try:
        m = MF(caminho)
    except Exception:
        return None
    if m is None or not getattr(m, "tags", None):
        return None
    try:
        blob = " ".join(str(v) for v in dict(m.tags).values())
    except Exception:
        return None
    achou = RX_ID_TAG.search(blob)
    return achou.group(1) if achou else None


def id_do_video(caminho):
    """Id pelo nome do arquivo; se nao houver, pelas tags."""
    return id_no_nome(os.path.basename(caminho)) or id_nas_tags(caminho)


def lado_no_cache(nome_arquivo):
    """Lado (px) da miniatura ja guardada, ou 0 se nao houver."""
    from PySide6.QtGui import QImage
    p = os.path.join(pasta_cache(), chave(nome_arquivo))
    if not os.path.exists(p):
        return 0
    img = QImage(p)
    return 0 if img.isNull() else img.width()


def encaixado(dados, lado=LADO):
    """QImage reduzida para caber em `lado` x `lado`, SEM cortar -- a mesma
    normalizacao que `gerar()` faz com a imagem embutida."""
    from PySide6.QtGui import QImage
    from PySide6.QtCore import Qt
    img = QImage()
    if not img.loadFromData(dados):
        return None
    if img.width() > lado or img.height() > lado:
        img = img.scaled(lado, lado, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return img


def melhorar_capa(nome_arquivo, quieto=True):
    """Troca a miniatura pela do YouTube SE a nova for maior. Devolve
    (trocou, lado_antigo, lado_novo).

    Duas travas, as duas pagas com erro visto na tela:

    1. `if novo > velho` -- quando o video nao tem `maxresdefault`, cai-se em
       `mqdefault` (320x180), que e MENOR que a imagem de 400x225 embutida:
       trocar ali pioraria a capa.
    2. **Quem ja tinha capa NAO tem o enquadramento mexido.** A imagem entra
       `encaixado`, nao `quadrado`. Cortar o centro de uma miniatura 16:9
       decepa o texto que quase toda capa de lyric video tem -- na primeira
       versao disto, "You Are Loved" virou "ou Are Love" e "LALALA" virou
       "ALAL". So quem NAO tinha capa nenhuma recebe o corte quadrado, que e a
       regra do Roger de 24/09/2026 para capa buscada na web.
    """
    caminho = os.path.join(MUSICA, nome_arquivo)
    vid = id_do_video(caminho)
    if not vid:
        return False, 0, 0
    velho = lado_no_cache(nome_arquivo)
    dados = baixar_thumb(vid)
    if not dados:
        return False, velho, 0
    img = quadrado(dados) if velho == 0 else encaixado(dados)
    if img is None:
        return False, velho, 0
    novo = img.width()
    if novo <= velho:
        return False, velho, novo
    destino = os.path.join(pasta_cache(), chave(nome_arquivo))
    return bool(img.save(destino, "PNG")), velho, novo


def varrer_acervo_antigo(quieto=False, so_listar=False):
    """Passa no acervo inteiro e melhora a capa de quem tem id (nome ou tags)."""
    from PySide6.QtGui import QImage           # noqa: F401  (garante o Qt carregado)
    trocadas = tentadas = mantidas = sem_id = 0
    for nome in sorted(os.listdir(MUSICA)):
        if os.path.splitext(nome)[1].lower() not in (".mp3", ".m4a"):
            continue
        if not id_do_video(os.path.join(MUSICA, nome)):
            sem_id += 1
            continue
        tentadas += 1
        if so_listar:
            continue
        trocou, velho, novo = melhorar_capa(nome)
        if trocou:
            trocadas += 1
            if not quieto:
                print("  %4d -> %4d  %s" % (velho, novo, nome[:66]))
        else:
            mantidas += 1
    if not quieto:
        print("\ncom id de video: %d  |  sem id: %d" % (tentadas, sem_id))
        print("capas TROCADAS por uma maior: %d  |  mantidas como estavam: %d"
              % (trocadas, mantidas))
    return trocadas, tentadas


def backups_do_cache():
    """Copias do cache guardadas antes de cada rodada, da mais nova para a mais velha."""
    base = os.path.dirname(pasta_cache())
    try:
        nomes = [d for d in os.listdir(base) if d.startswith("capas_backup_")]
    except Exception:
        return []
    return [os.path.join(base, d) for d in sorted(nomes, reverse=True)]


def restaurar(filtro=None, quieto=False):
    """Poe de volta a capa que estava no backup mais recente.

    `filtro` = pedaco do nome do arquivo de musica (sem acento nao vale, e o
    nome como esta no disco). Sem filtro, restaura TUDO.
    Serve para desfazer uma troca que nao agradou: a miniatura antiga continua
    guardada, entao nenhuma decisao aqui e definitiva.
    """
    import shutil
    bks = backups_do_cache()
    if not bks:
        if not quieto:
            print("nao ha copia de seguranca do cache.")
        return 0
    bkp, cache, postas = bks[0], pasta_cache(), 0
    for nome in sorted(os.listdir(MUSICA)):
        if os.path.splitext(nome)[1].lower() not in (".mp3", ".m4a"):
            continue
        if filtro and filtro.lower() not in nome.lower():
            continue
        k = chave(nome)
        de = os.path.join(bkp, k)
        if not os.path.exists(de):
            continue
        shutil.copy2(de, os.path.join(cache, k))
        postas += 1
        if not quieto and filtro:
            print("  voltou:", nome[:70])
    if not quieto:
        print("restauradas do backup %s: %d capas" % (os.path.basename(bkp), postas))
    return postas


if __name__ == "__main__":
    if "--restaurar" in sys.argv:
        i = sys.argv.index("--restaurar")
        alvo = sys.argv[i + 1] if len(sys.argv) > i + 1 else None
        restaurar(alvo)
    elif "--acervo-antigo" in sys.argv:
        from PySide6.QtWidgets import QApplication   # QImage precisa do app
        QApplication([])
        varrer_acervo_antigo(so_listar="--listar" in sys.argv)
    elif "--youtube" in sys.argv:
        from PySide6.QtWidgets import QApplication
        QApplication([])
        varrer_youtube(forcar="--forcar" in sys.argv)
    else:
        gerar(forcar="--forcar" in sys.argv)
