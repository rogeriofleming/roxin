# -*- coding: utf-8 -*-
"""Player de musica do Roger — app desktop, sem navegador.
Le D:\\Music e as playlists .m3u de D:\\Music\\Playlists."""

import sys, os, io, re, random

from PySide6.QtCore import (Qt, QUrl, QSize, QThread, Signal, QEvent, QPoint,
                            QFileSystemWatcher, QTimer, QPropertyAnimation,
                            QEasingCurve, QAbstractAnimation)
from PySide6.QtGui import (QKeySequence, QShortcut, QIcon, QPixmap, QPainter, QColor,
                           QFont, QPixmapCache, QPainterPath, QLinearGradient,
                           QRadialGradient, QPen, QBrush)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QLineEdit, QTableWidget, QTableWidgetItem, QLabel, QPushButton,
    QSlider, QHeaderView, QAbstractItemView, QFrame, QSizePolicy,
    QGraphicsOpacityEffect, QComboBox, QCheckBox)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices

MUSICA    = r"D:\Music"
PLAYLISTS = r"D:\Music\Playlists"
EXT       = (".mp3", ".m4a")
CAPA_LISTA  = 40          # capinha ao lado de cada musica
CAPA_RODAPE = 58          # capa da que esta tocando, no canto
CAPA_FILA   = 30          # capinha dentro do painel "a seguir"
CAPA_MINI   = 50          # capa dentro do miniplayer sobreposto

# Padrao de movimento (skill motion-design, arquetipo Premium): uma curva de
# assinatura e tres duracoes. Nada de inventar tempo caso a caso.
MOV_CLIQUE  = 150         # feedback de clique
MOV_PADRAO  = 260         # movimento de painel
MOV_CONTEXTO = 380        # troca de contexto (abrir/fechar o palco)


def suave(alvo, prop, de, para, ms=MOV_PADRAO, curva=QEasingCurve.OutCubic, fim=None):
    """Animacao com a curva de assinatura do app. Guardada no proprio objeto para
    o coletor de lixo do Python nao mata-la no meio (bug classico do Qt)."""
    a = QPropertyAnimation(alvo, prop.encode() if isinstance(prop, str) else prop)
    a.setDuration(ms)
    a.setStartValue(de)
    a.setEndValue(para)
    a.setEasingCurve(curva)
    if fim:
        a.finished.connect(fim)
    guardadas = getattr(alvo, "_animacoes", None)
    if guardadas is None:
        guardadas = []
        alvo._animacoes = guardadas
    guardadas.append(a)
    a.finished.connect(lambda: guardadas.remove(a) if a in guardadas else None)
    a.start(QAbstractAnimation.DeleteWhenStopped)
    return a


def pulsa(widget, ms=MOV_CLIQUE):
    """Feedback de clique: o icone AFUNDA e volta. Opacidade de 150ms nao se ve —
    movimento se ve. iconSize nao participa do layout, entao nada empurra a tela."""
    if not hasattr(widget, "iconSize"):
        return
    cheio = widget.iconSize()
    if cheio.width() < 8:
        return
    menor = QSize(max(6, int(cheio.width() * 0.76)), max(6, int(cheio.height() * 0.76)))
    suave(widget, "iconSize", cheio, menor, ms // 2, QEasingCurve.OutCubic,
          fim=lambda: suave(widget, "iconSize", menor, cheio,
                            ms, QEasingCurve.OutBack))

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

# nome da playlist -> arquivo .m3u de onde ela veio (so as de verdade)
ARQUIVO_DA_LISTA = {}

VIRTUAIS = ("Todas as músicas", "Fora das playlists")


def carregar():
    faixas, idx, listas = [], {}, []
    ARQUIVO_DA_LISTA.clear()
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
            itens, dur, titulo = [], None, None
            for ln in io.open(os.path.join(PLAYLISTS, f), encoding="utf-8", errors="replace"):
                ln = ln.strip()
                if ln.startswith("#EXTINF:"):
                    try:    dur = int(ln.split(":")[1].split(",")[0])
                    except Exception: dur = None
                    # o nome escrito na playlist manda: e como o Roger chama a musica
                    titulo = ln.split(",", 1)[1].strip() if "," in ln else None
                elif ln and not ln.startswith("#"):
                    n = add(ln)
                    if n is not None:
                        itens.append(n)
                        if dur: faixas[n]["d"] = dur
                        if titulo:
                            faixas[n]["t"] = titulo
                            faixas[n]["b"] = sem_acento(titulo)
                    dur = titulo = None
            nome_lista = os.path.splitext(f)[0]
            ARQUIVO_DA_LISTA[nome_lista] = os.path.join(PLAYLISTS, f)
            if itens:
                listas.append((nome_lista, itens))

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

# ---------------------------------------------------------------- baixar (Anzol)

ANZOL_ERRO = None          # por que o motor nao carregou, se nao carregou


def anzol():
    """Devolve o modulo `nucleo` do Anzol, ou None se nao der.
    Carregado so na primeira vez que o Roger abre a aba de baixar: importar
    yt_dlp no arranque atrasaria o app inteiro por uma funcao que ele quase
    nao usa."""
    global ANZOL_ERRO
    mod = globals().get("_ANZOL")
    if mod is not None:
        return mod
    for pasta in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "anzol"),
                  recurso("anzol"),
                  r"D:\Claude Code\Claude Mestre v2\projetos\anzol"):
        try:
            if not os.path.isfile(os.path.join(pasta, "nucleo.py")):
                continue
            if pasta not in sys.path:
                sys.path.insert(0, pasta)
            import nucleo as _n
            globals()["_ANZOL"] = _n
            return _n
        except Exception as e:
            ANZOL_ERRO = str(e)
    if ANZOL_ERRO is None:
        ANZOL_ERRO = "nao achei o nucleo.py do Anzol"
    return None


# ---------------------------------------------------------------- escrever playlist

def pasta_backup():
    p = os.path.join(os.path.dirname(CP.pasta_cache()), "backup_playlists")
    os.makedirs(p, exist_ok=True)
    return p


def guardar_copia(arquivo):
    """Copia o .m3u antes de reescrever — desfazer sem depender de memoria."""
    if not os.path.isfile(arquivo):
        return None
    import shutil, time as _t
    destino = os.path.join(pasta_backup(), "%s_%s.m3u" % (
        os.path.splitext(os.path.basename(arquivo))[0], _t.strftime("%Y%m%d-%H%M%S")))
    try:
        shutil.copy2(arquivo, destino)
        return destino
    except Exception:
        return None


def escrever_m3u(arquivo, entradas):
    """entradas: [(titulo, duracao_em_segundos, caminho), ...].
    Formato igual ao que ja existia na pasta: #EXTM3U, CRLF, UTF-8 sem BOM."""
    guardar_copia(arquivo)
    linhas = ["#EXTM3U"]
    for titulo, dur, caminho in entradas:
        linhas.append("#EXTINF:%d,%s" % (int(dur or 0), titulo))
        linhas.append(caminho)
    io.open(arquivo, "w", encoding="utf-8", newline="\r\n").write("\n".join(linhas) + "\n")


# ---------------------------------------------------------------- capas

import capas as CP

MOLDURA_FUNDO = "#221c33"      # o quadrado atras da capa (a imagem se encaixa dentro)
MOLDURA_CANTO = 5

def arquivo_ajustes():
    return os.path.join(os.path.dirname(CP.pasta_cache()), "ajustes.json")


def ler_ajustes():
    try:
        import json
        return json.load(io.open(arquivo_ajustes(), encoding="utf-8"))
    except Exception:
        return {}


def gravar_ajustes(d):
    try:
        import json
        io.open(arquivo_ajustes(), "w", encoding="utf-8").write(
            json.dumps(d, ensure_ascii=False, indent=1))
    except Exception:
        pass          # preferencia nao e dado critico: falhar aqui nao quebra o app


