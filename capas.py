# -*- coding: utf-8 -*-
"""Capas do Roxin.

Extrai a imagem embutida de cada musica de D:\Music e guarda uma miniatura
no cache (%LOCALAPPDATA%\Roxin\capas). O app le dali — nao mexe em tag nenhuma.

Rodar:  python capas.py            (so o que falta)
        python capas.py --forcar   (refaz tudo)
"""

import io, os, sys, hashlib

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


if __name__ == "__main__":
    gerar(forcar="--forcar" in sys.argv)
