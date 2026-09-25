# -*- coding: utf-8 -*-
"""Gera docs/marca.png — o pássaro e o nome, na cor de hoje.

Existe versionado de proposito: a imagem anterior era um render solto, de quando
o app se chamava "Rouxinol" e a marca era ambar. O script que a gerou se perdeu,
entao ninguem percebeu que a imagem tinha envelhecido. Esta aqui para que a marca
do README seja sempre refeita a partir de `marca.py`, nunca de um arquivo antigo.

    python docs/gerar_marca.py
"""
import os, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont
from PySide6.QtCore import Qt, QPointF, QRectF

import marca as M

ESCALA = 2                      # render em 2x: fica nitido em tela retina
L, A   = 460 * ESCALA, 130 * ESCALA


def main():
    app = QApplication(sys.argv)     # sem plataforma "offscreen": ela nao acha
                                     # as fontes do Windows e o texto sai quadrado
    pm = QPixmap(L, A)
    pm.fill(QColor(M.NOITE))

    pt = QPainter(pm)
    pt.setRenderHint(QPainter.Antialiasing, True)
    pt.setRenderHint(QPainter.TextAntialiasing, True)

    # disco do painel atras do passaro, como no canto da janela
    disco = 92 * ESCALA
    cx, cy = 36 * ESCALA + disco / 2, A / 2
    pt.setPen(Qt.NoPen)
    pt.setBrush(QColor(M.PAINEL))
    pt.drawEllipse(QPointF(cx, cy), disco / 2, disco / 2)

    # o passaro, na cor de destaque de hoje (M.AMBAR guarda o roxo #a77cf0)
    passaro = 62 * ESCALA
    pt.save()
    pt.translate(cx - passaro / 2, cy - passaro / 2 + 2 * ESCALA)
    M.desenhar(pt, passaro, M.AMBAR)
    pt.restore()

    # o nome, em serifa — a marca fala Georgia, a interface fala Segoe UI
    f = QFont("Georgia", 40 * ESCALA)
    f.setStyleStrategy(QFont.PreferAntialias)
    pt.setFont(f)
    pt.setPen(QColor(M.PENA))
    x = 36 * ESCALA + disco + 26 * ESCALA
    pt.drawText(QRectF(x, 0, L - x, A), Qt.AlignVCenter | Qt.AlignLeft, "Roxin")

    pt.end()

    destino = os.path.join(RAIZ, "docs", "marca.png")
    pm.save(destino)
    print("marca gerada:", destino, "|", L, "x", A,
          "| passaro:", M.AMBAR, "| fundo:", M.NOITE)


if __name__ == "__main__":
    main()
