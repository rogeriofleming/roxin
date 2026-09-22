# -*- coding: utf-8 -*-
"""Miniplayer do Roxin com o LIQUID GLASS do cofre — o codigo que o Roger aprovou.

Por que este arquivo existe: a skill `liquid-glass` do cofre e WEB (backdrop-filter
+ filtro SVG feTurbulence/feDisplacementMap). Qt nao tem backdrop-filter nem filtro
SVG sobre o que esta atras da janela, e a primeira tentativa foi reimplementar o
efeito na mao em QPainter — saiu pior ("o liquido ta mto mal feito", 22/09/2026).
A correcao nao e melhorar a imitacao: e RODAR o codigo aprovado. Entao a janelinha
inteira e uma pagina, num QWebEngineView, com o CSS e o filtro da skill.

Duas coisas que isso obriga:
  - o "fundo" do backdrop-filter e o que esta atras do ELEMENTO, nao atras da
    janela: por isso uma foto da tela entra na pagina como camada de baixo. A foto
    e tirada com a janelinha escondida, senao ela fotografa a si mesma;
  - widget Qt NAO aparece sobre o QWebEngineView (medido em 22/09/2026): os
    controles tambem tem que ser HTML, e falam com o Python por QWebChannel.

Custo declarado: o WebEngine sobe um processo Chromium — cerca de 100-150 MB de
RAM e um segundo a mais para a janelinha aparecer na primeira vez.
"""

import base64
import io
import json
import os

from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot, QPoint
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

# ---------------------------------------------------------------- a pagina

# A pagina (shader WebGL + calibracao aprovada) vive em mini_pagina.py.
from mini_pagina import PAGINA          # o HTML/WebGL do vidro mora la


class Ponte(QObject):
    """O que o HTML pode pedir ao Python. Nada alem disto."""

    def __init__(self, mini):
        super().__init__()
        self.mini = mini

    @Slot()
    def pronto(self):
        self.mini._pagina_pronta = True
        self.mini.mandar_tudo()

    @Slot()
    def voltar(self):
        """Traz o Roxin para a frente e desmancha a janelinha na hora."""
        pai = self.mini.pai
        self.mini.hide()
        if pai.isMinimized():
            pai.showNormal()
        pai.show()
        pai.raise_()
        pai.activateWindow()

    @Slot()
    def anterior(self):
        self.mini.pai._anterior()

    @Slot()
    def tocar(self):
        self.mini.pai._play_pause()

    @Slot()
    def proxima(self):
        self.mini.pai._pula(1)

    @Slot(float)
    def buscar(self, fracao):
        dur = self.mini.pai.mp.duration()
        if dur > 0:
            self.mini.pai.mp.setPosition(int(dur * fracao))

    @Slot(int, int)
    def pegar(self, x, y):
        self.mini._pegou = (QPoint(x, y), self.mini.pos())

    @Slot(int, int)
    def arrastar(self, x, y):
        if not self.mini._pegou:
            return
        inicio, onde = self.mini._pegou
        self.mini.move(onde + QPoint(x - inicio.x(), y - inicio.y()))

    @Slot()
    def soltar(self):
        if self.mini._pegou:
            self.mini._pegou = None
            self.mini.pai._guarda_lugar_do_mini()
            self.mini.fotografar_atras()


class MiniVidro(QWidget):
    """A janelinha. O vidro e HTML; o player continua sendo o Qt."""

    LARGURA, ALTURA = 400, 74

    def __init__(self, pai):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.pai = pai
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(self.LARGURA, self.ALTURA)
        self._pegou = None
        self._pagina_pronta = False
        self._atras_uri = ""
        self._dados = {"nome": "—", "capa": "", "pct": 0.0, "tocando": False}

        c = QVBoxLayout(self)
        c.setContentsMargins(0, 0, 0, 0)
        self.view = QWebEngineView(self)
        self.view.page().setBackgroundColor(Qt.transparent)
        self.canal = QWebChannel(self.view.page())
        self.ponte = Ponte(self)
        self.canal.registerObject("ponte", self.ponte)
        self.view.page().setWebChannel(self.canal)
        self.view.setHtml(PAGINA)      # a foto e a capa entram como data URI
        c.addWidget(self.view)

    # ---------------------------------------------------------------- fundo
    def fotografar_atras(self):
        """Foto do que esta atras, tirada com a janelinha ESCONDIDA — se ela
        estiver na tela, fotografa a si mesma e o vidro vira eco."""
        tela = self.screen() or QApplication.primaryScreen()
        estava = self.isVisible()
        if estava:
            self.setWindowOpacity(0.0)
            QApplication.processEvents()
        g = self.geometry()
        try:
            foto = tela.grabWindow(0, g.x(), g.y(), g.width(), g.height())
            buf = io.BytesIO()
            img = foto.toImage()
            from PySide6.QtCore import QBuffer, QByteArray
            ba = QByteArray()
            qb = QBuffer(ba)
            qb.open(QBuffer.WriteOnly)
            img.save(qb, "PNG")
            self._atras_uri = "data:image/png;base64," + base64.b64encode(
                bytes(ba)).decode("ascii")
        except Exception:
            self._atras_uri = ""
        if estava:
            self.setWindowOpacity(1.0)
        self._mandar({"atras": self._atras_uri})

    # ---------------------------------------------------------------- dados
    def _mandar(self, dados):
        if not self._pagina_pronta:
            return
        self.view.page().runJavaScript(
            "window.atualizar(%s)" % json.dumps(dados, ensure_ascii=False))

    def mandar_tudo(self):
        d = dict(self._dados)
        if self._atras_uri:
            d["atras"] = self._atras_uri
        self._mandar(d)

    def poe_faixa(self, nome, pixmap_capa):
        self._dados["nome"] = nome
        self._dados["capa"] = self._uri_do_pixmap(pixmap_capa)
        self._mandar({"nome": self._dados["nome"], "capa": self._dados["capa"]})

    def poe_progresso(self, pos, dur):
        pct = (pos / dur) if dur else 0.0
        self._dados["pct"] = pct
        self._mandar({"pct": pct})

    def poe_estado(self, tocando):
        self._dados["tocando"] = bool(tocando)
        self._mandar({"tocando": bool(tocando)})

    @staticmethod
    def _uri_do_pixmap(pm):
        if pm is None or pm.isNull():
            return ""
        from PySide6.QtCore import QBuffer, QByteArray
        ba = QByteArray()
        qb = QBuffer(ba)
        qb.open(QBuffer.WriteOnly)
        pm.toImage().save(qb, "PNG")
        return "data:image/png;base64," + base64.b64encode(bytes(ba)).decode("ascii")

    # ---------------------------------------------------------------- lugar
    def no_cantinho(self):
        tela = self.screen() or QApplication.primaryScreen()
        a = tela.availableGeometry()
        self.move(a.right() - self.width() - 18, a.bottom() - self.height() - 18)
