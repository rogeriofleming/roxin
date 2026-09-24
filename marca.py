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


def _caminhos_controle(nome):
    """Icones dos controles desenhados em vetor, num canvas 24x24.
    Glifo de fonte fica a merce da fonte instalada e serrilha; vetor nao."""
    p = QPainterPath()
    if nome == "play":
        p.moveTo(8, 5); p.lineTo(19, 12); p.lineTo(8, 19); p.closeSubpath()
    elif nome == "pause":
        p.addRoundedRect(QRectF(7.5, 5, 3.4, 14), 1.4, 1.4)
        p.addRoundedRect(QRectF(13.1, 5, 3.4, 14), 1.4, 1.4)
    elif nome == "anterior":
        p.addRoundedRect(QRectF(5, 5, 2.6, 14), 1.2, 1.2)
        p.moveTo(19, 5); p.lineTo(19, 19); p.lineTo(8.6, 12); p.closeSubpath()
    elif nome == "proxima":
        p.moveTo(5, 5); p.lineTo(15.4, 12); p.lineTo(5, 19); p.closeSubpath()
        p.addRoundedRect(QRectF(16.4, 5, 2.6, 14), 1.2, 1.2)
    elif nome == "aleatorio":
        for y1, y2 in ((7.5, 16.5), (16.5, 7.5)):          # duas setas que se cruzam
            c = QPainterPath()
            c.moveTo(3.5, y1)
            c.cubicTo(8, y1, 10, y2, 14.5, y2)
            p.addPath(_traco(c, 2.0))
        p.addPath(_ponta(14.0, 7.5)); p.addPath(_ponta(14.0, 16.5))
    elif nome == "repetir":
        c = QPainterPath()
        c.arcMoveTo(QRectF(4.5, 4.5, 15, 15), 65)
        c.arcTo(QRectF(4.5, 4.5, 15, 15), 65, 300)
        p.addPath(_traco(c, 2.0))
        p.addPath(_ponta(17.4, 8.6, -35))
    elif nome in ("saida", "som", "som_baixo", "mudo"):     # alto-falante
        # um corpo so para os quatro: o que muda e quantas ondas saem dele
        p.moveTo(4, 9.5); p.lineTo(8, 9.5); p.lineTo(12.5, 5); p.lineTo(12.5, 19)
        p.lineTo(8, 14.5); p.lineTo(4, 14.5); p.closeSubpath()
        ondas = {"saida": (3.4, 6.2), "som": (3.4, 6.2),
                 "som_baixo": (3.4,), "mudo": ()}[nome]
        for r in ondas:
            a = QPainterPath()
            a.arcMoveTo(QRectF(12.5 - r, 12 - r, r * 2, r * 2), -55)
            a.arcTo(QRectF(12.5 - r, 12 - r, r * 2, r * 2), -55, 110)
            p.addPath(_traco(a, 1.7))
        if nome == "mudo":                                  # o X no lugar das ondas
            for de, para in (((15.2, 9.2), (20.2, 14.2)), ((20.2, 9.2), (15.2, 14.2))):
                c = QPainterPath(); c.moveTo(*de); c.lineTo(*para)
                p.addPath(_traco(c, 1.8))
    return p


def _traco(caminho, espessura):
    """Transforma uma linha em area preenchivel (sem depender de caneta)."""
    from PySide6.QtGui import QPainterPathStroker
    s = QPainterPathStroker()
    s.setWidth(espessura)
    s.setCapStyle(Qt.RoundCap)
    s.setJoinStyle(Qt.RoundJoin)
    return s.createStroke(caminho)


def _ponta(x, y, giro=0):
    """Pontinha de seta triangular."""
    t = QPainterPath()
    t.moveTo(x, y - 3.1); t.lineTo(x + 4.4, y); t.lineTo(x, y + 3.1); t.closeSubpath()
    if giro:
        from PySide6.QtGui import QTransform
        t = QTransform().translate(x, y).rotate(giro).translate(-x, -y).map(t)
    return t


def icone_controle(nome, cor=PENA, tam=22):
    """QIcon vetorial de um controle do player."""
    pm = QPixmap(tam, tam)
    pm.fill(Qt.transparent)
    pt = QPainter(pm)
    pt.setRenderHint(QPainter.Antialiasing, True)
    pt.scale(tam / 24.0, tam / 24.0)
    pt.setPen(Qt.NoPen)
    pt.setBrush(QBrush(QColor(cor)))
    pt.drawPath(_caminhos_controle(nome))
    pt.end()
    return QIcon(pm)


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
