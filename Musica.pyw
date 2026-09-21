# -*- coding: utf-8 -*-
"""Player de musica do Roger — app desktop, sem navegador.
Le D:\\Music e as playlists .m3u de D:\\Music\\Playlists."""

import sys, os, io, re, random

from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QKeySequence, QShortcut, QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QLineEdit, QTableWidget, QTableWidgetItem, QLabel, QPushButton,
    QSlider, QHeaderView, QAbstractItemView, QFrame, QSizePolicy)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

MUSICA    = r"D:\Music"
PLAYLISTS = r"D:\Music\Playlists"
EXT       = (".mp3", ".m4a")

# ---------------------------------------------------------------- dados

def limpar(nome):
    """Nome de arquivo -> nome legivel."""
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

def sem_acento(t):
    """Busca tem que achar 'Coracao' digitado sem acento."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(t or ""))
                   if unicodedata.category(c) != "Mn").lower()

def mmss(seg):
    seg = max(0, int(seg or 0))
    return "%d:%02d" % (seg // 60, seg % 60)

def recurso(nome):
    """Caminho de um arquivo que acompanha o app — funciona solto E empacotado no .exe."""
    base = getattr(sys, "_MEIPASS", None)          # PyInstaller descompacta aqui
    if base:
        p = os.path.join(base, nome)
        if os.path.exists(p):
            return p
    if getattr(sys, "frozen", False):              # ao lado do executavel
        p = os.path.join(os.path.dirname(sys.executable), nome)
        if os.path.exists(p):
            return p
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), nome)


def cache_duracoes():
    """Duracoes ja medidas, para as faixas que nao vem de playlist (.m3u traz no #EXTINF)."""
    try:
        import json
        return {k.lower(): v for k, v in
                json.load(io.open(recurso("duracoes.json"), encoding="utf-8")).items()}
    except Exception:
        return {}

def carregar():
    faixas, idx, listas = [], {}, []
    dcache = cache_duracoes()

    def add(caminho):
        c = os.path.normpath(caminho)
        k = c.lower()
        if k in idx:
            return idx[k]
        if not os.path.isfile(c):
            return None
        idx[k] = len(faixas)
        nome = os.path.basename(c)
        faixas.append({"t": limpar(nome), "p": c, "d": dcache.get(nome.lower(), 0),
                       "b": sem_acento(limpar(nome))})
        return idx[k]

    if os.path.isdir(PLAYLISTS):
        for f in sorted(os.listdir(PLAYLISTS)):
            if not f.lower().endswith((".m3u", ".m3u8")):
                continue
            itens, dur = [], None
            for ln in io.open(os.path.join(PLAYLISTS, f), encoding="utf-8", errors="replace"):
                ln = ln.strip()
                if ln.startswith("#EXTINF:"):
                    try:    dur = int(ln.split(":")[1].split(",")[0])
                    except Exception: dur = None
                elif ln and not ln.startswith("#"):
                    n = add(ln)
                    if n is not None:
                        itens.append(n)
                        if dur: faixas[n]["d"] = dur
                    dur = None
            if itens:
                listas.append((os.path.splitext(f)[0], itens))

    soltas = []
    if os.path.isdir(MUSICA):
        for n in sorted(os.listdir(MUSICA)):
            if os.path.splitext(n)[1].lower() in EXT:
                c = os.path.normpath(os.path.join(MUSICA, n))
                if c.lower() not in idx:
                    soltas.append(add(c))
    if soltas:
        listas.append(("Fora das playlists", soltas))
    listas.insert(0, ("Todas as músicas", list(range(len(faixas)))))
    return faixas, listas

# ---------------------------------------------------------------- visual

import marca as M

ESTILO = """
QMainWindow, QWidget { background:%(noite)s; color:%(pena)s;
    font-family:"Segoe UI"; font-size:14px; }

#lado { background:%(painel)s; border-right:1px solid %(linha)s; }
QListWidget::item { margin:1px 0; }
#marcaNome { font-family:Georgia,"Times New Roman",serif; font-size:21px;
    color:%(pena)s; padding:0; }
#secao { color:%(fraca)s; font-size:10px; font-weight:700;
    letter-spacing:2.5px; padding:14px 20px 6px; }
QListWidget { background:transparent; border:none; outline:none; padding:0 10px; }
QListWidget::item { padding:9px 10px; border-radius:6px; color:#c8c2d6; }
QListWidget::item:hover { background:#1f1a2e; }
QListWidget::item:selected { background:#292139; color:%(pena)s; }

#busca { background:%(painel)s; border:1px solid %(linha)s; border-radius:8px;
    padding:8px 14px; color:%(pena)s; font-size:14px; }
#busca:focus { border:1px solid %(ambar)s; }

#titulo { font-family:Georgia,"Times New Roman",serif; font-size:24px;
    font-weight:400; padding:14px 4px 2px; color:%(pena)s; }
#sub { color:%(fraca)s; font-size:12px; padding:0 4px 10px; }

QTableWidget { background:transparent; border:none; outline:none;
    gridline-color:transparent; selection-background-color:#241d33; }
QTableWidget::item { padding:7px 6px; border:none; color:#dcd7e6; }
QTableWidget::item:hover { background:#1f1a2e; }
QTableWidget::item:selected { background:#241d33; color:%(pena)s; }
QHeaderView::section { background:%(noite)s; color:#7b7290; border:none;
    border-bottom:1px solid %(linha)s; padding:6px; font-size:10px;
    font-weight:700; letter-spacing:1.6px; }

#rodape { background:%(painel)s; border-top:1px solid %(linha)s; }
#rodape QLabel, #rodape QSlider, #rodape QWidget { background:transparent; }
#nomeAtual { font-size:14px; color:%(pena)s; }
#subAtual { font-size:12px; color:%(fraca)s; }

QPushButton { background:transparent; border:none; color:#dcd7e6;
    font-size:15px; border-radius:17px; }
QPushButton:hover { background:#241d33; }
QPushButton:checked { color:%(ambar)s; }
#rodape QPushButton#tocar { background:%(ambar)s; color:%(noite)s;
    border-radius:21px; font-size:16px; font-weight:700; }
#rodape QPushButton#tocar:hover { background:%(ambarClaro)s; }

QSlider::groove:horizontal { height:4px; background:#2a2338; border-radius:2px; }
QSlider::sub-page:horizontal { background:%(ambar)s; border-radius:2px; }
QSlider::handle:horizontal { background:%(pena)s; width:11px; height:11px;
    margin:-4px 0; border-radius:5px; }
QSlider::handle:horizontal:hover { background:#ffffff; }
#tempo { color:%(fraca)s; font-size:11px; }

QToolTip { background:%(painel)s; color:%(pena)s; border:1px solid %(linha)s;
    padding:5px 8px; }

QScrollBar:vertical { background:transparent; width:10px; margin:0; }
QScrollBar::handle:vertical { background:#2c2440; border-radius:5px; min-height:30px; }
QScrollBar::handle:vertical:hover { background:%(luar)s; }
QScrollBar::add-line, QScrollBar::sub-line { height:0; }
QScrollBar::add-page, QScrollBar::sub-page { background:transparent; }
""" % {"noite": M.NOITE, "painel": M.PAINEL, "linha": M.LINHA, "pena": M.PENA,
       "fraca": M.PENA_FRACA, "ambar": M.AMBAR, "ambarClaro": M.AMBAR_CLARO, "luar": M.LUAR}

class Player(QMainWindow):
    def __init__(self):
        super().__init__()
        self.faixas, self.listas = carregar()
        self.visiveis, self.ordem, self.pos, self.tocando = [], [], -1, -1

        self.setWindowTitle("Roxin")
        _ico = recurso("roxin.ico")
        self.setWindowIcon(QIcon(_ico) if os.path.isfile(_ico) else M.icone())
        self.resize(1080, 680)
        self.setMinimumSize(720, 460)

        self.saida = QAudioOutput(); self.saida.setVolume(0.8)
        self.mp = QMediaPlayer(); self.mp.setAudioOutput(self.saida)
        self.mp.positionChanged.connect(self._andou)
        self.mp.durationChanged.connect(self._durou)
        self.mp.mediaStatusChanged.connect(self._status)
        self.mp.playbackStateChanged.connect(self._estado)

        self._monta()
        self.lista_pls.setCurrentRow(0)
        self._abre(0)

    # -------------------------------------------------- montagem
    def _monta(self):
        raiz = QWidget(); self.setCentralWidget(raiz)
        vert = QVBoxLayout(raiz); vert.setContentsMargins(0,0,0,0); vert.setSpacing(0)

        corpo = QWidget(); linha = QHBoxLayout(corpo)
        linha.setContentsMargins(0,0,0,0); linha.setSpacing(0)
        vert.addWidget(corpo, 1)

        # ---- esquerda: playlists
        lado = QWidget(); lado.setObjectName("lado"); lado.setFixedWidth(230)
        cl = QVBoxLayout(lado); cl.setContentsMargins(0,0,0,10); cl.setSpacing(0)

        # assinatura da marca: passaro + nome
        assin = QWidget(); ca = QHBoxLayout(assin)
        ca.setContentsMargins(20, 20, 16, 14); ca.setSpacing(10)
        ave = QLabel(); ave.setPixmap(M.pixmap(26)); ave.setFixedSize(26, 26)
        nome = QLabel("Roxin"); nome.setObjectName("marcaNome")
        ca.addWidget(ave); ca.addWidget(nome); ca.addStretch(1)
        cl.addWidget(assin)

        sec = QLabel("PLAYLISTS"); sec.setObjectName("secao")
        cl.addWidget(sec)
        self.lista_pls = QListWidget()
        for nome, itens in self.listas:
            QListWidgetItem("%s      %d" % (nome, len(itens)), self.lista_pls)
        self.lista_pls.currentRowChanged.connect(self._abre)
        cl.addWidget(self.lista_pls, 1)
        linha.addWidget(lado)

        # ---- centro
        centro = QWidget(); cc = QVBoxLayout(centro)
        cc.setContentsMargins(26,10,20,0); cc.setSpacing(0)

        topo = QHBoxLayout(); topo.setContentsMargins(0,6,0,10)
        topo.addStretch(1)
        self.busca = QLineEdit(); self.busca.setObjectName("busca")
        self.busca.setPlaceholderText("Pesquisar música…")
        self.busca.setFixedWidth(430)
        self.busca.textChanged.connect(self._filtra)
        topo.addWidget(self.busca); topo.addStretch(1)
        cc.addLayout(topo)

        self.titulo = QLabel(); self.titulo.setObjectName("titulo"); cc.addWidget(self.titulo)
        self.sub = QLabel(); self.sub.setObjectName("sub"); cc.addWidget(self.sub)

        self.tab = QTableWidget(0, 2)
        self.tab.setHorizontalHeaderLabels(["MÚSICA", "TEMPO"])
        self.tab.verticalHeader().setVisible(False)
        self.tab.setShowGrid(False)
        self.tab.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tab.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tab.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tab.setFocusPolicy(Qt.StrongFocus)
        h = self.tab.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.Fixed)
        self.tab.setColumnWidth(1, 74)
        self.tab.cellDoubleClicked.connect(lambda r, c: self._toca_linha(r))
        cc.addWidget(self.tab, 1)
        linha.addWidget(centro, 1)

        # ---- rodape
        rod = QFrame(); rod.setObjectName("rodape"); rod.setFixedHeight(84)
        cr = QHBoxLayout(rod); cr.setContentsMargins(22,0,22,0); cr.setSpacing(16)

        infos = QVBoxLayout(); infos.setSpacing(3)
        infos.setContentsMargins(0, 0, 0, 0)
        self.nome_atual = QLabel("—"); self.nome_atual.setObjectName("nomeAtual")
        self.sub_atual  = QLabel("nada tocando"); self.sub_atual.setObjectName("subAtual")
        self.nome_atual.setMinimumWidth(170)
        for w in (self.nome_atual, self.sub_atual):
            w.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        infos.addStretch(1)
        infos.addWidget(self.nome_atual); infos.addWidget(self.sub_atual)
        infos.addStretch(1)
        cr.addLayout(infos, 3)

        def bt(txt, dica, w=34, obj=None):
            b = QPushButton(txt); b.setToolTip(dica); b.setFixedSize(w, w)
            b.setCursor(Qt.PointingHandCursor)
            if obj: b.setObjectName(obj)
            return b

        self.b_ant   = bt("\u25c2\u25c2", "Anterior")
        self.b_tocar = bt("\u25b6", "Tocar", 42, "tocar")
        self.b_prox  = bt("\u25b8\u25b8", "Próxima")
        self.b_ale   = bt("\u21c4", "Aleatório"); self.b_ale.setCheckable(True)
        self.b_rep   = bt("\u21bb", "Repetir");   self.b_rep.setCheckable(True)
        self.b_ant.clicked.connect(self._anterior)
        self.b_tocar.clicked.connect(self._play_pause)
        self.b_prox.clicked.connect(lambda: self._pula(1))
        self.b_ale.toggled.connect(self._aleatorio)
        for b in (self.b_ant, self.b_tocar, self.b_prox): cr.addWidget(b)

        self.t_atual = QLabel("0:00"); self.t_atual.setObjectName("tempo")
        self.t_total = QLabel("0:00"); self.t_total.setObjectName("tempo")
        self.barra = QSlider(Qt.Horizontal); self.barra.setRange(0, 0)
        self.barra.sliderMoved.connect(self.mp.setPosition)
        self.barra.setMinimumWidth(180)
        cr.addWidget(self.t_atual); cr.addWidget(self.barra, 4); cr.addWidget(self.t_total)

        cr.addWidget(self.b_ale); cr.addWidget(self.b_rep)
        self.vol = QSlider(Qt.Horizontal); self.vol.setRange(0, 100); self.vol.setValue(80)
        self.vol.setFixedWidth(90); self.vol.setToolTip("Volume")
        self.vol.valueChanged.connect(lambda v: self.saida.setVolume(v/100))
        vlb = QLabel("VOL"); vlb.setObjectName("tempo"); cr.addWidget(vlb); cr.addWidget(self.vol)
        vert.addWidget(rod)

        QShortcut(QKeySequence(Qt.Key_Space), self, self._play_pause)
        QShortcut(QKeySequence("Ctrl+F"), self, self.busca.setFocus)
        QShortcut(QKeySequence(Qt.Key_MediaNext), self, lambda: self._pula(1))
        QShortcut(QKeySequence(Qt.Key_MediaPrevious), self, self._anterior)
        QShortcut(QKeySequence(Qt.Key_Return), self.tab,
                  lambda: self._toca_linha(self.tab.currentRow()))

    # -------------------------------------------------- lista
    def _abre(self, i):
        if i < 0: return
        self.lista_idx = i
        self.busca.blockSignals(True); self.busca.clear(); self.busca.blockSignals(False)
        self._filtra()

    def _filtra(self):
        q = sem_acento(self.busca.text().strip())
        nome, itens = self.listas[self.lista_idx]
        self.visiveis = [n for n in itens if not q or q in self.faixas[n]["b"]]
        seg = sum(self.faixas[n]["d"] for n in self.visiveis)
        h, m = seg // 3600, (seg % 3600) // 60
        self.titulo.setText(nome)
        self.sub.setText("%d músicas%s" % (len(self.visiveis),
                         ("  ·  %sh %dmin" % (h, m)) if h else ("  ·  %dmin" % m) if m else ""))
        self.tab.setRowCount(len(self.visiveis))
        for lin, n in enumerate(self.visiveis):
            f = self.faixas[n]
            it = QTableWidgetItem(f["t"]); self.tab.setItem(lin, 0, it)
            t = QTableWidgetItem(mmss(f["d"]) if f["d"] else "—")
            t.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tab.setItem(lin, 1, t)
            if n == self.tocando:
                for c in (0, 1): self.tab.item(lin, c).setForeground(QColor("#e8834a"))

    # -------------------------------------------------- tocar
    def _toca_linha(self, lin):
        if lin < 0 or lin >= len(self.visiveis): return
        self.ordem = list(self.visiveis)
        self.pos = lin
        if self.b_ale.isChecked(): self._embaralha()
        self._toca()

    def _embaralha(self):
        atual = self.ordem[self.pos] if 0 <= self.pos < len(self.ordem) else None
        random.shuffle(self.ordem)
        if atual is not None: self.pos = self.ordem.index(atual)

    def _toca(self):
        if not (0 <= self.pos < len(self.ordem)): return
        self.tocando = self.ordem[self.pos]
        f = self.faixas[self.tocando]
        self.mp.setSource(QUrl.fromLocalFile(f["p"]))
        self.mp.play()
        self.nome_atual.setText(f["t"])
        self.sub_atual.setText(self.listas[self.lista_idx][0])
        self.setWindowTitle("%s — Roxin" % f["t"])
        self._filtra()

    def _play_pause(self):
        if self.mp.source().isEmpty():
            if self.visiveis: self._toca_linha(0)
            return
        if self.mp.playbackState() == QMediaPlayer.PlayingState: self.mp.pause()
        else: self.mp.play()

    def _pula(self, d):
        if not self.ordem: return
        self.pos = (self.pos + d) % len(self.ordem)
        self._toca()

    def _anterior(self):
        if self.mp.position() > 3000: self.mp.setPosition(0)
        else: self._pula(-1)

    def _aleatorio(self, on):
        if on and self.ordem: self._embaralha()

    # -------------------------------------------------- sinais
    def _andou(self, p):
        if not self.barra.isSliderDown(): self.barra.setValue(p)
        self.t_atual.setText(mmss(p/1000))

    def _durou(self, d):
        self.barra.setRange(0, d); self.t_total.setText(mmss(d/1000))

    def _estado(self, e):
        self.b_tocar.setText("\u275a\u275a" if e == QMediaPlayer.PlayingState else "\u25b6")

    def _status(self, s):
        if s == QMediaPlayer.EndOfMedia:
            if self.b_rep.isChecked():
                self.mp.setPosition(0); self.mp.play()
            else:
                self._pula(1)


def identidade_no_windows():
    """Sem isto o Windows agrupa a janela sob o pythonw.exe e mostra "Python"
    na barra de tarefas. O AppUserModelID da ao Roxin um lugar proprio."""
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Roger.Roxin.Player")
        return True
    except Exception:
        return False


if __name__ == "__main__":
    identidade_no_windows()
    app = QApplication(sys.argv)
    app.setStyleSheet(ESTILO)
    j = Player(); j.show()
    M.pintar_barra_titulo(j)      # barra de titulo na cor do app, nao no verde do Windows
    sys.exit(app.exec())
