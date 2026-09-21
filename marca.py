# -*- coding: utf-8 -*-
"""Marca Roxin — silhueta desenhada em vetor, sem arquivo de imagem externo."""

from PySide6.QtCore import QPointF, Qt, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPixmap, QIcon, QBrush

# ---------------------------------------------------------------- paleta
NOITE      = "#0f0c16"   # fundo: madrugada roxa (nunca preto puro)
PAINEL     = "#181425"   # superficie elevada
LINHA      = "#272033"   # divisoes
PENA       = "#e9e5ef"   # texto principal: branco com um veu lilas
PENA_FRACA = "#8f88a3"   # texto secundario
AMBAR      = "#a77cf0"   # destaque: o roxo do Roxin
AMBAR_CLARO= "#bb97f6"   # destaque em hover
LUAR       = "#6d5f9e"   # apoio, usado com parcimonia


def caminho_passaro():
    """Rouxinol de perfil, pousado, olhando para a esquerda. Canvas 100x100."""
    p = QPainterPath()
    # bico: curto e encaixado na cabeca, como o de um rouxinol
    p.moveTo(11, 32)
    p.lineTo(26, 28.5)
    p.lineTo(26, 36.5)
    p.closeSubpath()
    # cabeca + costas + cauda + peito, num traco so
    c = QPainterPath()
    c.moveTo(25, 25)
    c.cubicTo(33, 15, 49, 20, 54, 34)      # topo da cabeca descendo pelas costas
    c.cubicTo(59, 45, 66, 54, 74, 59)      # dorso ate a base da cauda
    c.lineTo(95, 79)                        # cauda: ponta longa e inclinada
    c.lineTo(87, 83)
    c.cubicTo(73, 75, 62, 71, 52, 68)      # volta da cauda
    c.cubicTo(37, 64, 26, 54, 24, 43)      # barriga subindo
    c.cubicTo(23, 36, 22, 30, 25, 25)      # fecha no peito/garganta
    c.closeSubpath()
    p.addPath(c)
    return p


def caminho_asa():
    """Asa: uma folha fechada sobre o corpo, dobrada."""
    a = QPainterPath()
    a.moveTo(33, 38)
    a.cubicTo(45, 36, 56, 45, 62, 58)
    a.cubicTo(52, 56, 40, 50, 33, 38)
    a.closeSubpath()
    return a


def desenhar(painter, tam, cor=AMBAR, cor_asa=None, olho=True):
    """Desenha a marca num painter ja posicionado, ocupando tam x tam."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.scale(tam / 100.0, tam / 100.0)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(cor)))
    painter.drawPath(caminho_passaro())
    painter.setBrush(QBrush(QColor(cor_asa or QColor(cor).darker(135))))
    painter.drawPath(caminho_asa())
    if olho:
        painter.setBrush(QBrush(QColor(NOITE)))
        painter.drawEllipse(QPointF(30, 30), 2.6, 2.6)
    painter.restore()


def pixmap(tam, cor=AMBAR, fundo=None):
    pm = QPixmap(tam, tam)
    pm.fill(QColor(fundo) if fundo else Qt.transparent)
    pt = QPainter(pm)
    desenhar(pt, tam, cor)
    pt.end()
    return pm


def pintar_barra_titulo(janela):
    """Windows 11: tira a cor de destaque do sistema da barra de titulo e poe a do app.
    Devolve True se o Windows aceitou. Em versao antiga falha em silencio, sem quebrar."""
    import ctypes
    DARK, BORDA, FUNDO, TEXTO = 20, 34, 35, 36     # DWMWA_*
    def colorref(hexa):
        h = hexa.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return ctypes.c_int(b << 16 | g << 8 | r)  # COLORREF e 0x00BBGGRR, nao RGB
    try:
        hwnd = int(janela.winId())
        dwm = ctypes.windll.dwmapi
        ok = True
        for attr, valor in ((DARK, ctypes.c_int(1)), (FUNDO, colorref(NOITE)),
                            (TEXTO, colorref(PENA)), (BORDA, colorref(LINHA))):
            r = dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(valor), 4)
            ok = ok and (r == 0)
        return ok
    except Exception:
        return False


def icone(tam=256):
    """Icone da janela: passaro ambar sobre disco de noite."""
    pm = QPixmap(tam, tam)
    pm.fill(Qt.transparent)
    pt = QPainter(pm)
    pt.setRenderHint(QPainter.Antialiasing, True)
    pt.setPen(Qt.NoPen)
    pt.setBrush(QBrush(QColor(PAINEL)))
    pt.drawEllipse(QRectF(0, 0, tam, tam))
    pt.translate(tam * 0.13, tam * 0.16)
    desenhar(pt, tam * 0.74)
    pt.end()
    return QIcon(pm)
