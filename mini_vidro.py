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

# O filtro e o CSS sao os da skill liquid-glass (assets/liquid-glass.css e a demo
# ideias/liquid-glass-real.html): feTurbulence fractalNoise 0.006/0.009, 2 oitavas,
# semente 12, feGaussianBlur 2 e feDisplacementMap scale 42, com blur(3px)
# saturate(1.7). Nao mexer nesses numeros sem ele aprovar: sao os calibrados.
PAGINA = """<!doctype html>
<meta charset="utf-8">
<style>
  :root{
    --lg-tint: 255,255,255;
    --lg-tint-op: .05;
    --lg-radius: 18px;
    --lg-blur: 3px;
    --lg-sat: 1.7;
    --lg-border: rgba(255,255,255,.22);
    --lg-highlight: rgba(255,255,255,.55);
    --pena: #e9e5ef;
    --roxo: #a77cf0;
    --noite: #0f0c16;
  }
  html,body{margin:0;height:100%;background:transparent;overflow:hidden;
    font-family:"Segoe UI","Yu Gothic UI",sans-serif;-webkit-user-select:none;user-select:none}

  /* a foto do que esta atras da janela: e o "fundo" que o vidro refrata */
  #atras{position:fixed;inset:0;background-size:cover;background-position:center;
    border-radius:var(--lg-radius)}

  /* ---- o vidro: classe .lg da skill, com a variante que refrata ---- */
  .lg{
    position:fixed;inset:0;
    border-radius:var(--lg-radius);
    background:rgba(var(--lg-tint), calc(var(--lg-tint-op) - .01));
    border:1px solid var(--lg-border);
    box-shadow:
      inset 0 1px 1px var(--lg-highlight),
      inset 0 -1px 1px rgba(255,255,255,.12),
      inset 0 0 22px rgba(255,255,255,.08),
      0 20px 50px rgba(0,0,0,.40);
    overflow:hidden;isolation:isolate;
    -webkit-backdrop-filter:blur(var(--lg-blur)) saturate(var(--lg-sat)) url(#lente);
    backdrop-filter:blur(var(--lg-blur)) saturate(var(--lg-sat)) url(#lente);
    display:flex;align-items:center;gap:12px;padding:0 12px 0 12px;
    box-sizing:border-box;
  }
  /* aberracao cromatica na borda */
  .lg::before{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;
    box-shadow:inset 1.5px 0 2px rgba(255,0,80,.45), inset -1.5px 0 2px rgba(0,180,255,.45);
    mix-blend-mode:screen;opacity:.55}

  #capa{width:50px;height:50px;border-radius:9px;object-fit:cover;flex:0 0 auto;
    box-shadow:0 2px 10px rgba(0,0,0,.45);background:rgba(255,255,255,.06)}
  .meio{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;gap:6px;z-index:2}
  #nome{color:var(--pena);font-size:13px;white-space:nowrap;overflow:hidden;
    text-overflow:ellipsis;text-shadow:0 1px 3px rgba(0,0,0,.55)}
  #trilha{height:3px;border-radius:2px;background:rgba(255,255,255,.22);cursor:pointer}
  #cheio{height:100%;width:0;border-radius:2px;background:var(--roxo)}

  .ctrl{display:flex;align-items:center;gap:6px;flex:0 0 auto;z-index:2}
  button{border:none;background:transparent;cursor:pointer;padding:0;
    width:28px;height:28px;border-radius:14px;display:grid;place-items:center;
    transition:background .15s}
  button:hover{background:rgba(255,255,255,.16)}
  button svg{width:15px;height:15px;fill:var(--pena)}
  #toc{width:32px;height:32px;border-radius:16px;background:var(--roxo)}
  #toc:hover{background:#bb97f6}
  #toc svg{fill:var(--noite);width:14px;height:14px}
</style>

<div id="atras"></div>

<section class="lg" id="vidro">
  <img id="capa" alt="">
  <div class="meio">
    <div id="nome">—</div>
    <div id="trilha"><div id="cheio"></div></div>
  </div>
  <div class="ctrl">
    <button id="ant" title="Anterior">
      <svg viewBox="0 0 16 16"><path d="M4 2h2v12H4zM14 2v12L6.5 8z"/></svg>
    </button>
    <button id="toc" title="Tocar / pausar">
      <svg id="icone" viewBox="0 0 16 16"><path d="M4 2l10 6-10 6z"/></svg>
    </button>
    <button id="prox" title="Próxima">
      <svg viewBox="0 0 16 16"><path d="M10 2h2v12h-2zM2 2l7.5 6L2 14z"/></svg>
    </button>
  </div>
</section>

<svg width="0" height="0" style="position:absolute">
  <filter id="lente" x="-20%" y="-20%" width="140%" height="140%">
    <feTurbulence type="fractalNoise" baseFrequency="0.006 0.009" numOctaves="2"
                  seed="12" result="n"/>
    <feGaussianBlur in="n" stdDeviation="2" result="nb"/>
    <feDisplacementMap in="SourceGraphic" in2="nb" scale="42"
                       xChannelSelector="R" yChannelSelector="G"/>
  </filter>
</svg>

<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
  var ponte = null;
  window.addEventListener("load", function () {
    if (typeof QWebChannel === "undefined") return;
    new QWebChannel(qt.webChannelTransport, function (canal) {
      ponte = canal.objects.ponte;
      ponte.pronto();
    });
  });

  document.getElementById("ant").onclick  = function(e){ e.stopPropagation(); ponte && ponte.anterior(); };
  document.getElementById("toc").onclick  = function(e){ e.stopPropagation(); ponte && ponte.tocar(); };
  document.getElementById("prox").onclick = function(e){ e.stopPropagation(); ponte && ponte.proxima(); };

  // clicar na trilha pula para aquele ponto
  document.getElementById("trilha").addEventListener("pointerdown", function(e){
    e.stopPropagation();
    var r = this.getBoundingClientRect();
    ponte && ponte.buscar(Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)));
  });

  // arrastar a janelinha: o WebEngine come o mouse, entao o arraste vai pela ponte
  var arrastando = false;
  document.getElementById("vidro").addEventListener("pointerdown", function(e){
    if (e.target.closest("button") || e.target.closest("#trilha")) return;
    arrastando = true;
    ponte && ponte.pegar(e.screenX, e.screenY);
    this.setPointerCapture(e.pointerId);
  });
  document.addEventListener("pointermove", function(e){
    if (arrastando && ponte) ponte.arrastar(e.screenX, e.screenY);
  });
  document.addEventListener("pointerup", function(){
    if (!arrastando) return;
    arrastando = false;
    ponte && ponte.soltar();
  });

  // chamado pelo Python
  window.atualizar = function (d) {
    if (d.nome !== undefined) { document.getElementById("nome").textContent = d.nome;
                                document.getElementById("nome").title = d.nome; }
    if (d.capa !== undefined) document.getElementById("capa").src = d.capa;
    if (d.pct  !== undefined) document.getElementById("cheio").style.width = (d.pct * 100) + "%";
    if (d.tocando !== undefined) {
      document.getElementById("icone").innerHTML = d.tocando
        ? '<path d="M3.5 2h3.2v12H3.5zM9.3 2h3.2v12H9.3z"/>'
        : '<path d="M4 2l10 6-10 6z"/>';
    }
    if (d.atras !== undefined) {
      document.getElementById("atras").style.backgroundImage = "url('" + d.atras + "')";
    }
  };
</script>
"""


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
