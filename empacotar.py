# -*- coding: utf-8 -*-
"""Empacota playlists do Roxin num arquivo .zip que o celular entende.

    python empacotar.py --listar
    python empacotar.py "Ghibli melhores"
    python empacotar.py "Ghibli melhores" "Lofi favoritas" --saida D:\\pacotes
    python empacotar.py --conferir pacotes/Roxin_Ghibli-melhores.zip

POR QUE ISTO EXISTE
-------------------
As playlists .m3u guardam CAMINHO ABSOLUTO do PC (`D:\\Music\\...`). No celular esse
caminho nao existe, entao a playlist chegaria vazia. Este script traduz o acervo num
indice de caminho RELATIVO (`roxin.json`) e junta, no mesmo arquivo, as musicas, as
capas e as duracoes -- tudo que o app precisa e nada que ele tenha de adivinhar.

POR QUE .zip E NAO PASTA
------------------------
O app do Google Drive no Android nao baixa PASTA, so arquivo a arquivo (verificado em
27/09/2026). Um arquivo unico ele baixa direto para Download/. O Roger sobe o .zip no
Drive com a mao dele -- este script nao fala com a internet.

LEI DESTE ARQUIVO
-----------------
Ele SO LE D:\\Music. Nunca renomeia, nunca move, nunca apaga, nunca reescreve um .m3u.
Em 27/09/2026 um loop meu sem filtro renomeou 29 arquivos do acervo dele e quebrou 17
entradas em 8 playlists, caladas. Toda escrita daqui acontece na pasta de saida.

Compressao: as musicas entram SEM compressao (ZIP_STORED). MP3/M4A ja vem comprimido --
deflate gastaria minutos de CPU para economizar quase nada, e o .zip aqui serve de
CAIXA, nao de compactador. So o indice, que e texto, entra comprimido.
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import unicodedata
import zipfile
from datetime import datetime, timedelta, timezone

MUSICA    = r"D:\Music"
PLAYLISTS = r"D:\Music\Playlists"
EXT       = (".mp3", ".m4a")
VERSAO_INDICE = 1
BRT = timezone(timedelta(hours=-3))

# Nao viajam: sao listas montadas pelo app na hora, nao existem como arquivo.
VIRTUAIS = ("Todas as músicas", "Fora das playlists")

# ------------------------------------------------------------------ o acervo


def pasta_capas():
    """Onde o Roxin de mesa guarda as miniaturas. Mesma conta do capas.py."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Roxin", "capas")


def chave_capa(nome_arquivo):
    """Nome do arquivo de musica -> nome do arquivo de miniatura (igual ao capas.py)."""
    return hashlib.md5(nome_arquivo.lower().encode("utf-8")).hexdigest() + ".png"


def limpar(nome):
    """Nome de arquivo -> nome legivel. Copia fiel do limpar() do Musica.pyw: se as
    duas pontas limparem diferente, o titulo na tela do celular nao bate com o do PC."""
    t = os.path.splitext(nome)[0]
    for rx in (r"\(M4A_\d+K\)", r"\(MP3_\d+K\)", r"\(mp3\)", r"\[[A-Za-z0-9_\-]{11}\]",
               r"\(Official (Music )?Video\)", r"\[Official (Music )?Video\]",
               r"\(Official Lyric Video\)", r"\(Lyric Video\)", r"\(Official Audio\)",
               r"\(Lyrics\)", r"\[Lyrics\]", r"\(Audio\)"):
        t = re.sub(rx, "", t, flags=re.I)
    t = re.sub(r"^\d{1,3}\s*-\s*", "", t).replace("AC_DC", "AC/DC")
    for a, b in (("_t", "'t"), ("_s", "'s"), ("_m", "'m"), ("_ll", "'ll"),
                 ("_re", "'re"), ("_ve", "'ve"), ("_d", "'d")):
        t = re.sub(r"\b(\w+)%s\b" % a, lambda m, b=b: m.group(1) + b, t)
    t = t.replace(" _ ", " / ").replace("_", " ")
    return re.sub(r"\s+", " ", t).strip(" -\u2013\u2014_") or os.path.splitext(nome)[0]