def capa_livre(nome_arquivo, lado):
    """Capa grande no aspecto REAL da imagem (o acervo e cheio de 16:9): a moldura
    quadrada, que alinha bem a lista, aqui deixaria duas tarjas vazias enormes.
    Sem capa, devolve o quadrado com o passaro."""
    ck = "roxin:capagrande:%s:%d" % (nome_arquivo.lower(), lado)
    pm = QPixmapCache.find(ck)
    if pm:
        return pm
    arq = os.path.join(CP.pasta_cache(), CP.chave(nome_arquivo))
    dentro = QPixmap(arq) if os.path.isfile(arq) else QPixmap()
    if dentro.isNull():
        return capa(nome_arquivo, lado)
    d = dentro.scaled(lado, lado, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pm = QPixmap(d.size())
    pm.fill(Qt.transparent)
    pt = QPainter(pm)
    pt.setRenderHint(QPainter.Antialiasing, True)
    forma = QPainterPath()
    forma.addRoundedRect(0, 0, d.width(), d.height(), 14, 14)
    pt.setClipPath(forma)
    pt.drawPixmap(0, 0, d)
    pt.setClipping(False)
    pt.setPen(QColor(255, 255, 255, 28))
    pt.drawPath(forma)
    pt.end()
    QPixmapCache.insert(ck, pm)
    return pm


class Capeiro(QThread):
    """Gera as miniaturas em segundo plano na primeira vez que o app abre numa
    maquina — sem isso, no notebook toda musica apareceria sem capa."""
    pronto = Signal(int)

    def run(self):
        try:
            com, _sem, _erro = CP.gerar(quieto=True)
            self.pronto.emit(com)
        except Exception:
            self.pronto.emit(0)      # falhou: fica so o passaro, o app nao quebra


def capa(nome_arquivo, tam, canto=None):
    """Moldura QUADRADA de tam x tam com a capa encaixada dentro, sem cortar.
    Quem nao tem capa recebe o passaro esmaecido. Fica em cache do Qt."""
    canto = max(MOLDURA_CANTO, tam // 26) if canto is None else canto
    ck = "roxin:capa:%s:%d:%d" % (nome_arquivo.lower(), tam, canto)
    pm = QPixmapCache.find(ck)
    if pm:
        return pm
    pm = QPixmap(tam, tam)
    pm.fill(Qt.transparent)
    pt = QPainter(pm)
    pt.setRenderHint(QPainter.Antialiasing, True)
    cam = QPainterPath()
    cam.addRoundedRect(0, 0, tam, tam, canto, canto)
    pt.fillPath(cam, QColor(MOLDURA_FUNDO))
    arq = os.path.join(CP.pasta_cache(), CP.chave(nome_arquivo))
    dentro = QPixmap(arq) if os.path.isfile(arq) else QPixmap()
    if not dentro.isNull():
        pt.setClipPath(cam)
        d = dentro.scaled(tam, tam, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pt.drawPixmap((tam - d.width()) // 2, (tam - d.height()) // 2, d)
    else:
        # o passaro ocupa 66% numa capinha de 40px, mas so ~22% num card de 470:
        # ampliado, a silhueta chapada fica crua. Proporcao cai com o tamanho.
        if tam <= 64:
            fracao = 0.66
        elif tam >= 360:
            fracao = 0.22
        else:
            fracao = 0.66 + (0.22 - 0.66) * (tam - 64) / float(360 - 64)
        a = int(tam * fracao)
        pt.translate((tam - a) / 2.0, (tam - a) / 2.0)
        M.desenhar(pt, a, "#5b4f86", olho=False)
    pt.end()
    QPixmapCache.insert(ck, pm)
    return pm


# ---------------------------------------------------------------- visual

import marca as M

ESTILO = """
QMainWindow, QWidget { background:%(noite)s; color:%(pena)s;
    font-family:"Segoe UI","Yu Gothic UI","Meiryo","MS UI Gothic",sans-serif; font-size:14px; }

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
QTableWidget::item { padding:4px 6px; border:none; color:#dcd7e6; }
QTableWidget::item:hover { background:#1f1a2e; }
QTableWidget::item:selected { background:#241d33; color:%(pena)s; }
QHeaderView::section { background:%(noite)s; color:#7b7290; border:none;
    border-bottom:1px solid %(linha)s; padding:6px; font-size:10px;
    font-weight:700; letter-spacing:1.6px; }

#fila { background:%(painel)s; border-left:1px solid %(linha)s; }
#fila QLabel { background:transparent; }
#fila QListWidget { padding:0 6px; }
#fila QListWidget::item { padding:7px 10px; margin-right:4px; border-radius:6px; }
#botaoFila { color:%(fraca)s; font-size:12px; padding:0 12px; border-radius:14px;
    border:1px solid %(linha)s; }
#botaoFila:hover { color:%(pena)s; background:#241d33; }
#botaoFila:checked { color:%(ambar)s; border:1px solid %(ambar)s; background:transparent; }
#limpaFila { color:%(fraca)s; font-size:11px; padding:0 10px; border-radius:12px; }
#limpaFila:hover { color:%(pena)s; background:#241d33; }
#dicaFila { color:%(fraca)s; font-size:12px; padding:14px 18px; }

#botaoBaixar { background:%(painel)s; border:1px solid %(linha)s; border-radius:8px;
    color:%(fraca)s; font-size:13px; padding:0 16px; }
#botaoBaixar:hover { color:%(pena)s; border:1px solid %(luar)s; }
#botaoBaixar:checked { color:%(ambar)s; border:1px solid %(ambar)s; }

#pescaria { background:%(painel)s; border:1px solid %(linha)s; border-radius:10px; }
#pescaria QLabel { background:transparent; }
#qualidade { background:%(noite)s; border:1px solid %(linha)s; border-radius:8px;
    padding:6px 10px; color:%(pena)s; }
#qualidade QAbstractItemView { background:%(painel)s; border:1px solid %(linha)s;
    selection-background-color:#292139; color:%(pena)s; }
#pescarBotao { background:%(ambar)s; color:%(noite)s; border:none; border-radius:16px;
    padding:0 20px; font-size:13px; font-weight:600; }
#pescarBotao:hover { background:%(ambarClaro)s; }
#pescarBotao:disabled { background:#3a3252; color:%(fraca)s; }
#naPlaylist { color:%(fraca)s; font-size:12px; }
#naPlaylist:disabled { color:#5c5570; }
#credito { color:#5c5570; font-size:10px; }
#recadoPesca { color:%(fraca)s; font-size:12px; }

#palco { background:%(noite)s; }
#palco QLabel { background:transparent; }
#nomePalco { font-family:Georgia,"Times New Roman",serif; font-size:30px;
    color:%(pena)s; padding:0 20px; }
#subPalco { color:%(fraca)s; font-size:13px; letter-spacing:1.4px; }
#palcoBotao { background:transparent; border:none; border-radius:25px; }
#palcoBotao:hover { background:#241d33; }
#palcoTocar { background:%(ambar)s; border:none; border-radius:34px; }
#palcoTocar:hover { background:%(ambarClaro)s; }

#mini { background:transparent; }
#mini QLabel { background:transparent; }
#miniNome { color:%(pena)s; font-size:13px; }
#miniBotao { background:transparent; border:none; border-radius:14px; }
#miniBotao:hover { background:rgba(255,255,255,26); }
#miniTocar { background:%(ambar)s; border-radius:16px; }
#miniTocar:hover { background:%(ambarClaro)s; }
#miniBarra { background:transparent; border:none; }
#miniBarra::groove:horizontal { height:3px; background:#332a47; border-radius:2px;
    margin:0; }
#miniBarra::sub-page:horizontal { background:%(ambar)s; border-radius:2px; }
#miniBarra::add-page:horizontal { background:#332a47; border-radius:2px; }
#miniBarra::handle:horizontal { background:%(pena)s; width:8px; height:8px;
    margin:-3px 0; border-radius:4px; }

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

def vidro_do_windows(janela):
    """Liga o acrilico do DWM: e ele que desfoca o que esta ATRAS da janela.
    Qt nao tem backdrop-filter — sem isto, "vidro" seria so pintura chapada.
    Tenta o atributo do Windows 11 e, se falhar, a API de composicao do Win10.
    Devolve o caminho que funcionou, ou None."""
    import ctypes
    try:
        hwnd = int(janela.winId())
        dwm = ctypes.windll.dwmapi
    except Exception:
        return None

    try:      # a janelinha e escura: avisar o DWM, senao a moldura sai clara
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
    except Exception:
        pass

    # Medido nesta maquina em 22/09/2026, com as quatro APIs lado a lado sobre um
    # fundo colorido (tmp/capas/vidro_4_caminhos.png): as tres "modernas"
    # RETORNAM SUCESSO e nao desfocam nada — a janela fica opaca. Quem desfoca de
    # verdade numa janela translucida do Qt e a antiga DwmEnableBlurBehindWindow.
    # Por isso ela vem PRIMEIRO: codigo de retorno aqui nao prova efeito.
    try:
        class MARGENS_BLUR(ctypes.Structure):
            _fields_ = [("dwFlags", ctypes.c_uint), ("fEnable", ctypes.c_int),
                        ("hRgnBlur", ctypes.c_void_p),
                        ("fTransitionOnMaximized", ctypes.c_int)]
        bb = MARGENS_BLUR(0x1, 1, None, 0)       # DWM_BB_ENABLE, janela toda
        if dwm.DwmEnableBlurBehindWindow(hwnd, ctypes.byref(bb)) == 0:
            return "blur do DWM"
    except Exception:
        pass

    try:      # reserva: acrilico do Win11 (nao desfocou aqui, mas pode em outra maquina)
        if dwm.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(ctypes.c_int(3)), 4) == 0:
            return "acrilico do Windows 11"
    except Exception:
        pass
    return None


class Clicavel(QWidget):
    """Area que avisa quando e clicada — o canto do rodape que abre o palco."""
    clicado = Signal()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.clicado.emit()


class Palco(QWidget):
    """A capa grande. Clique em qualquer lugar (fora dos botoes) volta ao normal:
    botao e barra consomem o clique antes, entao nao fecham sem querer."""
    clicado = Signal()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.clicado.emit()


def rolagem_suave(area, ms=260):
    """Roda do mouse animada, em vez do salto seco do Qt.

    Duas coisas: rolar POR PIXEL (o padrao do Qt rola por item, e item de 50px
    salta) e animar o caminho ate o destino com a curva de assinatura do app.
    Guarda a animacao no proprio widget para o coletor nao mata-la no meio.
    """
    area.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    barra = area.verticalScrollBar()

    def roda(ev):
        passos = ev.angleDelta().y() / 120.0
        if not passos:
            return
        alvo = barra.value() - int(passos * 3 * max(18, barra.singleStep() or 18))
        alvo = max(barra.minimum(), min(barra.maximum(), alvo))
        if alvo == barra.value():
            return
        a = getattr(area, "_anim_rolagem", None)
        if a is not None:
            a.stop()
        a = QPropertyAnimation(barra, b"value")
        a.setDuration(ms)
        a.setStartValue(barra.value())
        a.setEndValue(alvo)
        a.setEasingCurve(QEasingCurve.OutCubic)
        area._anim_rolagem = a
        a.start(QAbstractAnimation.DeleteWhenStopped)
        ev.accept()

    area.wheelEvent = roda


class Tabela(QTableWidget):
    """QTableWidget que avisa quando o Roger arrasta uma linha para outro lugar.
    O QTableWidget puro move as celulas e nao diz o que aconteceu — sem este
    sinal nao havia como gravar a nova ordem no .m3u."""
    moveu = Signal(int, int)          # de, para

    def dropEvent(self, ev):
        de = self.currentRow()
        alvo = self.indexAt(ev.position().toPoint())
        para = alvo.row() if alvo.isValid() else self.rowCount() - 1
        if de >= 0 and para >= 0 and de != para:
            ev.setDropAction(Qt.IgnoreAction)
            ev.accept()
            self.moveu.emit(de, para)
        else:
            ev.ignore()


class Mini(QWidget):
    """Miniplayer sobreposto: capa, nome e os tres controles.

    Qt.Tool tira da barra de tarefas; WindowStaysOnTop deixa por cima dos outros
    apps; WA_ShowWithoutActivating faz aparecer SEM roubar o foco de quem o Roger
    esta usando. Sem moldura, entao o arraste e feito na mao."""

    def __init__(self, pai):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.pai = pai
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)   # canto redondo de verdade
        self.setObjectName("mini")
        self.setFixedSize(400, 74)
        self._arrasto = None
        self._vidro = None            # qual caminho de acrilico pegou
        self._atras = None            # foto do que esta atras (para refratar)
        self._fase = 0.0              # fase da onda: e o que faz parecer liquido
        self._onda = QTimer(self)
        self._onda.setInterval(33)    # ~30 quadros por segundo
        self._onda.timeout.connect(self._andar_onda)

        c = QHBoxLayout(self); c.setContentsMargins(12, 12, 10, 12); c.setSpacing(12)
        self.capa = QLabel(); self.capa.setFixedSize(CAPA_MINI, CAPA_MINI)
        c.addWidget(self.capa)

        meio = QVBoxLayout(); meio.setSpacing(3); meio.setContentsMargins(0, 2, 0, 2)
        self.nome = QLabel("—"); self.nome.setObjectName("miniNome")
        self.nome.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.barra = QSlider(Qt.Horizontal); self.barra.setObjectName("miniBarra")
        self.barra.setRange(0, 0); self.barra.setFixedHeight(10)
        self.barra.sliderMoved.connect(pai.mp.setPosition)
        meio.addStretch(1); meio.addWidget(self.nome); meio.addWidget(self.barra)
        meio.addStretch(1)
        c.addLayout(meio, 1)

        def bt(qual, dica, dono, tam=26):
            b = QPushButton(); b.setObjectName("miniBotao")
            b.setFixedSize(tam, tam); b.setToolTip(dica)
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(M.icone_controle(qual, M.PENA, 16)); b.setIconSize(QSize(16, 16))
            b.clicked.connect(dono)
            return b

        self.b_ant = bt("anterior", "Anterior", pai._anterior, 28)
        self.b_toc = bt("play", "Tocar / pausar", pai._play_pause, 32)
        self.b_toc.setObjectName("miniTocar")
        self.b_prox = bt("proxima", "Próxima", lambda: pai._pula(1), 28)
        for b in (self.b_ant, self.b_toc, self.b_prox):
            c.addWidget(b)

    # -- o liquido
    def _andar_onda(self):
        self._fase += 0.075
        if self._fase > 6.283185:
            self._fase -= 6.283185
        self.update()

    def fotografar_atras(self):
        """A foto tem que ser tirada com a janelinha ESCONDIDA: se ela estiver na
        tela, entra na propria foto e a refracao vira eco de si mesma."""
        tela = self.screen() or QApplication.primaryScreen()
        estava = self.isVisible()
        if estava:
            self.setWindowOpacity(0.0)
            QApplication.processEvents()
        g = self.geometry()
        try:
            self._atras = tela.grabWindow(0, g.x(), g.y(), g.width(), g.height())
        except Exception:
            self._atras = None
        if estava:
            self.setWindowOpacity(1.0)
        self.update()

    def _pintar_liquido(self, p, forma):
        """Desenha a foto do fundo em faixas deslocadas por uma senoide. A borda
        entorta mais que o meio, que e o que uma lente faz."""
        import math
        foto = self._atras
        if foto is None or foto.isNull():
            return
        alt = self.height()
        p.save()
        p.setClipPath(forma)
        p.setOpacity(0.78)
        faixa = 2
        meio = alt / 2.0
        for y in range(0, alt, faixa):
            # quanto mais longe do meio (vertical), mais a lente desloca
            distancia = abs(y - meio) / meio
            amplitude = 4.0 + 9.0 * (distancia ** 1.4)
            # duas frequencias somadas: uma so fica com cara de listra mecanica
            dx = (amplitude * math.sin(y / 11.0 + self._fase)
                  + amplitude * 0.45 * math.sin(y / 4.5 - self._fase * 1.7))
            p.drawPixmap(int(round(dx)), y, foto, 0, y, self.width(), faixa)
        p.restore()
        p.setOpacity(1.0)

    # -- o vidro
    def showEvent(self, ev):
        super().showEvent(ev)
        if self._vidro is None:
            self._vidro = vidro_do_windows(self) or "sem acrilico (so a moldura)"
        self._reelide()
        self._onda.start()

    def hideEvent(self, ev):
        super().hideEvent(ev)
        self._onda.stop()          # sem gastar quadro quando ninguem ve

    RAIO = 17

    def paintEvent(self, ev):
        """As camadas do liquid glass que Qt permite, de baixo para cima."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(0, 0, -1, -1)
        forma = QPainterPath()
        forma.addRoundedRect(float(r.x()), float(r.y()), float(r.width()),
                             float(r.height()), self.RAIO, self.RAIO)

        # 1. base bem clara: o pedido foi "menos vidro escuro, mais transparencia".
        #    Ela serve so para o texto continuar legivel sobre fundo claro.
        base = QLinearGradient(0, 0, 0, r.height())
        base.setColorAt(0.0, QColor(34, 28, 51, 106))
        base.setColorAt(1.0, QColor(15, 12, 22, 140))
        p.fillPath(forma, QBrush(base))

        # 1b. a camada LIQUIDA: o fundo refratado, ondulando
        self._pintar_liquido(p, forma)

        # 1c. veu fino DEPOIS da onda: sem ele, fundo claro e ruidoso engole o
        #     nome da musica. Mantem a onda visivel e devolve a legibilidade.
        p.fillPath(forma, QColor(16, 13, 24, 58))

        # (o brilho que seguia o mouse foi tirado por pedido dele)

        # 3. moldura de luz: fio claro no topo, sombra na base — da volume de lente
        p.save(); p.setClipPath(forma)
        topo = QLinearGradient(0, 0, 0, 18)
        topo.setColorAt(0.0, QColor(255, 255, 255, 46))
        topo.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(r.x(), r.y(), r.width(), 18, QBrush(topo))
        baixo = QLinearGradient(0, r.height() - 16, 0, r.height())
        baixo.setColorAt(0.0, QColor(0, 0, 0, 0))
        baixo.setColorAt(1.0, QColor(0, 0, 0, 66))
        p.fillRect(r.x(), r.height() - 16, r.width(), 16, QBrush(baixo))
        p.restore()

        # 4. aberracao cromatica: dois fios deslocados, ciano em cima e magenta
        #    embaixo. E o detalhe que faz parecer lente, e nao plastico.
        p.save()
        ciano = QPainterPath()
        ciano.addRoundedRect(float(r.x()) + 0.6, float(r.y()) + 1.4,
                             float(r.width()), float(r.height()), self.RAIO, self.RAIO)
        p.setPen(QPen(QColor(120, 235, 255, 46), 1.0)); p.drawPath(ciano)
        magenta = QPainterPath()
        magenta.addRoundedRect(float(r.x()) - 0.6, float(r.y()) - 1.4,
                               float(r.width()), float(r.height()), self.RAIO, self.RAIO)
        p.setPen(QPen(QColor(255, 130, 230, 40), 1.0)); p.drawPath(magenta)
        p.restore()

        # 5. borda do vidro por cima de tudo
        p.setPen(QPen(QColor(255, 255, 255, 56), 1.0))
        p.drawPath(forma)
        p.end()

    # -- arraste, porque nao ha barra de titulo
    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._arrasto = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, ev):
        if self._arrasto is not None and ev.buttons() & Qt.LeftButton:
            self.move(ev.globalPosition().toPoint() - self._arrasto)
            return
        return

    def mouseReleaseEvent(self, ev):
        if self._arrasto is not None:
            self._arrasto = None
            self.pai._guarda_lugar_do_mini()
            self.fotografar_atras()      # mudou de lugar: o fundo atras e outro

    def poe_nome(self, texto):
        """Guarda o nome inteiro e mostra a versao cortada com reticencia. O corte
        e refeito quando o rotulo ganha largura (no show e no resize): na primeira
        pintura ele ainda nao tem o tamanho final, e o nome saia inteiro."""
        self._texto = texto
        self.nome.setToolTip(texto)
        self._reelide()

    def _reelide(self):
        from PySide6.QtGui import QFontMetrics
        texto = getattr(self, "_texto", "")
        if not texto:
            return
        larg = self.nome.width()
        if larg < 40:                     # layout ainda nao rodou
            larg = self.width() - CAPA_MINI - 128
        self.nome.setText(QFontMetrics(self.nome.font()).elidedText(
            texto, Qt.ElideRight, max(40, larg)))

    # nao criar outro showEvent aqui: a classe ja tem um (o do vidro), e o
    # segundo sobrescrevia o primeiro — foi assim que o vidro ficou desligado
    # sem dar erro nenhum.
    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._reelide()

    # -- mesma API do mini de vidro, para o Player nao precisar saber qual esta em uso
    def poe_faixa(self, nome, pixmap_capa):
        self.capa.setPixmap(pixmap_capa)
        self.poe_nome(nome)

    def poe_progresso(self, pos, dur):
        if not self.barra.isSliderDown():
            self.barra.setRange(0, dur or 0)
            self.barra.setValue(pos)

    def poe_estado(self, tocando):
        self.b_toc.setIcon(M.icone_controle("pause" if tocando else "play", M.NOITE, 16))

    def mandar_tudo(self):
        pass

    def no_cantinho(self):
        """Canto de baixo à direita da área util (acima da barra de tarefas)."""
        tela = self.screen() or QApplication.primaryScreen()
        a = tela.availableGeometry()
        self.move(a.right() - self.width() - 18, a.bottom() - self.height() - 18)


class Player(QMainWindow):
    def __init__(self):
        super().__init__()
        self.faixas, self.listas = carregar()
        self.listas = list(self.listas)
        self.visiveis, self.ordem, self.pos, self.tocando = [], [], -1, -1
        self.fila = []          # "tocar a seguir": temporaria, morre ao fechar o app

        self.setWindowTitle("Roxin")
        _ico = recurso("roxin.ico")
        self.setWindowIcon(QIcon(_ico) if os.path.isfile(_ico) else M.icone())
        self.resize(1080, 680)
        self.setMinimumSize(720, 460)

        self._saida_escolhida = None          # None = seguir o padrao do Windows
        self.saida = QAudioOutput(); self.saida.setVolume(0.8)
        self._devs = QMediaDevices(self)
        self._devs.audioOutputsChanged.connect(self._saida_do_sistema_mudou)
        self.mp = QMediaPlayer(); self.mp.setAudioOutput(self.saida)
        self.mp.positionChanged.connect(self._andou)
        self.mp.durationChanged.connect(self._durou)
        self.mp.mediaStatusChanged.connect(self._status)
        self.mp.playbackStateChanged.connect(self._estado)

        self._monta()
        self.lista_pls.setCurrentRow(0)
        self._abre(0)

        self._pinta_fila()

        self._ajustes = ler_ajustes()
        self.mini = None          # nasce na primeira vez que for preciso
        self.b_mini.setChecked(bool(self._ajustes.get("mini", False)))

        # capa que chegar DEPOIS (o buscador roda em segundo plano, fora do app)
        # tem que aparecer sozinha: vigiar a pasta do cache e repintar.
        self._vigia = QFileSystemWatcher([CP.pasta_cache()], self)
        self._repinta = QTimer(self); self._repinta.setSingleShot(True)
        self._repinta.setInterval(2500)      # espera a poeira baixar: chegam em lote
        self._repinta.timeout.connect(lambda: self._capas_prontas(1))
        self._vigia.directoryChanged.connect(lambda _c: self._repinta.start())

        self._capeiro = None
        if CP.quantas_no_cache() < 10:
            self._capeiro = Capeiro(self)
            self._capeiro.pronto.connect(self._capas_prontas)
            self._capeiro.start()

    # -------------------------------------------------- montagem
    def _monta(self):
        raiz = QWidget(); self.setCentralWidget(raiz)
        vert = QVBoxLayout(raiz); vert.setContentsMargins(0,0,0,0); vert.setSpacing(0)

        corpo = QWidget(); linha = QHBoxLayout(corpo)
        linha.setContentsMargins(0,0,0,0); linha.setSpacing(0)
        vert.addWidget(corpo, 1)
        self.corpo = corpo

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
        rolagem_suave(self.lista_pls, 220)
        self.lista_pls.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista_pls.customContextMenuRequested.connect(self._menu_playlist)
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
        topo.addWidget(self.busca)

        # o lugar dele e aqui, do lado da busca: baixar musica e achar musica sao
        # a mesma familia de tarefa; no rodape (com os controles) nao era
        self.b_baixar = QPushButton("Baixar"); self.b_baixar.setObjectName("botaoBaixar")
        self.b_baixar.setCheckable(True); self.b_baixar.setCursor(Qt.PointingHandCursor)
        self.b_baixar.setFixedHeight(36); self.b_baixar.setMinimumWidth(74)
        self.b_baixar.setToolTip("Baixar música de um link")
        self.b_baixar.toggled.connect(self._mostra_pescaria)
        topo.addSpacing(10)
        topo.addWidget(self.b_baixar)
        topo.addStretch(1)
        cc.addLayout(topo)

        self._monta_pescaria(cc)

        self.titulo = QLabel(); self.titulo.setObjectName("titulo"); cc.addWidget(self.titulo)
        self.sub = QLabel(); self.sub.setObjectName("sub"); cc.addWidget(self.sub)

        self.tab = Tabela(0, 3)
        self.tab.setHorizontalHeaderLabels(["", "MÚSICA", "TEMPO"])
        self.tab.setIconSize(QSize(CAPA_LISTA, CAPA_LISTA))
        self.tab.verticalHeader().setDefaultSectionSize(CAPA_LISTA + 10)
        self.tab.verticalHeader().setVisible(False)
        self.tab.setShowGrid(False)
        self.tab.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tab.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tab.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tab.setFocusPolicy(Qt.StrongFocus)
        h = self.tab.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Fixed)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.Fixed)
        self.tab.setColumnWidth(0, CAPA_LISTA + 16)
        self.tab.setColumnWidth(2, 74)
        # a capinha entra so nas linhas que aparecem: com 1152 faixas, carregar
        # tudo de uma vez seguraria a tela
        self.tab.verticalScrollBar().valueChanged.connect(self._capas_a_vista)
        rolagem_suave(self.tab)
        self.tab.cellDoubleClicked.connect(lambda r, c: self._toca_linha(r))
        self.tab.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab.customContextMenuRequested.connect(self._menu_faixa)
        self.tab.setDragDropMode(QAbstractItemView.InternalMove)
        self.tab.setDragDropOverwriteMode(False)
        self.tab.setDefaultDropAction(Qt.MoveAction)
        self.tab.moveu.connect(self._reordena)
        cc.addWidget(self.tab, 1)
        linha.addWidget(centro, 1)

        # ---- direita: a fila. Fica escondida ate ele agendar a primeira musica
        self.painel_fila = QWidget(); self.painel_fila.setObjectName("fila")
        self.painel_fila.setFixedWidth(272)
        cf = QVBoxLayout(self.painel_fila)
        cf.setContentsMargins(0, 0, 0, 10); cf.setSpacing(0)

        cab = QHBoxLayout(); cab.setContentsMargins(20, 20, 12, 6)
        self.tit_fila = QLabel("A SEGUIR"); self.tit_fila.setObjectName("secao")
        self.tit_fila.setContentsMargins(0, 0, 0, 0)
        self.b_limpa = QPushButton("limpar"); self.b_limpa.setObjectName("limpaFila")
        self.b_limpa.setCursor(Qt.PointingHandCursor); self.b_limpa.setFixedHeight(24)
        self.b_limpa.clicked.connect(self._limpa_fila)
        cab.addWidget(self.tit_fila); cab.addStretch(1); cab.addWidget(self.b_limpa)
        cf.addLayout(cab)

        self.dica_fila = QLabel("Clique com o botão direito numa\nmúsica e escolha “Tocar a seguir”.\n\n"
                                "A fila é temporária: fechou o\nRoxin, ela zera.")
        self.dica_fila.setObjectName("dicaFila"); self.dica_fila.setWordWrap(True)
        cf.addWidget(self.dica_fila)

        self.lista_fila = QListWidget()
        self.lista_fila.setIconSize(QSize(CAPA_FILA, CAPA_FILA))
        self.lista_fila.setTextElideMode(Qt.ElideRight)
        self.lista_fila.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lista_fila.setWordWrap(False)
        self.lista_fila.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista_fila.customContextMenuRequested.connect(self._menu_fila)
        self.lista_fila.itemDoubleClicked.connect(self._toca_da_fila)
        rolagem_suave(self.lista_fila, 220)
        cf.addWidget(self.lista_fila, 1)
        linha.addWidget(self.painel_fila)
        self.painel_fila.setVisible(False)

        # ---- rodape
        rod = QFrame(); rod.setObjectName("rodape"); rod.setFixedHeight(84)
        cr = QHBoxLayout(rod); cr.setContentsMargins(22,0,22,0); cr.setSpacing(16)

        self.agora = Clicavel()
        self.agora.setCursor(Qt.PointingHandCursor)
        self.agora.setToolTip("Abrir a capa grande")
        self.agora.clicado.connect(self._abre_palco)
        ca2 = QHBoxLayout(self.agora)
        ca2.setContentsMargins(0, 0, 0, 0); ca2.setSpacing(16)

        self.capa_atual = QLabel()
        self.capa_atual.setFixedSize(CAPA_RODAPE, CAPA_RODAPE)
        self.capa_atual.setPixmap(capa("", CAPA_RODAPE))
        ca2.addWidget(self.capa_atual)

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
        ca2.addLayout(infos, 1)
        cr.addWidget(self.agora, 3)

        def bt(txt, dica, w=34, obj=None):
            b = QPushButton(txt); b.setToolTip(dica); b.setFixedSize(w, w)
            b.setCursor(Qt.PointingHandCursor)
            b.setIconSize(QSize(20, 20) if w < 40 else QSize(18, 18))
            if obj: b.setObjectName(obj)
            return b

        self.b_ant   = bt("", "Anterior");  self.b_ant.setIcon(M.icone_controle("anterior"))
        self.b_tocar = bt("", "Tocar", 42, "tocar"); self.b_tocar.setIcon(M.icone_controle("play", M.NOITE, 20))
        self.b_prox  = bt("", "Próxima"); self.b_prox.setIcon(M.icone_controle("proxima"))
        self.b_ale   = bt("", "Aleatório"); self.b_ale.setCheckable(True)
        self.b_ale.setIcon(M.icone_controle("aleatorio"))
        self.b_rep   = bt("", "Repetir"); self.b_rep.setCheckable(True)
        self.b_rep.setIcon(M.icone_controle("repetir"))
        self.b_ant.clicked.connect(self._anterior)
        self.b_tocar.clicked.connect(self._play_pause)
        self.b_prox.clicked.connect(lambda: self._pula(1))
        self.b_ale.toggled.connect(self._aleatorio)
        # com icone (e nao texto), o :checked do estilo nao muda a cor — trocar o icone
        self.b_ale.toggled.connect(lambda on: self.b_ale.setIcon(
            M.icone_controle("aleatorio", M.AMBAR if on else M.PENA)))
        self.b_rep.toggled.connect(lambda on: self.b_rep.setIcon(
            M.icone_controle("repetir", M.AMBAR if on else M.PENA)))
        for b in (self.b_ant, self.b_tocar, self.b_prox):
            b.clicked.connect(lambda _=False, w=b: pulsa(w))
            cr.addWidget(b)

        self.t_atual = QLabel("0:00"); self.t_atual.setObjectName("tempo")
        self.t_total = QLabel("0:00"); self.t_total.setObjectName("tempo")
        self.barra = QSlider(Qt.Horizontal); self.barra.setRange(0, 0)
        self.barra.sliderMoved.connect(self.mp.setPosition)
        self.barra.setMinimumWidth(180)
        cr.addWidget(self.t_atual); cr.addWidget(self.barra, 4); cr.addWidget(self.t_total)

        cr.addWidget(self.b_ale); cr.addWidget(self.b_rep)

        self.b_fila = QPushButton("Fila"); self.b_fila.setObjectName("botaoFila")
        self.b_fila.setCheckable(True); self.b_fila.setCursor(Qt.PointingHandCursor)
        self.b_fila.setFixedHeight(28); self.b_fila.setMinimumWidth(58)
        self.b_fila.setToolTip("Mostrar o que está agendado")
        self.b_fila.toggled.connect(self._mostra_fila)
        cr.addWidget(self.b_fila)

        self.b_mini = QPushButton("Mini"); self.b_mini.setObjectName("botaoFila")
        self.b_mini.setCheckable(True); self.b_mini.setCursor(Qt.PointingHandCursor)
        self.b_mini.setFixedHeight(28); self.b_mini.setMinimumWidth(58)
        self.b_mini.setToolTip("Player no cantinho quando eu sair do Roxin")
        self.b_mini.toggled.connect(self._liga_mini)
        cr.addWidget(self.b_mini)

        # escolher POR ONDE sai o som (TV, fone...). O Qt fixa o dispositivo ao abrir
        # e nao acompanha a troca feita no Windows — por isso a escolha mora aqui.
        self.b_saida = bt("", "Sair o som por…"); self.b_saida.setIcon(M.icone_controle("saida"))
        self.b_saida.clicked.connect(self._menu_saida)
        cr.addWidget(self.b_saida)

        self.vol = QSlider(Qt.Horizontal); self.vol.setRange(0, 100); self.vol.setValue(80)
        self.vol.setFixedWidth(90); self.vol.setToolTip("Volume")
        self.vol.valueChanged.connect(lambda v: self.saida.setVolume(v/100))
        cr.addWidget(self.vol)
        vert.addWidget(rod)
        self.rod = rod
        self._monta_palco(vert)

        QShortcut(QKeySequence(Qt.Key_Space), self, self._play_pause)
        QShortcut(QKeySequence("Ctrl+F"), self, self.busca.setFocus)
        QShortcut(QKeySequence(Qt.Key_MediaNext), self, lambda: self._pula(1))
        QShortcut(QKeySequence(Qt.Key_MediaPrevious), self, self._anterior)
        QShortcut(QKeySequence(Qt.Key_Return), self.tab,
                  lambda: self._toca_linha(self.tab.currentRow()))

    # -------------------------------------------------- baixar musica (Anzol)
    def _monta_pescaria(self, cc):
        """A abinha discreta: fechada, nao ocupa um pixel."""
        self.pescaria = QFrame(); self.pescaria.setObjectName("pescaria")
        cx = QVBoxLayout(self.pescaria)
        cx.setContentsMargins(16, 14, 16, 14); cx.setSpacing(10)

        linha1 = QHBoxLayout(); linha1.setSpacing(10)
        self.link = QLineEdit(); self.link.setObjectName("busca")
        self.link.setFixedHeight(34)
        self.link.setPlaceholderText("Cole aqui o link da música…")
        self.link.returnPressed.connect(self._pescar)
        linha1.addWidget(self.link, 1)

        self.qualidade = QComboBox(); self.qualidade.setObjectName("qualidade")
        self.qualidade.setFixedHeight(34)
        self.qualidade.addItem("MP3 192kbps", "mp3")
        self.qualidade.addItem("Original (mais rápido)", "m4a")
        linha1.addWidget(self.qualidade)

        self.b_pescar = QPushButton("Baixar"); self.b_pescar.setObjectName("pescarBotao")
        self.b_pescar.setCursor(Qt.PointingHandCursor); self.b_pescar.setFixedHeight(32)
        self.b_pescar.clicked.connect(self._pescar)
        linha1.addWidget(self.b_pescar)

        self.b_cancelar = QPushButton("Cancelar"); self.b_cancelar.setObjectName("limpaFila")
        self.b_cancelar.setCursor(Qt.PointingHandCursor); self.b_cancelar.setFixedHeight(32)
        self.b_cancelar.clicked.connect(self._cancelar_pesca)
        self.b_cancelar.setVisible(False)
        linha1.addWidget(self.b_cancelar)
        cx.addLayout(linha1)

        linha2 = QHBoxLayout(); linha2.setSpacing(12)
        self.na_playlist = QCheckBox("pôr também na playlist aberta")
        self.na_playlist.setObjectName("naPlaylist")
        linha2.addWidget(self.na_playlist)
        linha2.addStretch(1)
        self.credito = QLabel("motor: Anzol, de Alex Skot · MIT")
        self.credito.setObjectName("credito")
        linha2.addWidget(self.credito)
        cx.addLayout(linha2)

        self.recado_pesca = QLabel(""); self.recado_pesca.setObjectName("recadoPesca")
        self.recado_pesca.setWordWrap(True); self.recado_pesca.setVisible(False)
        cx.addWidget(self.recado_pesca)

        cc.addWidget(self.pescaria)
        self.pescaria.setVisible(False)
        self._job = None
        self._relogio_pesca = QTimer(self)
        self._relogio_pesca.setInterval(400)
        self._relogio_pesca.timeout.connect(self._olhar_pesca)

    def _mostra_pescaria(self, on):
        if on:
            self.pescaria.setMaximumHeight(0)
            self.pescaria.setVisible(True)
            self.pescaria.adjustSize()          # sem isto o sizeHint vem menor que o
            alvo = max(self.pescaria.sizeHint().height(),   # conteudo e o painel corta
                       self.pescaria.layout().sizeHint().height(), 132)
            # ao terminar, solta o limite: quem manda na altura passa a ser o conteudo
            suave(self.pescaria, "maximumHeight", 0, alvo, MOV_PADRAO,
                  fim=lambda: self.pescaria.setMaximumHeight(16777215))
            self.link.setFocus()
            nome, _itens, arq = self._lista_atual()
            self.na_playlist.setEnabled(bool(arq))
            self.na_playlist.setText("pôr também em “%s”" % nome if arq
                                     else "pôr numa playlist (abra uma primeiro)")
        else:
            suave(self.pescaria, "maximumHeight", self.pescaria.height(), 0,
                  MOV_PADRAO, QEasingCurve.InCubic,
                  fim=lambda: self.pescaria.setVisible(False))

    def _recado(self, texto, cor=None):
        self.recado_pesca.setText(texto)
        self.recado_pesca.setVisible(bool(texto))
        self.recado_pesca.setStyleSheet("color:%s;" % cor if cor else "")

    def _pescar(self):
        url = self.link.text().strip()
        if not url:
            return
        if self._job:
            self._recado("Espera esta terminar antes de mandar outra.", M.AMBAR)
            return
        n = anzol()
        if n is None:
            self._recado("Não consegui carregar o motor do Anzol: %s" % ANZOL_ERRO, "#e8834a")
            return
        modo = self.qualidade.currentData()
        if modo in getattr(n, "MODOS_COM_FFMPEG", ()) and not n.ffmpeg_disponivel():
            self._recado("MP3 precisa do ffmpeg, que não achei aqui. "
                         "Escolhe “Original (mais rápido)”.", "#e8834a")
            return
        import threading
        from pathlib import Path
        self._job = n.criar_job(url, modo)
        self._alvo_playlist = (self._lista_atual()[0]
                               if self.na_playlist.isChecked() and self.na_playlist.isEnabled()
                               else None)
        threading.Thread(target=n.rodar_download,
                         args=(self._job, url, modo, False, Path(MUSICA)),
                         daemon=True).start()
        self.b_pescar.setEnabled(False)
        self.b_cancelar.setVisible(True)
        self._recado("Procurando…")
        self._relogio_pesca.start()

    def _cancelar_pesca(self):
        n = anzol()
        if n and self._job:
            n.cancelar_job(self._job)
            self._recado("Cancelando…")

    def _olhar_pesca(self):
        n = anzol()
        if not (n and self._job):
            self._relogio_pesca.stop(); return
        j = n.ler_job(self._job)
        if not j:
            self._relogio_pesca.stop(); self._fim_da_pesca(); return
        titulo = j.get("titulo") or ""
        st = j.get("status")
        if st in ("iniciando", "baixando", "convertendo"):
            partes = [titulo or "baixando…"]
            if j.get("pct"):
                partes.append("%.0f%%" % j["pct"])
            if j.get("velocidade"):
                partes.append(str(j["velocidade"]))
            if j.get("eta"):
                partes.append("faltam %s" % j["eta"])
            self._recado("  ·  ".join(partes))
            return
        self._relogio_pesca.stop()
        if st == "concluido":
            nomes = [a["nome"] for a in (j.get("arquivos") or [])]
            entraram = [x for x in (self._guardar_pescado(nm) for nm in nomes) if x is not None]
            if entraram:
                self._recado("Pronto: %s — já está no app." % ", ".join(
                    self.faixas[i]["t"] for i in entraram), M.AMBAR)
                self.link.clear()
            else:
                self._recado("Baixou, mas não consegui pôr na lista. "
                             "Está em D:\Music.", "#e8834a")
        elif st == "cancelado":
            self._recado("Cancelado.")
        else:
            self._recado(j.get("erro") or "Não deu certo.", "#e8834a")
        self._fim_da_pesca()

    def _fim_da_pesca(self):
        self._job = None
        self.b_pescar.setEnabled(True)
        self.b_cancelar.setVisible(False)

    def _guardar_pescado(self, nome_arquivo):
        """Poe a musica baixada na biblioteca VIVA, sem reler o disco: recarregar
        trocaria todos os indices e bagunçaria a fila e o que esta tocando."""
        caminho = os.path.normpath(os.path.join(MUSICA, nome_arquivo))
        if not os.path.isfile(caminho):
            return None
        if os.path.splitext(caminho)[1].lower() not in EXT:
            return None            # baixou video: fica na pasta, mas nao entra no player
        for i, f in enumerate(self.faixas):
            if f["p"].lower() == caminho.lower():
                return i
        dur = 0
        try:
            from mutagen import File as MF
            m = MF(caminho, easy=True)
            if m and m.info:
                dur = int(round(m.info.length or 0))
        except Exception:
            pass
        nome = os.path.basename(caminho)
        self.faixas.append({"t": limpar(nome), "p": caminho, "d": dur,
                            "b": sem_acento(limpar(nome))})
        n = len(self.faixas) - 1
        for i, (rot, itens) in enumerate(self.listas):
            if rot == "Todas as músicas":
                self.listas[i] = (rot, list(itens) + [n])
        try:
            CP.gerar(quieto=True)          # capinha da faixa nova
        except Exception:
            pass
        if getattr(self, "_alvo_playlist", None):
            self._poe_na_lista(n, self._alvo_playlist)
        else:
            self._conta_fora()
            self._rotulos_playlists()
            self._filtra()
        QPixmapCache.clear()
        self._capas_a_vista()
        return n

    # -------------------------------------------------- palco (capa cheia)
    def _monta_palco(self, vert):
        self.palco = Palco()
        self.palco.setObjectName("palco")
        self.palco.clicado.connect(self._fecha_palco)
        cp = QVBoxLayout(self.palco)
        cp.setContentsMargins(40, 26, 40, 30); cp.setSpacing(0)

        cp.addStretch(1)
        self.capa_palco = QLabel(); self.capa_palco.setAlignment(Qt.AlignCenter)
        self.capa_palco.setScaledContents(False)
        cp.addWidget(self.capa_palco, 0, Qt.AlignHCenter)

        self.nome_palco = QLabel("—"); self.nome_palco.setObjectName("nomePalco")
        self.nome_palco.setAlignment(Qt.AlignCenter)
        self.sub_palco = QLabel(""); self.sub_palco.setObjectName("subPalco")
        self.sub_palco.setAlignment(Qt.AlignCenter)
        cp.addSpacing(22)
        cp.addWidget(self.nome_palco); cp.addWidget(self.sub_palco)

        # barra larga com os tempos
        fb = QHBoxLayout(); fb.setContentsMargins(0, 18, 0, 0); fb.setSpacing(12)
        self.t_atual_p = QLabel("0:00"); self.t_atual_p.setObjectName("tempo")
        self.t_total_p = QLabel("0:00"); self.t_total_p.setObjectName("tempo")
        self.barra_palco = QSlider(Qt.Horizontal); self.barra_palco.setRange(0, 0)
        self.barra_palco.sliderMoved.connect(self.mp.setPosition)
        self.barra_palco.setMaximumWidth(680)
        fb.addStretch(1); fb.addWidget(self.t_atual_p)
        fb.addWidget(self.barra_palco, 6); fb.addWidget(self.t_total_p); fb.addStretch(1)
        cp.addLayout(fb)

        # controles graudos
        fc = QHBoxLayout(); fc.setContentsMargins(0, 16, 0, 0); fc.setSpacing(18)

        def bt(qual, dica, dono, tam, obj="palcoBotao", icone=22):
            b = QPushButton(); b.setObjectName(obj)
            b.setFixedSize(tam, tam); b.setToolTip(dica)
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(M.icone_controle(qual, M.PENA, icone))
            b.setIconSize(QSize(icone, icone))
            b.clicked.connect(dono)
            b.clicked.connect(lambda _=False, w=b: pulsa(w, 190))
            return b

        self.p_ale = bt("aleatorio", "Aleatório", self.b_ale.toggle, 42, icone=20)
        self.p_ant = bt("anterior", "Anterior", self._anterior, 50, icone=24)
        self.p_toc = bt("play", "Tocar / pausar", self._play_pause, 68, "palcoTocar", 26)
        self.p_toc.setIcon(M.icone_controle("play", M.NOITE, 26))
        self.p_prox = bt("proxima", "Próxima", lambda: self._pula(1), 50, icone=24)
        self.p_rep = bt("repetir", "Repetir", self.b_rep.toggle, 42, icone=20)
        fc.addStretch(1)
        for b in (self.p_ale, self.p_ant, self.p_toc, self.p_prox, self.p_rep):
            fc.addWidget(b)
        fc.addStretch(1)
        cp.addLayout(fc)
        cp.addStretch(1)

        # os dois modos espelham o estado dos toggles do rodape
        self.b_ale.toggled.connect(lambda on: self.p_ale.setIcon(
            M.icone_controle("aleatorio", M.AMBAR if on else M.PENA, 20)))
        self.b_rep.toggled.connect(lambda on: self.p_rep.setIcon(
            M.icone_controle("repetir", M.AMBAR if on else M.PENA, 20)))

        vert.addWidget(self.palco, 1)
        self.palco.setVisible(False)
        self._no_palco = False
        QShortcut(QKeySequence(Qt.Key_Escape), self, self._fecha_palco)

    def _lado_da_capa(self):
        """A capa ocupa ~2/3 da janela, e o resto sobra para nome e controles."""
        return max(200, int(min(self.height() * 0.62, self.width() * 0.56)))

    def _pinta_palco(self):
        if self.tocando < 0:
            return
        f = self.faixas[self.tocando]
        lado = self._lado_da_capa()
        # a AREA e sempre quadrada (lado x lado) e a imagem se centraliza dentro:
        # assim nome, barra e controles ficam na mesma altura em qualquer capa
        self.capa_palco.setFixedSize(lado, lado)
        self.capa_palco.setPixmap(capa_livre(os.path.basename(f["p"]), lado))
        self.nome_palco.setText(f["t"])
        self.sub_palco.setText(self.listas[self.lista_idx][0])
        self.barra_palco.setRange(0, self.mp.duration())
        self.barra_palco.setValue(self.mp.position())
        self.t_total_p.setText(mmss(self.mp.duration() / 1000))
        self.t_atual_p.setText(mmss(self.mp.position() / 1000))

    def _abre_palco(self):
        if self._no_palco or self.tocando < 0:
            return
        self._no_palco = True
        self._pinta_palco()
        self.corpo.setVisible(False)
        self.rod.setVisible(False)
        self.palco.setVisible(True)
        ef = QGraphicsOpacityEffect(self.palco); self.palco.setGraphicsEffect(ef)
        suave(ef, "opacity", 0.0, 1.0, MOV_CONTEXTO, QEasingCurve.OutCubic,
              fim=lambda: self.palco.setGraphicsEffect(None))
        self._capa_crescendo(0.88, 1.0, MOV_CONTEXTO + 40)

    def _capa_crescendo(self, de, para, ms):
        """A imagem escala dentro da area (que e fixa): da o movimento de entrada
        sem empurrar nome e controles."""
        from PySide6.QtCore import QVariantAnimation
        if self.tocando < 0:
            return
        nome = os.path.basename(self.faixas[self.tocando]["p"])
        lado = self._lado_da_capa()
        a = QVariantAnimation(self)
        a.setDuration(ms)
        a.setStartValue(float(de))
        a.setEndValue(float(para))
        a.setEasingCurve(QEasingCurve.OutCubic)

        def passo(v):
            if not self._no_palco:
                return
            self.capa_palco.setPixmap(capa_livre(nome, max(40, int(lado * float(v)))))

        a.valueChanged.connect(passo)
        a.finished.connect(lambda: self._pinta_palco() if self._no_palco else None)
        self._anim_capa = a          # sem guardar, o coletor mata no meio
        a.start(QAbstractAnimation.DeleteWhenStopped)

    def _fecha_palco(self):
        if not self._no_palco:
            return
        self._no_palco = False
        ef = QGraphicsOpacityEffect(self.palco); self.palco.setGraphicsEffect(ef)

        def voltar():
            self.palco.setGraphicsEffect(None)
            self.palco.setVisible(False)
            self.corpo.setVisible(True)
            self.rod.setVisible(True)
            ef2 = QGraphicsOpacityEffect(self.corpo); self.corpo.setGraphicsEffect(ef2)
            suave(ef2, "opacity", 0.0, 1.0, MOV_PADRAO, QEasingCurve.OutCubic,
                  fim=lambda: self.corpo.setGraphicsEffect(None))

        suave(ef, "opacity", 1.0, 0.0, MOV_PADRAO, QEasingCurve.InCubic, fim=voltar)

    # -------------------------------------------------- lista
    def _abre(self, i):
        if i < 0: return
        trocou = getattr(self, "lista_idx", None) != i
        self.lista_idx = i
        self.busca.blockSignals(True); self.busca.clear(); self.busca.blockSignals(False)
        self._filtra()
        if trocou:
            ef = QGraphicsOpacityEffect(self.tab)
            self.tab.setGraphicsEffect(ef)
            suave(ef, "opacity", 0.25, 1.0, 200, QEasingCurve.OutCubic,
                  fim=lambda: self.tab.setGraphicsEffect(None))

    def _filtra(self):
        q = sem_acento(self.busca.text().strip())
        nome, itens = self.listas[self.lista_idx]
        # arrastar so faz sentido em playlist de verdade e sem filtro na tela
        pode_mover = bool(ARQUIVO_DA_LISTA.get(nome)) and not q
        self.tab.setDragEnabled(pode_mover)
        self.tab.setAcceptDrops(pode_mover)
        self.visiveis = [n for n in itens if not q or q in self.faixas[n]["b"]]
        seg = sum(self.faixas[n]["d"] for n in self.visiveis)
        h, m = seg // 3600, (seg % 3600) // 60
        self.titulo.setText(nome)
        self.sub.setText("%d músicas%s" % (len(self.visiveis),
                         ("  ·  %sh %dmin" % (h, m)) if h else ("  ·  %dmin" % m) if m else ""))
        self.tab.setRowCount(len(self.visiveis))
        for lin, n in enumerate(self.visiveis):
            f = self.faixas[n]
            self.tab.setItem(lin, 0, QTableWidgetItem())
            it = QTableWidgetItem(f["t"]); self.tab.setItem(lin, 1, it)
            t = QTableWidgetItem(mmss(f["d"]) if f["d"] else "—")
            t.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tab.setItem(lin, 2, t)
            if n == self.tocando:
                for c in (1, 2): self.tab.item(lin, c).setForeground(QColor("#e8834a"))
        self._capas_a_vista()

    # -------------------------------------------------- miniplayer
    def _garante_mini(self):
        """Cria a janelinha na primeira vez. Tenta o mini de VIDRO (a pagina com o
        CSS aprovado); sem QtWebEngine na maquina, cai no pintado a mao."""
        if self.mini is not None:
            return self.mini
        try:
            from mini_vidro import MiniVidro
            self.mini = MiniVidro(self)
            self._tipo_mini = "vidro (HTML + filtro da skill)"
        except Exception as e:
            self.mini = Mini(self)
            self._tipo_mini = "pintado a mao (sem QtWebEngine: %s)" % e
        lugar = self._ajustes.get("mini_lugar")
        self.mini.move(QPoint(*lugar)) if lugar else self.mini.no_cantinho()
        return self.mini

    def _liga_mini(self, on):
        self._ajustes["mini"] = bool(on)
        gravar_ajustes(self._ajustes)
        self._decide_mini()

    def _guarda_lugar_do_mini(self):
        if self.mini is None:
            return
        pt = self.mini.pos()
        self._ajustes["mini_lugar"] = [pt.x(), pt.y()]
        gravar_ajustes(self._ajustes)

    def _decide_mini(self, aqui=None):
        """Mostra o mini quando o Roger esta FORA do Roxin. `aqui` existe para o
        teste poder dizer "a janela principal esta ativa" sem depender do foco real."""
        aqui = self.isActiveWindow() if aqui is None else aqui
        fora = self.isMinimized() or not aqui
        precisa = self.b_mini.isChecked() and fora and self.tocando >= 0
        if precisa:
            self._garante_mini()
            self._pinta_mini()
            if not self.mini.isVisible():
                self.mini.fotografar_atras()      # com ela ainda escondida
                self.mini.setWindowOpacity(0.0)
                self.mini.show()
                suave(self.mini, "windowOpacity", 0.0, 1.0, MOV_PADRAO)
        elif self.mini is not None and self.mini.isVisible():
            suave(self.mini, "windowOpacity", self.mini.windowOpacity(), 0.0,
                  180, QEasingCurve.InCubic, fim=self.mini.hide)

    def _pinta_mini(self):
        if self.tocando < 0 or self.mini is None:
            return
        f = self.faixas[self.tocando]
        self.mini.poe_faixa(f["t"], capa(os.path.basename(f["p"]), CAPA_MINI * 2))
        self.mini.poe_progresso(self.mp.position(), self.mp.duration())
        self.mini.poe_estado(self.mp.playbackState() == QMediaPlayer.PlayingState)

    def changeEvent(self, ev):
        super().changeEvent(ev)
        if ev.type() in (QEvent.ActivationChange, QEvent.WindowStateChange):
            self._decide_mini()

    def closeEvent(self, ev):
        if self.mini is not None:
            self.mini.close()          # senao a janelinha sobrevive ao app
        super().closeEvent(ev)

    def resizeEvent(self, ev):
        """Janela maior mostra mais linhas — elas tambem precisam de capinha."""
        super().resizeEvent(ev)
        self._capas_a_vista()
        if getattr(self, "_no_palco", False):
            self._pinta_palco()

    def _capas_prontas(self, quantas):
        """As miniaturas acabaram de nascer: repintar o que esta na tela."""
        if not quantas:
            return
        QPixmapCache.clear()
        for lin in range(self.tab.rowCount()):
            it = self.tab.item(lin, 0)
            if it is not None:
                it.setIcon(QIcon())
        self._capas_a_vista()
        if self.tocando >= 0:
            self.capa_atual.setPixmap(
                capa(os.path.basename(self.faixas[self.tocando]["p"]), CAPA_RODAPE))

    def _capas_a_vista(self):
        """Poe a capinha nas linhas que estao na tela (e um pouco antes/depois)."""
        if not self.visiveis: return
        vp = self.tab.viewport()
        pri = self.tab.rowAt(0)
        ult = self.tab.rowAt(vp.height() - 1)
        pri = 0 if pri < 0 else max(0, pri - 4)
        ult = len(self.visiveis) - 1 if ult < 0 else min(len(self.visiveis) - 1, ult + 4)
        for lin in range(pri, ult + 1):
            it = self.tab.item(lin, 0)
            if it is None or not it.icon().isNull():
                continue
            nome = os.path.basename(self.faixas[self.visiveis[lin]]["p"])
            it.setIcon(QIcon(capa(nome, CAPA_LISTA)))

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
        self.capa_atual.setPixmap(capa(os.path.basename(f["p"]), CAPA_RODAPE))
        ef = QGraphicsOpacityEffect(self.capa_atual)
        self.capa_atual.setGraphicsEffect(ef)
        suave(ef, "opacity", 0.25, 1.0, MOV_PADRAO, QEasingCurve.OutCubic,
              fim=lambda: self.capa_atual.setGraphicsEffect(None))
        self.setWindowTitle("%s — Roxin" % f["t"])
        if self.mini is not None:
            self._pinta_mini()
        if getattr(self, "_no_palco", False):
            self._pinta_palco()
        self._filtra()

    def _play_pause(self):
        if self.mp.source().isEmpty():
            if self.visiveis: self._toca_linha(0)
            return
        if self.mp.playbackState() == QMediaPlayer.PlayingState: self.mp.pause()
        else: self.mp.play()

    def _pula(self, d):
        if d > 0 and self.fila:
            n = self.fila.pop(0)
            self._pinta_fila()
            self._toca_este(n)
            return
        if not self.ordem: return
        self.pos = (self.pos + d) % len(self.ordem)
        self._toca()

    def _toca_este(self, n):
        """Toca a faixa n sem perder a navegacao: ela entra na ordem logo
        depois da atual, entao "anterior" e "proxima" seguem fazendo sentido."""
        if n in self.ordem:
            self.pos = self.ordem.index(n)
        else:
            self.ordem.insert(self.pos + 1, n)
            self.pos += 1
        self._toca()

    def _mostra_fila(self, on):
        """Painel desliza em vez de pular na tela."""
        largura = 272
        if on:
            self.painel_fila.setMaximumWidth(0)
            self.painel_fila.setVisible(True)
            suave(self.painel_fila, "maximumWidth", 0, largura, MOV_PADRAO)
        else:
            suave(self.painel_fila, "maximumWidth", self.painel_fila.width(), 0,
                  MOV_PADRAO, QEasingCurve.InCubic,
                  fim=lambda: self.painel_fila.setVisible(False))

    # -------------------------------------------------- fila ("tocar a seguir")
    def _enfileira(self, n, topo):
        self.fila.insert(0, n) if topo else self.fila.append(n)
        self._pinta_fila()
        if not self.painel_fila.isVisible():
            self.b_fila.setChecked(True)          # a primeira vez abre o painel sozinho

    def _pinta_fila(self):
        self.lista_fila.clear()
        for n in self.fila:
            f = self.faixas[n]
            it = QListWidgetItem(QIcon(capa(os.path.basename(f["p"]), CAPA_FILA)), f["t"])
            it.setToolTip("%s  ·  %s" % (f["t"], mmss(f["d"])))
            self.lista_fila.addItem(it)
        self.tit_fila.setText("A SEGUIR" if not self.fila else "A SEGUIR    %d" % len(self.fila))
        self.b_fila.setText("Fila" if not self.fila else "Fila  %d" % len(self.fila))
        self.b_limpa.setVisible(bool(self.fila))
        self.dica_fila.setVisible(not self.fila)
        self.lista_fila.setVisible(bool(self.fila))

    def _limpa_fila(self):
        self.fila = []
        self._pinta_fila()

    def _toca_da_fila(self, item):
        i = self.lista_fila.row(item)
        if 0 <= i < len(self.fila):
            n = self.fila.pop(i)
            self._pinta_fila()
            self._toca_este(n)

    # -------------------------------------------------- curadoria das playlists
    def _lista_atual(self):
        """(nome, itens, arquivo). arquivo None = lista virtual, nao se edita."""
        nome, itens = self.listas[self.lista_idx]
        return nome, itens, ARQUIVO_DA_LISTA.get(nome)

    def _entradas(self, itens):
        return [(self.faixas[n]["t"], self.faixas[n]["d"], self.faixas[n]["p"])
                for n in itens]

    def _grava_lista(self, nome, itens):
        arq = ARQUIVO_DA_LISTA.get(nome)
        if not arq:
            return False
        escrever_m3u(arq, self._entradas(itens))
        for i, (n, _it) in enumerate(self.listas):
            if n == nome:
                self.listas[i] = (nome, itens)
                break
        self._conta_fora()
        self._rotulos_playlists()
        return True

    def _conta_fora(self):
        """Mantem "Fora das playlists" honesta sem reler o disco."""
        em_lista = set()
        for nome, itens in self.listas:
            if nome not in VIRTUAIS:
                em_lista.update(itens)
        for i, (nome, _itens) in enumerate(self.listas):
            if nome == "Fora das playlists":
                self.listas[i] = (nome, [n for n in range(len(self.faixas))
                                         if n not in em_lista])
                return

    def _rotulos_playlists(self):
        sel = self.lista_pls.currentRow()
        self.lista_pls.blockSignals(True)
        self.lista_pls.clear()
        for nome, itens in self.listas:
            QListWidgetItem("%s      %d" % (nome, len(itens)), self.lista_pls)
        self.lista_pls.setCurrentRow(min(sel, self.lista_pls.count() - 1))
        self.lista_pls.blockSignals(False)

    def _tira_da_lista(self, n):
        nome, itens, arq = self._lista_atual()
        if not arq:
            return
        from PySide6.QtWidgets import QMessageBox
        r = QMessageBox.question(self, "Tirar da playlist",
                                 "Tirar “%s” de %s?\n\nO arquivo da música não é apagado."
                                 % (self.faixas[n]["t"], nome))
        if r != QMessageBox.Yes:
            return
        self._grava_lista(nome, [x for x in itens if x != n])
        self._filtra()

    def _poe_na_lista(self, n, nome_destino):
        for nome, itens in self.listas:
            if nome == nome_destino:
                if n in itens:
                    return
                self._grava_lista(nome_destino, list(itens) + [n])
                self._filtra()
                return

    def _nova_lista(self, n=None):
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        nome, ok = QInputDialog.getText(self, "Nova playlist", "Nome da playlist:")
        nome = (nome or "").strip()
        if not ok or not nome:
            return
        if nome in ARQUIVO_DA_LISTA or nome in VIRTUAIS:
            QMessageBox.warning(self, "Nova playlist", "Já existe uma playlist com esse nome.")
            return
        if any(c in nome for c in '\\/:*?"<>|'):
            QMessageBox.warning(self, "Nova playlist",
                                "O nome não pode ter estes caracteres:  \\ / : * ? \" < > |")
            return
        arq = os.path.join(PLAYLISTS, nome + ".m3u")
        itens = [n] if n is not None else []
        escrever_m3u(arq, self._entradas(itens))
        ARQUIVO_DA_LISTA[nome] = arq
        # entra na ordem alfabetica, como o disco devolveria
        pos = len(self.listas)
        for i, (nm, _it) in enumerate(self.listas):
            if nm not in VIRTUAIS and nm.lower() > nome.lower():
                pos = i; break
        self.listas.insert(pos, (nome, itens))
        self._conta_fora()
        self._rotulos_playlists()

    def _reordena(self, de, para):
        """Arrastou uma linha: gravar a nova ordem no .m3u."""
        nome, itens, arq = self._lista_atual()
        if not arq or self.busca.text().strip():
            return          # com filtro ligado a ordem na tela nao e a ordem real
        itens = list(itens)
        if not (0 <= de < len(itens) and 0 <= para < len(itens)):
            return
        itens.insert(para, itens.pop(de))
        self._grava_lista(nome, itens)
        self._filtra()
        self.tab.selectRow(para)

    def _menu_playlist(self, ponto):
        from PySide6.QtWidgets import QMenu, QInputDialog, QMessageBox
        i = self.lista_pls.indexAt(ponto).row()
        if i < 0:
            return
        nome = self.listas[i][0]
        arq = ARQUIVO_DA_LISTA.get(nome)
        m = QMenu(self)
        a_nova = m.addAction("Criar playlist vazia…")
        a_ren = a_apaga = None
        if arq:
            m.addSeparator()
            a_ren = m.addAction("Renomear “%s”…" % nome)
            a_apaga = m.addAction("Apagar a playlist “%s”" % nome)
        esc = m.exec(self.lista_pls.viewport().mapToGlobal(ponto))
        if esc is None:
            return
        if esc == a_nova:
            self._nova_lista(None)
        elif esc == a_ren:
            novo, ok = QInputDialog.getText(self, "Renomear playlist", "Novo nome:", text=nome)
            novo = (novo or "").strip()
            if not ok or not novo or novo == nome:
                return
            if novo in ARQUIVO_DA_LISTA or novo in VIRTUAIS:
                QMessageBox.warning(self, "Renomear", "Já existe uma playlist com esse nome.")
                return
            destino = os.path.join(PLAYLISTS, novo + ".m3u")
            guardar_copia(arq)
            os.rename(arq, destino)
            ARQUIVO_DA_LISTA.pop(nome, None)
            ARQUIVO_DA_LISTA[novo] = destino
            self.listas[i] = (novo, self.listas[i][1])
            self._rotulos_playlists()
            self._filtra()
        elif esc == a_apaga:
            r = QMessageBox.question(self, "Apagar playlist",
                                     "Apagar a playlist “%s”?\n\nAs músicas continuam "
                                     "em D:\\Music — só a lista é apagada." % nome)
            if r != QMessageBox.Yes:
                return
            guardar_copia(arq)
            try:
                os.remove(arq)
            except Exception as e:
                QMessageBox.warning(self, "Apagar playlist", "Não consegui apagar: %s" % e)
                return
            ARQUIVO_DA_LISTA.pop(nome, None)
            self.listas.pop(i)
            self._conta_fora()
            self._rotulos_playlists()
            self.lista_pls.setCurrentRow(0)
            self._abre(0)

    def _menu_faixa(self, ponto):
        """Clique direito numa musica: fila e curadoria da playlist."""
        from PySide6.QtWidgets import QMenu
        lin = self.tab.rowAt(ponto.y())
        if lin < 0 or lin >= len(self.visiveis): return
        n = self.visiveis[lin]
        nome_atual, _itens, arq_atual = self._lista_atual()
        m = QMenu(self)
        a_seguir = m.addAction("Tocar a seguir")
        a_fim    = m.addAction("Pôr no fim da fila")
        m.addSeparator()
        a_agora  = m.addAction("Tocar agora")
        m.addSeparator()

        sub = m.addMenu("Adicionar à playlist")
        acoes_add = {}
        for nome, itens in self.listas:
            if nome in VIRTUAIS or nome == nome_atual:
                continue
            a = sub.addAction(nome)
            a.setEnabled(n not in itens)
            acoes_add[a] = nome
        sub.addSeparator()
        a_nova = sub.addAction("Nova playlist com esta música…")

        a_tira = None
        if arq_atual:
            a_tira = m.addAction("Tirar de “%s”" % nome_atual)

        esc = m.exec(self.tab.viewport().mapToGlobal(ponto))
        if esc is None:
            return
        if   esc == a_seguir: self._enfileira(n, True)
        elif esc == a_fim:    self._enfileira(n, False)
        elif esc == a_agora:  self._toca_linha(lin)
        elif esc == a_nova:   self._nova_lista(n)
        elif esc == a_tira:   self._tira_da_lista(n)
        elif esc in acoes_add: self._poe_na_lista(n, acoes_add[esc])

    def _menu_fila(self, ponto):
        from PySide6.QtWidgets import QMenu
        i = self.lista_fila.indexAt(ponto).row()
        if i < 0 or i >= len(self.fila): return
        m = QMenu(self)
        a_agora = m.addAction("Tocar agora")
        a_topo  = m.addAction("Subir para o topo da fila")
        a_tira  = m.addAction("Tirar da fila")
        esc = m.exec(self.lista_fila.viewport().mapToGlobal(ponto))
        if esc == a_agora:
            self._toca_da_fila(self.lista_fila.item(i))
        elif esc == a_topo:
            self.fila.insert(0, self.fila.pop(i)); self._pinta_fila()
        elif esc == a_tira:
            self.fila.pop(i); self._pinta_fila()

    def _anterior(self):
        if self.mp.position() > 3000: self.mp.setPosition(0)
        else: self._pula(-1)

    def _aleatorio(self, on):
        if on and self.ordem: self._embaralha()

    # -------------------------------------------------- saida de audio
    def _menu_saida(self):
        """Lista as saidas do sistema e troca sem parar a musica."""
        from PySide6.QtWidgets import QMenu
        atual = self.saida.device()
        m = QMenu(self)
        acao_padrao = m.addAction("Padrão do sistema")
        acao_padrao.setCheckable(True)
        acao_padrao.setChecked(self._saida_escolhida is None)
        m.addSeparator()
        acoes = {}
        for d in QMediaDevices.audioOutputs():
            a = m.addAction(d.description())
            a.setCheckable(True)
            a.setChecked(self._saida_escolhida is not None and d.id() == atual.id())
            acoes[a] = d
        esc = m.exec(self.b_saida.mapToGlobal(self.b_saida.rect().topLeft()))
        if esc is None:
            return
        if esc is acao_padrao:
            self._saida_escolhida = None
            self._aplicar_saida(QMediaDevices.defaultAudioOutput())
        elif esc in acoes:
            self._saida_escolhida = acoes[esc]
            self._aplicar_saida(acoes[esc])

    def _aplicar_saida(self, disp):
        """Troca o dispositivo preservando o ponto da musica."""
        tocando = self.mp.playbackState() == QMediaPlayer.PlayingState
        onde = self.mp.position()
        self.saida.setDevice(disp)
        if onde:
            self.mp.setPosition(onde)
        if tocando:
            self.mp.play()
        self.b_saida.setToolTip("Som saindo por: %s" % disp.description())

    def _saida_do_sistema_mudou(self):
        """Se o Roger nao fixou uma saida, seguir o padrao do Windows quando ele mudar."""
        if self._saida_escolhida is None:
            self._aplicar_saida(QMediaDevices.defaultAudioOutput())

    # -------------------------------------------------- sinais
    def _andou(self, p):
        if not self.barra.isSliderDown(): self.barra.setValue(p)
        self.t_atual.setText(mmss(p/1000))
        if self.mini is not None and self.mini.isVisible():
            self.mini.poe_progresso(p, self.mp.duration())
        if getattr(self, "_no_palco", False) and not self.barra_palco.isSliderDown():
            self.barra_palco.setValue(p)
            self.t_atual_p.setText(mmss(p / 1000))

    def _durou(self, d):
        self.barra.setRange(0, d); self.t_total.setText(mmss(d/1000))
        if self.mini is not None: self.mini.poe_progresso(self.mp.position(), d)
        if hasattr(self, "barra_palco"):
            self.barra_palco.setRange(0, d); self.t_total_p.setText(mmss(d / 1000))

    def _estado(self, e):
        qual = "pause" if e == QMediaPlayer.PlayingState else "play"
        self.b_tocar.setIcon(M.icone_controle(qual, M.NOITE, 20))
        if self.mini is not None:
            self.mini.poe_estado(qual == "pause")
        if hasattr(self, "p_toc"):
            self.p_toc.setIcon(M.icone_controle(qual, M.NOITE, 26))

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
    # o QtWebEngine (usado pelo miniplayer de vidro) exige contexto de GL
    # compartilhado, e isso tem que ser dito ANTES de a QApplication nascer
    try:
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    except Exception:
        pass
    app = QApplication(sys.argv)
    f = QFont("Segoe UI", 10)
    f.setStyleStrategy(QFont.PreferAntialias)       # sem isto o japones serrilha
    f.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(f)
    app.setStyleSheet(ESTILO)
    j = Player(); j.show()
    M.pintar_barra_titulo(j)      # barra de titulo na cor do app, nao no verde do Windows
    sys.exit(app.exec())
