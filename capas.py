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
    for nome in sorted(os.listdir(MUSICA)):
        if os.path.splitext(nome)[1].lower() not in (".mp3", ".m4a"):
            continue
        destino = os.path.join(cache, chave(nome))
        if os.path.exists(destino) and not forcar:
            pulou += 1; com += 1
            continue
        dados = imagem_embutida(os.path.join(MUSICA, nome))
        if not dados:
            sem += 1
            continue
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


if __name__ == "__main__":
    if "--youtube" in sys.argv:
        from PySide6.QtWidgets import QApplication   # QImage precisa do app
        QApplication([])
        varrer_youtube(forcar="--forcar" in sys.argv)
    else:
        gerar(forcar="--forcar" in sys.argv)
