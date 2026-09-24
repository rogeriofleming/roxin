# -*- coding: utf-8 -*-
"""Conferencias da rolagem por roda do mouse (rolagem_suave).

Por que este teste existe: em 24/09/2026 a lista de musicas parou de rolar. A
causa era `a.start(DeleteWhenStopped)` numa animacao cuja referencia ficava
guardada em `area._anim_rolagem`: terminada a animacao, o C++ era destruido e a
roda seguinte chamava `.stop()` em memoria liberada -> access violation. Rodando
por `pythonw` (o Roxin.exe), isso nao aparece em lugar nenhum: o sintoma e a
lista simplesmente nao rolar.

Cada caso roda em SUBPROCESSO proprio, de proposito: o defeito derrubava o
interpretador, e um teste que morre junto nao reporta nada.

    python testes/teste_rolagem.py              # os casos rapidos
    python testes/teste_rolagem.py --completo   # + o app real, com o acervo
"""
import os, subprocess, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PREAMBULO = r'''
import faulthandler, io, re, sys
faulthandler.enable()
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QAbstractAnimation, QPointF
from PySide6.QtGui import QWheelEvent
fonte = io.open(r"{raiz}\Musica.pyw", encoding="utf-8").read()
ns = dict(QAbstractItemView=QAbstractItemView, QPropertyAnimation=QPropertyAnimation,
          QEasingCurve=QEasingCurve, QAbstractAnimation=QAbstractAnimation)
exec(compile(re.search(r"^def rolagem_suave\(.*?(?=^class )", fonte, re.S|re.M).group(0),
             "rolagem_suave", "exec"), ns)
app = QApplication(sys.argv)
t = QTableWidget(400, 2)
for i in range(400): t.setItem(i, 0, QTableWidgetItem("faixa %d" % i))
ns["rolagem_suave"](t); t.resize(320, 420); t.show(); app.processEvents()
b = t.verticalScrollBar()
def roda(cliques=-1):
    ev = QWheelEvent(QPointF(10,10), QPointF(10,10), QPointF(0,0).toPoint(),
                     QPointF(0,120*cliques).toPoint(), Qt.NoButton, Qt.NoModifier,
                     Qt.NoScrollPhase, False)
    QApplication.sendEvent(t.viewport(), ev)
def assentar(ms=800):
    for _ in range(ms//10):
        app.processEvents(); app.thread().msleep(10)
'''

CASOS = [
    ("roda uma vez e a lista anda", r'''
v0 = b.value(); roda(); assentar(400)
assert b.value() != v0, "a primeira roda nao rolou"
print("ok")
'''),
    ("roda DE NOVO depois da animacao morrer (o defeito de 24/09)", r'''
roda(); assentar(800)                 # tempo de sobra para o deleteLater
v1 = b.value()
roda(); assentar(400)                 # esta e a que quebrava
assert b.value() != v1, "a segunda roda foi engolida: a animacao guardada morreu"
print("ok")
'''),
    ("a animacao guardada continua viva depois de terminar", r'''
roda(); assentar(800)
try:
    estado = t._anim_rolagem.state()
except RuntimeError as e:
    raise AssertionError("objeto C++ ja destruido: %s" % e)
print("ok")
'''),
    ("dez rodas seguidas, com pausa entre elas", r'''
andou = 0
for _ in range(10):
    v = b.value(); roda(); assentar(400)
    if b.value() != v: andou += 1
    if b.value() >= b.maximum(): b.setValue(0); assentar(50)
assert andou == 10, "so %d de 10 rodas andaram" % andou
print("ok")
'''),
    ("roda para CIMA volta a lista", r'''
b.setValue(b.maximum()); assentar(50)
v0 = b.value(); roda(+1); assentar(400)
assert b.value() < v0, "a roda para cima nao subiu"
print("ok")
'''),
    ("rodas encadeadas somam, em vez de perder clique", r'''
b.setValue(0); assentar(50)
roda(); app.processEvents(); roda(); app.processEvents(); roda()
assentar(600)
um = 3 * max(18, b.singleStep() or 18)
assert b.value() > um * 2, "tres cliques rapidos renderam menos que dois (%d)" % b.value()
print("ok")
'''),
]

APP_REAL = r'''
import faulthandler, importlib.util, sys, os
faulthandler.enable()
os.chdir(r"{raiz}"); sys.path.insert(0, r"{raiz}")
spec = importlib.util.spec_from_file_location("roxin_app", r"{raiz}\Musica.pyw")
mod = importlib.util.module_from_spec(spec); sys.modules["roxin_app"] = mod
from PySide6.QtCore import QCoreApplication, Qt, QPointF, QAbstractAnimation
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
spec.loader.exec_module(mod)
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QWheelEvent
app = QApplication(sys.argv)
j = mod.Player(); j.show(); app.processEvents()
tab, b = j.tab, j.tab.verticalScrollBar()
def assentar(ms):
    for _ in range(ms//10): app.processEvents(); app.thread().msleep(10)
def roda():
    ev = QWheelEvent(QPointF(10,10), QPointF(10,10), QPointF(0,0).toPoint(),
                     QPointF(0,-120).toPoint(), Qt.NoButton, Qt.NoModifier,
                     Qt.NoScrollPhase, False)
    QApplication.sendEvent(tab.viewport(), ev)
falhou = []
for linha in range(min(7, j.lista_pls.count())):
    j.lista_pls.setCurrentRow(linha); assentar(500)
    b.setValue(0); assentar(50)
    if b.maximum() == 0:            # playlist que cabe na tela nao tem o que rolar
        continue
    v0 = b.value(); roda(); assentar(500)
    if b.value() == v0:
        falhou.append(j.lista_pls.item(linha).text().strip())
assert not falhou, "nao rolou em: %s" % falhou
print("ok")
'''


def rodar(nome, corpo, raiz):
    script = PREAMBULO.format(raiz=raiz) + corpo
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-u", "-c", script], capture_output=True,
                       text=True, env=env, timeout=300)
    if r.returncode == 0 and r.stdout.strip().endswith("ok"):
        print(f"  [OK   ] {nome}")
        return True
    motivo = (r.stderr or r.stdout).strip().splitlines()
    detalhe = motivo[-1] if motivo else f"exit {r.returncode}"
    if r.returncode < 0 or r.returncode == 139 or "access violation" in (r.stderr or ""):
        detalhe = f"O PROCESSO MORREU (exit {r.returncode}) — {detalhe}"
    print(f"  [FALHA] {nome}\n          {detalhe}")
    return False


if __name__ == "__main__":
    raiz = RAIZ
    print("Rolagem por roda do mouse — cada caso em processo proprio\n")
    resultados = [rodar(n, c, raiz) for n, c in CASOS]
    if "--completo" in sys.argv:
        print("\nApp real (carrega o acervo, demora):")
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, "-u", "-c", APP_REAL.format(raiz=raiz)],
                           capture_output=True, text=True, env=env, timeout=600)
        ok = r.returncode == 0 and r.stdout.strip().endswith("ok")
        print(f"  [{'OK   ' if ok else 'FALHA'}] entrar em cada playlist e rolar")
        if not ok:
            print("         ", (r.stderr or r.stdout).strip().splitlines()[-1:])
        resultados.append(ok)
    print(f"\n{sum(resultados)}/{len(resultados)} passaram")
    sys.exit(0 if all(resultados) else 1)