def cache_duracoes(base=None):
    """Duracoes ja medidas pelo app de mesa. Faltar isto nao e erro: a playlist traz
    a duracao no #EXTINF, e o que sobrar fica 0 (o app mede quando tocar)."""
    alvo = os.path.join(base or os.path.dirname(os.path.abspath(__file__)), "duracoes.json")
    try:
        return {k.lower(): v for k, v in
                json.load(io.open(alvo, encoding="utf-8")).items()}
    except Exception:
        return {}


def ler_playlists(pasta=PLAYLISTS, duracoes=None):
    """Le os .m3u e devolve {nome_da_lista: [ {caminho, titulo, duracao}, ... ]}.

    O titulo escrito no #EXTINF MANDA sobre o nome do arquivo -- e como o Roger chama
    a musica, e foi assim que o app de mesa sempre fez. Entrada que aponta para arquivo
    que nao existe entra como FALTANDO, nunca e engolida em silencio."""
    duracoes = duracoes if duracoes is not None else cache_duracoes()
    listas, faltando = {}, {}
    if not os.path.isdir(pasta):
        return listas, faltando
    for f in sorted(os.listdir(pasta)):
        if not f.lower().endswith((".m3u", ".m3u8")):
            continue
        nome_lista = os.path.splitext(f)[0]
        itens, ausentes, dur, titulo = [], [], None, None
        for ln in io.open(os.path.join(pasta, f), encoding="utf-8", errors="replace"):
            ln = ln.strip()
            if ln.startswith("#EXTINF:"):
                try:
                    dur = int(ln.split(":")[1].split(",")[0])
                except Exception:
                    dur = None
                titulo = ln.split(",", 1)[1].strip() if "," in ln else None
            elif ln and not ln.startswith("#"):
                c = os.path.normpath(ln)
                if os.path.isfile(c):
                    base = os.path.basename(c)
                    itens.append({
                        "caminho": c,
                        "titulo": titulo or limpar(base),
                        "duracao": dur or duracoes.get(base.lower(), 0),
                    })
                else:
                    ausentes.append(ln)
                dur = titulo = None
        listas[nome_lista] = itens
        if ausentes:
            faltando[nome_lista] = ausentes
    return listas, faltando


# ------------------------------------------------------- nome seguro no celular

PROIBIDOS = r'<>:"/\|?*'


def nome_no_pacote(caminho, usados):
    """Nome do arquivo DENTRO do pacote: legivel, seguro nos dois sistemas e unico.

    Acento fica (UTF-8 passa liso em Android e iOS); o que sai sao os caracteres que
    sistema de arquivo recusa. Se dois nomes diferentes desabarem no mesmo resultado,
    entra um sufixo curto do hash do caminho original -- assim duas faixas de nome
    parecido nunca se sobrescrevem, que seria perda de musica, calada.

    O nome na TELA nao depende disto: vem do titulo gravado no indice."""
    base, ext = os.path.splitext(os.path.basename(caminho))
    limpo = "".join(("_" if c in PROIBIDOS else c) for c in base)
    limpo = "".join(c for c in limpo if unicodedata.category(c)[0] != "C")  # controle
    limpo = re.sub(r"\s+", " ", limpo).strip(" .") or "faixa"
    if len(limpo) > 90:
        limpo = limpo[:90].strip()
    alvo = limpo + ext.lower()
    if alvo.lower() in usados:
        h = hashlib.sha1(caminho.lower().encode("utf-8")).hexdigest()[:6]
        alvo = "%s [%s]%s" % (limpo, h, ext.lower())
    usados.add(alvo.lower())
    return alvo


def sha256(caminho, bloco=1 << 20):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for p in iter(lambda: f.read(bloco), b""):
            h.update(p)
    return h.hexdigest()


def slug(nome):
    s = unicodedata.normalize("NFKD", nome)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")
    return s or "pacote"


# ------------------------------------------------------------------ empacotar


