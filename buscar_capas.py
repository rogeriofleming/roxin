# -*- coding: utf-8 -*-
"""Capa REAL (quadrada) para as musicas sem imagem embutida.

Usa a API publica de busca da Apple (sem chave, somente leitura). NAO altera
nenhuma musica e NAO grava direto no cache do app: guarda em "propostas" e monta
um HTML de conferencia, porque a busca por nome erra e quem aprova e o Roger.

    python buscar_capas.py --amostra 40    # mede o acerto numa amostra
    python buscar_capas.py                 # varre tudo que falta
    python buscar_capas.py --aprovar       # copia as propostas para o cache do app
"""
import io, os, re, sys, json, time, shutil, unicodedata
import urllib.parse, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capas as C

API_APPLE  = "https://itunes.apple.com/search?%s"
API_DEEZER = "https://api.deezer.com/search?%s"
PROPOSTAS = os.path.join(os.path.dirname(C.pasta_cache()), "propostas")
RELATORIO = os.path.join(os.path.dirname(C.pasta_cache()), "conferir_capas.html")

RUIDO = ("official", "video", "audio", "lyrics", "lyric", "legendado", "legendada",
         "traducao", "hd", "remastered", "version", "feat", "ft", "letra", "clipe",
         "nocopyrightsounds", "ncs", "release", "cover", "with")


def normal(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s)


def fichas(s):
    return [p for p in normal(s).split() if p and p not in RUIDO and len(p) > 1]


def termo_de_busca(nome_arquivo):
    s = os.path.splitext(nome_arquivo)[0]
    for rx in (r"\(M4A_\d+K\)", r"\(MP3_\d+K\)", r"\[[A-Za-z0-9_\-]{11}\]",
               r"__ ?LEGENDADO ?__", r"\(?\bLegendad[oa]\b\)?", r"\(Lyrics?\)",
               r"\[Lyrics?\]", r"\(Official.*?\)", r"\[Official.*?\]", r"\(Tradu..o\)",
               r"_Tradu..o_", r"\(Audio\)", r"\(8D AUDIO\)", r"\(Video.*?\)",
               r"\[No Copyright Music\]", r"\[NCS Release\]"):
        s = re.sub(rx, " ", s, flags=re.I)
    s = re.sub(r"^\d{1,3}\s*[-\.]\s*", "", s).replace("_", " ")
    return re.sub(r"\s+", " ", s).strip(" -–—")


def cobertura(alvo, dentro_de):
    """Quanto das palavras de alvo aparece em dentro_de (0 a 1)."""
    a, b = fichas(alvo), set(fichas(dentro_de))
    if not a:
        return 0.0
    return sum(1 for p in a if p in b) / float(len(a))


def miolo(titulo):
    """Titulo sem os parenteses: "Sucker For Pain (with X)" -> "Sucker For Pain".
    Sem isso, o extra do catalogo derruba o casamento de musica certa."""
    return re.sub(r"[\(\[].*?[\)\]]", " ", str(titulo or ""))


def escolher(resultados, termo):
    """Devolve (item, nota, forca). forca "forte" = artista confere;
    "conferir" = so o titulo bate (nome de arquivo sem artista) e vai para o HTML
    num grupo separado, porque e ali que a busca por nome erra.
    Exigir o ARTISTA e o que barra "Ellie Goulding" virar "Ella Langley"."""
    forte, nota_forte = None, 0.0
    fraco = None
    curto = len(fichas(termo)) <= 6          # nome curto = provavelmente so o titulo
    for pos, it in enumerate(resultados):
        if not it.get("arte"):
            continue
        ct = cobertura(miolo(it.get("trackName")), termo)
        ca = cobertura(it.get("artistName"), termo)
        if ct >= 0.75 and ca >= 0.5:
            nota = ct * 0.6 + ca * 0.4
            if nota > nota_forte:
                forte, nota_forte = it, nota
        elif pos == 0 and curto and ct >= 0.999 and fraco is None:
            fraco = it
    if forte is not None:
        return forte, nota_forte, "forte"
    if fraco is not None:
        return fraco, 0.6, "conferir"
    return None, 0.0, None


