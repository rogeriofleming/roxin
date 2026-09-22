# -*- coding: utf-8 -*-
"""Renderiza a tela do Roxin sem abrir janela e sem tocar som (teste MUDO)."""
import os, sys
# sem plataforma "offscreen": ela nao acha as fontes do Windows e o texto
# sai como quadradinhos. WA_DontShowOnScreen renderiza de verdade, sem aparecer.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util, importlib.machinery
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

spec = importlib.util.spec_from_loader("rx", importlib.machinery.SourceFileLoader("rx", os.path.join(os.path.dirname(os.path.abspath(__file__)), "Musica.pyw")))
rx = importlib.util.module_from_spec(spec); spec.loader.exec_module(rx)

app = QApplication(sys.argv)
app.setFont(QFont("Segoe UI", 10))
app.setStyleSheet(rx.ESTILO)
j = rx.Player()
j.saida.setVolume(0.0)          # MUDO: teste meu nao toca som na maquina dele
j.resize(1080, 680)
from PySide6.QtCore import Qt as _Qt
j.setAttribute(_Qt.WA_DontShowOnScreen, True)
j.show()
app.processEvents()

destino = sys.argv[1] if len(sys.argv) > 1 else "_tela_capas.png"
alvo = sys.argv[2] if len(sys.argv) > 2 else None
if alvo:
    for i, (nome, _) in enumerate(j.listas):
        if nome.lower().startswith(alvo.lower()):
            j.lista_pls.setCurrentRow(i); break
if "--tocando" in sys.argv:
    # MUDO: volume ja esta em 0.0 antes de qualquer play
    lin = int(sys.argv[sys.argv.index("--tocando") + 1])
    j.saida.setVolume(0.0)
    j._toca_linha(lin)
    j.mp.pause()
    app.processEvents()
    print("tocando:", j.nome_atual.text(), "| volume:", j.saida.volume())
app.processEvents()
j.grab().save(destino)
print("render:", destino, "| playlist:", j.titulo.text(), "|", j.sub.text())
print("volume do teste:", j.saida.volume())