def montar_indice(nomes_listas, listas, capas=None):
    """Monta o indice do pacote. Faixa repetida em duas playlists entra UMA vez:
    o pacote guarda bytes, e bytes duplicados seriam MB a mais para ele subir."""
    capas = pasta_capas() if capas is None else capas
    faixas, por_caminho, usados = [], {}, set()
    saida_listas = []
    for nome in nomes_listas:
        idxs = []
        for item in listas.get(nome, []):
            c = item["caminho"]
            k = c.lower()
            if k not in por_caminho:
                base = os.path.basename(c)
                arq_capa = os.path.join(capas, chave_capa(base))
                tem_capa = os.path.isfile(arq_capa)
                dentro = nome_no_pacote(c, usados)
                por_caminho[k] = len(faixas)
                faixas.append({
                    "origem": c,                       # so para o gerador; sai do json
                    "arquivo": "musicas/" + dentro,
                    "titulo": item["titulo"],
                    "duracao": int(item["duracao"] or 0),
                    "capa": ("capas/" + os.path.splitext(dentro)[0] + ".png") if tem_capa else None,
                    "origem_capa": arq_capa if tem_capa else None,
                })
            n = por_caminho[k]
            # duracao/titulo da playlist ganham de um valor vazio vindo de outra lista
            if item["duracao"] and not faixas[n]["duracao"]:
                faixas[n]["duracao"] = int(item["duracao"])
            idxs.append(n)
        saida_listas.append({"nome": nome, "faixas": idxs})
    return faixas, saida_listas


def empacotar(nomes_listas, saida="pacotes", pasta_playlists=PLAYLISTS,
              capas=None, base_duracoes=None, quieto=False, forcar=False):
    """Gera um .zip por chamada, com as playlists pedidas. Devolve o relatorio."""
    def diz(*a):
        if not quieto:
            print(*a)

    listas, faltando = ler_playlists(pasta_playlists,
                                     cache_duracoes(base_duracoes))
    desconhecidas = [n for n in nomes_listas if n not in listas]
    if desconhecidas:
        raise SystemExit("playlist que nao existe: %s\ndisponiveis: %s"
                         % (", ".join(desconhecidas), ", ".join(sorted(listas))))

    faixas, saida_listas = montar_indice(nomes_listas, listas, capas)
    if not faixas:
        raise SystemExit("nenhuma faixa nas playlists pedidas -- nada a empacotar")

    os.makedirs(saida, exist_ok=True)
    rotulo = slug(nomes_listas[0]) if len(nomes_listas) == 1 else "%d-listas" % len(nomes_listas)
    destino = os.path.join(saida, "Roxin_%s.zip" % rotulo)

    # espaco: somar antes e avisar antes, nao falhar no meio da copia
    total_bytes = sum(os.path.getsize(f["origem"]) for f in faixas)
    livre = espaco_livre(saida)
    if livre is not None and livre < total_bytes * 1.05:
        raise SystemExit("espaco insuficiente em %s: precisa ~%s, livre %s"
                         % (saida, humano(total_bytes), humano(livre)))

    anterior = ler_indice(destino) if os.path.isfile(destino) else None
    diz("Empacotando %d faixa(s) de %s" % (len(faixas), ", ".join(nomes_listas)))

    indice = {
        "versao": VERSAO_INDICE,
        "gerado": datetime.now(BRT).isoformat(timespec="seconds"),
        "pacote": ", ".join(nomes_listas),
        "faixas": [],
        "playlists": saida_listas,
    }

    tmp = destino + ".parcial"
    copiadas = capas_dentro = 0
    try:
        # ZIP64 ligado na mao: acervo de musica passa de 4 GB sem esforco
        with zipfile.ZipFile(tmp, "w", allowZip64=True) as z:
            for f in faixas:
                origem = f["origem"]
                z.write(origem, f["arquivo"], compress_type=zipfile.ZIP_STORED)
                copiadas += 1
                entrada = {
                    "arquivo": f["arquivo"],
                    "titulo": f["titulo"],
                    "duracao": f["duracao"],
                    "bytes": os.path.getsize(origem),
                    "sha256": sha256(origem),
                    "capa": f["capa"],
                }
                if f["capa"]:
                    z.write(f["origem_capa"], f["capa"], compress_type=zipfile.ZIP_STORED)
                    capas_dentro += 1
                indice["faixas"].append(entrada)
                if not quieto and copiadas % 25 == 0:
                    diz("  %d/%d" % (copiadas, len(faixas)))
            z.writestr("roxin.json",
                       json.dumps(indice, ensure_ascii=False, indent=1),
                       compress_type=zipfile.ZIP_DEFLATED)
        os.replace(tmp, destino)
    finally:
        if os.path.isfile(tmp):
            os.remove(tmp)          # parcial nunca fica no lugar do bom

    rel = {
        "arquivo": destino,
        "faixas": len(indice["faixas"]),
        "capas": capas_dentro,
        "sem_capa": len(indice["faixas"]) - capas_dentro,
        "bytes": os.path.getsize(destino),
        "playlists": {l["nome"]: len(l["faixas"]) for l in saida_listas},
        "faltando_no_pc": faltando,
        "mudou": comparar(anterior, indice) if anterior else None,
    }
    diz("\n%s" % destino)
    diz("  %d faixas  ·  %d com capa, %d sem  ·  %s"
        % (rel["faixas"], rel["capas"], rel["sem_capa"], humano(rel["bytes"])))
    for nome, n in rel["playlists"].items():
        diz("  playlist %-24s %3d faixas" % (nome, n))
    if faltando:
        diz("\n  ATENCAO -- entradas quebradas nas playlists DO PC (nao entraram):")
        for nome, itens in faltando.items():
            diz("    %s: %d" % (nome, len(itens)))
        diz("    rode  python conferir_playlists.py --detalhe")
    if rel["mudou"]:
        m = rel["mudou"]
        diz("\n  em relacao ao pacote anterior: +%d entraram, -%d sairam, %d iguais"
            % (len(m["entraram"]), len(m["sairam"]), m["iguais"]))
    return rel