def _pega(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Roxin/1.0 (player local)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(io.TextIOWrapper(r, encoding="utf-8"))


def deezer(termo):
    """Fonte principal. A da Apple bloqueia depois de ~100 consultas (429 e depois
    403) — com 623 musicas para buscar, ela nao serve para varredura."""
    p = urllib.parse.urlencode({"q": termo, "limit": 5})
    saida = []
    for d in (_pega(API_DEEZER % p).get("data") or []):
        alb = d.get("album") or {}
        saida.append({"artistName": (d.get("artist") or {}).get("name", ""),
                      "trackName": d.get("title", ""),
                      "arte": alb.get("cover_big") or alb.get("cover_medium") or ""})
    return saida


def apple(termo):
    """Reserva, para quando o Deezer nao acha."""
    p = urllib.parse.urlencode({"term": termo, "media": "music", "limit": 5})
    saida = []
    for d in (_pega(API_APPLE % p).get("results") or []):
        arte = d.get("artworkUrl100") or ""
        saida.append({"artistName": d.get("artistName", ""),
                      "trackName": d.get("trackName", ""),
                      "arte": arte.replace("100x100bb", "600x600bb")})
    return saida


def consulta(termo, tentativas=3):
    """Deezer primeiro; se der erro ou vier vazio, tenta a Apple.
    Em 429/403 espera e tenta de novo, em vez de queimar a fila toda."""
    espera = 15
    for n in range(tentativas):
        try:
            r = deezer(termo)
            if r:
                return r
            try:
                return apple(termo)
            except Exception:
                return []
        except urllib.error.HTTPError as e:
            if e.code not in (429, 403) or n == tentativas - 1:
                raise
            print("      %d: esperando %ds" % (e.code, espera)); sys.stdout.flush()
            time.sleep(espera); espera *= 2
    return []


def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Roxin/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


TENTADOS = os.path.join(os.path.dirname(C.pasta_cache()), "tentados.json")


def ja_tentados():
    try:
        return json.load(io.open(TENTADOS, encoding="utf-8"))
    except Exception:
        return {}


def guardar_tentados(d):
    io.open(TENTADOS, "w", encoding="utf-8").write(
        json.dumps(d, ensure_ascii=False, indent=1))


def sem_capa(pular_tentados=True):
    """Musicas sem capa no cache. Retomada: pula quem ja tem proposta baixada
    ou ja foi consultado sem sucesso, para nao gastar a API de novo."""
    feitos = ja_tentados() if pular_tentados else {}
    faltam = []
    for n in sorted(os.listdir(C.MUSICA)):
        if os.path.splitext(n)[1].lower() not in (".mp3", ".m4a"):
            continue
        if os.path.exists(os.path.join(C.pasta_cache(), C.chave(n))):
            continue
        if os.path.exists(os.path.join(PROPOSTAS, C.chave(n))):
            continue
        if n in feitos:
            continue
        faltam.append(n)
    return faltam


def aprovar(so_fortes=True):
    """Leva as propostas para o cache que o app le. Por padrao SO as que tiveram
    o artista confirmado — as de titulo solto erram e ficam para ele conferir."""
    if not os.path.isdir(PROPOSTAS):
        print("nao ha propostas em %s" % PROPOSTAS)
        return 0
    reg = ja_tentados()
    forca_por_arquivo = {}
    for nome, d in reg.items():
        if isinstance(d, dict) and d.get("r") == "aceito":
            forca_por_arquivo[C.chave(nome)] = d.get("forca", "conferir")
    n = pulou = 0
    for f in sorted(os.listdir(PROPOSTAS)):
        if not f.endswith(".png"):
            continue
        if so_fortes and forca_por_arquivo.get(f) != "forte":
            pulou += 1
            continue
        shutil.copy2(os.path.join(PROPOSTAS, f), os.path.join(C.pasta_cache(), f))
        n += 1
    print("%d capas copiadas para o cache do app" % n)
    if pulou:
        print("%d ficaram de fora (so o titulo bateu): conferir em %s" % (pulou, RELATORIO))
    return n


ESTILO = """
 body{background:#0f0c16;color:#e9e5ef;font:14px "Segoe UI",sans-serif;margin:0;padding:28px}
 h1{font:400 26px Georgia,serif;margin:0 0 6px}
 h2{font:400 18px Georgia,serif;color:#a77cf0;margin:34px 0 14px;
    border-top:1px solid #272033;padding-top:20px}
 p.sub{color:#8f88a3;margin:0 0 24px;max-width:72ch;line-height:1.55}
 .grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:18px}
 figure{margin:0;background:#181425;border:1px solid #272033;border-radius:10px;padding:10px}
 img{width:100%;aspect-ratio:1;object-fit:contain;background:#221c33;border-radius:6px;display:block}
 figcaption{font-size:11px;line-height:1.45;margin-top:8px;display:flex;flex-direction:column;gap:3px}
 b{color:#e9e5ef;font-weight:600} span{color:#8f88a3}
"""


def html(_ignorado=None):
    """Monta o HTML com TODAS as propostas em disco, nao so as desta rodada —
    a busca cai em 429 e roda em pedacos, entao o relatorio tem que acumular."""
    reg = ja_tentados()
    aceitos = []
    for nome, d in sorted(reg.items()):
        if not isinstance(d, dict) or d.get("r") != "aceito":
            continue
        arq = os.path.join(PROPOSTAS, C.chave(nome))
        if os.path.exists(arq):
            aceitos.append((nome, d.get("rotulo", "?"), arq, 0, d.get("forca", "conferir")))

    def grade(itens):
        saida = []
        for nome, rotulo, arq, nota, forca in itens:
            saida.append(
                '<figure><img src="file:///%s" alt=""><figcaption><b>%s</b>'
                '<span>%s</span></figcaption></figure>'
                % (arq.replace("\\", "/"), rotulo.replace("<", "&lt;"),
                   nome.replace("<", "&lt;")[:70]))
        return "".join(saida) or '<p class="sub">nenhuma</p>'

    fortes   = [a for a in aceitos if a[4] == "forte"]
    conferir = [a for a in aceitos if a[4] != "forte"]
    doc = ('<!doctype html><meta charset="utf-8"><title>Conferir capas - Roxin</title>'
           '<style>%s</style><h1>Conferir capas</h1>'
           '<p class="sub">Em cima de cada quadro, o que a busca devolveu; embaixo, o '
           'arquivo da tua pasta. Nada disso entrou no app ainda.</p>'
           '<h2>Artista confere &mdash; %d</h2><div class="grade">%s</div>'
           '<h2>So o titulo bate, confirma pra mim &mdash; %d</h2>'
           '<p class="sub">O nome do arquivo nao traz o artista, entao aceitei o primeiro '
           'resultado da busca. E aqui que costuma vir capa errada.</p>'
           '<div class="grade">%s</div>'
           % (ESTILO, len(fortes), grade(fortes), len(conferir), grade(conferir)))
    io.open(RELATORIO, "w", encoding="utf-8").write(doc)
    print("conferencia: %s" % RELATORIO)


def refazer_em_alta(limite_px=260):
    """As primeiras rodadas guardaram a capa em 160px (o cache era 160). Depois do
    cache subir para 512, a capa grande do modo "capa cheia" precisa de resolucao:
    reconsulta pelo ROTULO ja casado (nao pelo nome sujo do arquivo) e baixa o
    maior tamanho que a fonte tiver."""
    from PySide6.QtGui import QImage
    from PySide6.QtCore import Qt
    reg = ja_tentados()
    fila = []
    for nome, d in sorted(reg.items()):
        if not isinstance(d, dict) or d.get("r") != "aceito":
            continue
        for pasta in (C.pasta_cache(), PROPOSTAS):
            alvo = os.path.join(pasta, C.chave(nome))
            if not os.path.exists(alvo):
                continue
            im = QImage(alvo)
            if max(im.width(), im.height()) <= limite_px:
                fila.append((nome, d, alvo))
                break
    print("capas em baixa resolucao: %d" % len(fila))
    trocadas = falhou = igual = 0
    for i, (nome, d, alvo) in enumerate(fila, 1):
        rotulo = d.get("rotulo") or ""
        try:
            res = consulta(rotulo)
        except Exception as e:
            falhou += 1; print("  %4d ERRO %s" % (i, e)); continue
        it, _nota, _forca = escolher(res, rotulo)
        if it is None and res:
            it = res[0]                      # o rotulo veio do proprio catalogo
        if it is None or not it.get("arte"):
            igual += 1; continue
        url = it["arte"].replace("/500x500", "/1000x1000").replace(
            "500x500-000000-80-0-0", "1000x1000-000000-80-0-0")
        try:
            img = QImage()
            if not img.loadFromData(baixar(url)):
                img = QImage()
                if not img.loadFromData(baixar(it["arte"])):
                    falhou += 1; continue
            if max(img.width(), img.height()) <= limite_px:
                igual += 1; continue
            if img.width() > C.LADO or img.height() > C.LADO:
                img = img.scaled(C.LADO, C.LADO, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img.save(alvo, "PNG")
            d["url"] = url
            trocadas += 1
        except Exception as e:
            falhou += 1; print("  %4d ERRO baixa %s" % (i, e))
        time.sleep(0.4)
        if i % 25 == 0:
            guardar_tentados(reg); print("  ... %d/%d" % (i, len(fila))); sys.stdout.flush()
    guardar_tentados(reg)
    print("")
    print("trocadas por versao grande: %d | ja eram o maximo: %d | falhas: %d"
          % (trocadas, igual, falhou))
    return trocadas


def main():
    if "--aprovar" in sys.argv:
        return aprovar(so_fortes="--tudo" not in sys.argv)
    if "--grandes" in sys.argv:
        return refazer_em_alta()

    faltam = sem_capa()
    print("sem capa embutida: %d" % len(faltam))
    amostra = 0
    if "--amostra" in sys.argv:
        amostra = int(sys.argv[sys.argv.index("--amostra") + 1])
        import random
        random.seed(7)
        faltam = random.sample(faltam, min(amostra, len(faltam)))

    os.makedirs(PROPOSTAS, exist_ok=True)
    from PySide6.QtGui import QImage
    from PySide6.QtCore import Qt

    feitos = ja_tentados()
    aceitos, recusados, vazios, falhas = [], 0, 0, 0
    for i, nome in enumerate(faltam, 1):
        termo = termo_de_busca(nome)
        try:
            res = consulta(termo)
        except Exception as e:
            falhas += 1
            print("  %4d ERRO rede  %s" % (i, e))
            if ("429" in str(e) or "403" in str(e)) and falhas >= 3:
                print("  a API esta cortando mesmo com espera — paro aqui. "
                      "Rode de novo mais tarde: a retomada continua de onde parou.")
                break
            continue
        if not res:
            vazios += 1
            feitos[nome] = {"r": "nada"}
            print("  %4d nada       %s" % (i, termo[:58]))
            continue
        it, nota, forca = escolher(res, termo)
        if it is None:
            recusados += 1
            feitos[nome] = {"r": "recusado",
                            "rotulo": "%s - %s" % (res[0].get("artistName", "?"),
                                                   res[0].get("trackName", "?"))}
            print("  %4d recusei    %-38s (1o era: %s - %s)"
                  % (i, termo[:38], res[0].get("artistName", "?")[:16],
                     res[0].get("trackName", "?")[:20]))
            continue
        rotulo = "%s - %s" % (it.get("artistName", "?"), it.get("trackName", "?"))
        arq = os.path.join(PROPOSTAS, C.chave(nome))
        if amostra:
            aceitos.append((nome, rotulo, "", nota, forca))
            print("  %4d %-9s %-38s -> %s" % (i, forca, termo[:38], rotulo[:40]))
        else:
            try:
                img = QImage()
                if img.loadFromData(baixar(it["arte"])):
                    img.scaled(C.LADO, C.LADO, Qt.KeepAspectRatio,
                               Qt.SmoothTransformation).save(arq, "PNG")
                    aceitos.append((nome, rotulo, arq, nota, forca))
                    feitos[nome] = {"r": "aceito", "rotulo": rotulo, "forca": forca}
                else:
                    falhas += 1
            except Exception as e:
                falhas += 1
                print("  %4d ERRO baixa %s" % (i, e))
        time.sleep(0.45)     # ritmo folgado: e API publica de graca

    guardar_tentados(feitos)
    restam = len(sem_capa())
    print("")
    print("ainda sem tentativa: %d" % restam)
    nf = sum(1 for a in aceitos if a[4] == "forte")
    print("")
    print("aceitas: %d (%d com artista confirmado, %d para conferir)" % (len(aceitos), nf, len(aceitos) - nf))
    print("recusadas: %d | nada encontrado: %d | falhas: %d  (de %d)"
          % (recusados, vazios, falhas, len(faltam)))
    if not amostra:
        html()
        print("propostas em: %s  (nada foi para o app ainda)" % PROPOSTAS)


if __name__ == "__main__":
    main()
