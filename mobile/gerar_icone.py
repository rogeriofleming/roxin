# -*- coding: utf-8 -*-
"""Gera o icone do app Android a partir de `marca.py` -- o mesmo vetor do app de mesa.

    python mobile/gerar_icone.py

Existe versionado pelo mesmo motivo do docs/gerar_marca.py: icone e imagem, e
imagem envelhece calada. Se a marca mudar, este script refaz os cinco tamanhos a
partir da FONTE, e ninguem precisa lembrar de reexportar na mao.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainter, QPixmap, QColor
from PySide6.QtCore import Qt

import marca as M

# os cinco baldes de densidade do Android, com o lado do icone em cada
DENSIDADES = {
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
}

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "android", "app", "src", "main", "res")


def desenhar(lado):
    """Passaro roxo sobre disco de madrugada, com folga nas bordas.

    O Android recorta o icone em circulo, quadrado arredondado ou gota, dependendo
    do aparelho -- por isso o passaro fica dentro de ~62% do lado, senao a cauda
    (que e a marca do bicho) e a primeira coisa que o recorte come."""
    pm = QPixmap(lado, lado)
    pm.fill(Qt.transparent)
    pt = QPainter(pm)
    pt.setRenderHint(QPainter.Antialiasing, True)
    pt.setPen(Qt.NoPen)
    pt.setBrush(QColor(M.NOITE))
    pt.drawEllipse(0, 0, lado, lado)
    dentro = lado * 0.62
    pt.translate((lado - dentro) / 2, (lado - dentro) / 2)
    M.desenhar(pt, dentro, cor=M.AMBAR)      # AMBAR guarda o roxo #a77cf0
    pt.end()
    return pm


def main():
    app = QApplication(sys.argv)          # precisa existir para o QPixmap pintar
    if not os.path.isdir(RES):
        print("nao achei %s -- rode o flutter create antes" % RES)
        return 1
    feitos = []
    for nome, lado in DENSIDADES.items():
        pasta = os.path.join(RES, "mipmap-" + nome)
        os.makedirs(pasta, exist_ok=True)
        alvo = os.path.join(pasta, "ic_launcher.png")
        pm = desenhar(lado)
        if not pm.save(alvo, "PNG"):
            print("FALHOU ao salvar %s" % alvo)
            return 1
        feitos.append("%s (%dpx)" % (nome, lado))
    print("icone do Roxin gerado a partir de marca.py:")
    for f in feitos:
        print("  " + f)
    del app
    return 0


if __name__ == "__main__":
    sys.exit(main())