def comparar(antes, agora):
    a = {f["arquivo"] for f in antes.get("faixas", [])}
    b = {f["arquivo"] for f in agora.get("faixas", [])}
    return {"entraram": sorted(b - a), "sairam": sorted(a - b), "iguais": len(a & b)}


# ------------------------------------------------------------------- conferir


def ler_indice(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        return json.loads(z.read("roxin.json").decode("utf-8"))


def conferir(zip_path, quieto=False):
    """Abre o pacote e prova, sem confiar em nada: cada faixa do indice esta dentro,
    com o tamanho certo e o MESMO sha256. Devolve lista de problemas (vazia = bom)."""
    def diz(*a):
        if not quieto:
            print(*a)

    problemas = []
    with zipfile.ZipFile(zip_path) as z:
        nomes = set(z.namelist())
        if "roxin.json" not in nomes:
            return ["sem roxin.json -- nao e pacote do Roxin"]
        ind = json.loads(z.read("roxin.json").decode("utf-8"))
        if ind.get("versao") != VERSAO_INDICE:
            problemas.append("indice versao %s, este script fala %s"
                             % (ind.get("versao"), VERSAO_INDICE))
        for f in ind.get("faixas", []):
            if f["arquivo"] not in nomes:
                problemas.append("faixa no indice e fora do pacote: %s" % f["arquivo"])
                continue
            with z.open(f["arquivo"]) as dentro:
                h = hashlib.sha256()
                n = 0
                for p in iter(lambda: dentro.read(1 << 20), b""):
                    h.update(p)
                    n += len(p)
            if n != f["bytes"]:
                problemas.append("tamanho diferente: %s (%d no pacote, %d no indice)"
                                 % (f["arquivo"], n, f["bytes"]))
            if h.hexdigest() != f["sha256"]:
                problemas.append("sha256 diferente: %s" % f["arquivo"])
            if f.get("capa") and f["capa"] not in nomes:
                problemas.append("capa no indice e fora do pacote: %s" % f["capa"])
        # caminho relativo, nunca absoluto: e a razao de existir do indice
        for f in ind.get("faixas", []):
            if os.path.isabs(f["arquivo"]) or re.match(r"^[A-Za-z]:", f["arquivo"]):
                problemas.append("caminho ABSOLUTO no indice: %s" % f["arquivo"])
        alvos = {f["arquivo"] for f in ind.get("faixas", [])}
        for l in ind.get("playlists", []):
            for n in l["faixas"]:
                if not (0 <= n < len(ind["faixas"])):
                    problemas.append("playlist %s aponta para faixa %s, que nao existe"
                                     % (l["nome"], n))
        orfaos = [n for n in nomes
                  if n.startswith("musicas/") and n not in alvos]
        if orfaos:
            problemas.append("%d arquivo(s) dentro do pacote fora do indice" % len(orfaos))

    if quieto:
        return problemas
    if problemas:
        diz("%s -- %d PROBLEMA(S):" % (zip_path, len(problemas)))
        for p in problemas[:40]:
            diz("  - %s" % p)
    else:
        ind = ler_indice(zip_path)
        diz("%s -- OK" % zip_path)
        diz("  %d faixas, geradas em %s, 0 problema"
            % (len(ind["faixas"]), ind.get("gerado", "?")))
    return problemas


# --------------------------------------------------------------------- apoio


def espaco_livre(pasta):
    try:
        import shutil
        return shutil.disk_usage(pasta if os.path.isdir(pasta)
                                 else os.path.dirname(os.path.abspath(pasta))).free
    except Exception:
        return None


def humano(n):
    n = float(n or 0)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return "%.1f %s" % (n, u) if u != "B" else "%d B" % n
        n /= 1024


def listar(pasta=PLAYLISTS, base_duracoes=None):
    listas, faltando = ler_playlists(pasta, cache_duracoes(base_duracoes))
    if not listas:
        print("nenhuma playlist em %s" % pasta)
        return
    print("Playlists em %s\n" % pasta)
    print("  %-26s %6s %10s %9s" % ("nome", "faixas", "duracao", "tamanho"))
    for nome in sorted(listas):
        itens = listas[nome]
        seg = sum(i["duracao"] or 0 for i in itens)
        try:
            b = sum(os.path.getsize(i["caminho"]) for i in itens)
        except OSError:
            b = 0
        aviso = "  <- %d quebrada(s)" % len(faltando[nome]) if nome in faltando else ""
        print("  %-26s %6d %7dh%02d %9s%s"
              % (nome, len(itens), seg // 3600, (seg % 3600) // 60, humano(b), aviso))
    print("\nEscolha as que vao viajar:\n  python empacotar.py \"nome\" \"outro nome\"")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Empacota playlists do Roxin num .zip para o celular.")
    ap.add_argument("listas", nargs="*", help="nomes das playlists que vao viajar")
    ap.add_argument("--listar", action="store_true", help="mostra as playlists e o peso de cada")
    ap.add_argument("--conferir", metavar="ZIP", help="confere um pacote ja gerado")
    ap.add_argument("--saida", default="pacotes", help="pasta do .zip (padrao: pacotes)")
    ap.add_argument("--quieto", action="store_true")
    a = ap.parse_args(argv)

    if a.conferir:
        return 1 if conferir(a.conferir, a.quieto) else 0
    if a.listar or not a.listas:
        listar()
        return 0
    rel = empacotar(a.listas, saida=a.saida, quieto=a.quieto)
    ruins = conferir(rel["arquivo"], quieto=True)
    if ruins:
        print("\nPACOTE COM PROBLEMA -- %d item(ns). Rode --conferir para ver." % len(ruins))
        return 1
    if not a.quieto:
        print("\n  conferido: cada faixa com o mesmo sha256 do original, 0 problema")
        print("  agora: subir esse arquivo no Drive e baixar no celular")
    return 0


if __name__ == "__main__":
    sys.exit(main())
