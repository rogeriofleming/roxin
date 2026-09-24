# -*- coding: utf-8 -*-
"""Conferencias do volume no palco (modo capa cheia), pedido em 24/09/2026.

O que estas conferencias travam: o VALOR do volume mora num lugar so -- o slider
do rodape, que e quem fala com a saida de audio. O do palco e espelho. Se alguem
um dia fizer o palco falar direto com a saida, o espelho desencontra e estes
casos caem.

    python testes/teste_volume_palco.py
"""
import importlib.util, os, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def montar():
    os.chdir(RAIZ); sys.path.insert(0, RAIZ)
    spec = importlib.util.spec_from_file_location("roxin_app", os.path.join(RAIZ, "Musica.pyw"))
    mod = importlib.util.module_from_spec(spec); sys.modules["roxin_app"] = mod
    from PySide6.QtCore import QCoreApplication, Qt
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    spec.loader.exec_module(mod)
    # teste NAO mexe nas preferencias de verdade do Roger: o ajustes.json vira um
    # de mentira em tmp/ (montar o Player ja grava nele, pelo botao Mini)
    mod.arquivo_ajustes = lambda: os.path.join(RAIZ, "tmp", "ajustes_de_teste.json")
    os.makedirs(os.path.join(RAIZ, "tmp"), exist_ok=True)
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyleSheet(mod.ESTILO)
    j = mod.Player(); j.resize(1359, 767); j.show()
    return app, j


def main():
    app, j = montar()

    def bombear(ms=300):
        for _ in range(ms // 10): app.processEvents(); app.thread().msleep(10)

    falhas = []
    def conf(nome, cond, extra=""):
        print(f"  [{'OK   ' if cond else 'FALHA'}] {nome} {extra}")
        if not cond: falhas.append(nome)

    bombear(200)
    j.tocando = 0
    j._abre_palco(); bombear(700)

    conf("o palco abre", j._no_palco)
    conf("a barra de volume aparece no palco", j.vol_palco.isVisible())
    conf("nasce espelhando o rodape", j.vol_palco.value() == j.vol.value(),
         f"(palco={j.vol_palco.value()} rodape={j.vol.value()})")

    j.vol_palco.setValue(35); bombear(60)
    conf("mexer no palco muda o rodape", j.vol.value() == 35, f"(rodape={j.vol.value()})")
    conf("  e chega na saida de audio", abs(j.saida.volume() - 0.35) < 0.01,
         f"(saida={j.saida.volume():.2f})")

    j.vol.setValue(80); bombear(60)
    conf("mexer no rodape muda o palco", j.vol_palco.value() == 80,
         f"(palco={j.vol_palco.value()})")

    j.p_som.click(); bombear(60)
    conf("o alto-falante silencia", j.vol.value() == 0, f"(volume={j.vol.value()})")
    j.p_som.click(); bombear(60)
    conf("e devolve o volume de antes", j.vol.value() == 80, f"(volume={j.vol.value()})")

    j.vol.setValue(0); bombear(60)
    j.p_som.click(); bombear(60)
    conf("mudo ja no zero volta num volume audivel", j.vol.value() > 0,
         f"(volume={j.vol.value()})")

    base = j.vol_palco.mapTo(j, j.vol_palco.rect().bottomLeft()).y()
    conf("a coluna do volume cabe na janela", base <= 767, f"(base em y={base})")
    conf("o palco inteiro cabe", j.palco.sizeHint().height() <= 767,
         f"(precisa de {j.palco.sizeHint().height()}px)")

    # --- o lugar do volume (pedido de 24/09/2026: em pe, a direita da capa)
    j.vol.setValue(80); bombear(120)
    from PySide6.QtCore import Qt as _Qt
    cap = j.capa_palco.rect(); cap.moveTopLeft(j.capa_palco.mapTo(j, j.capa_palco.rect().topLeft()))
    tor = j.torre_som.rect(); tor.moveTopLeft(j.torre_som.mapTo(j, j.torre_som.rect().topLeft()))

    conf("o volume esta EM PE", j.vol_palco.orientation() == _Qt.Vertical)
    conf("e fica a DIREITA da capa", tor.left() >= cap.right(),
         f"(capa termina em x={cap.right()}, coluna comeca em x={tor.left()})")
    conf("na mesma faixa de altura da capa (e centrada nela)",
         tor.top() >= cap.top() - 1 and tor.bottom() <= cap.bottom() + 1
         and abs((tor.top() + tor.bottom()) - (cap.top() + cap.bottom())) <= 2,
         f"(capa {cap.top()}-{cap.bottom()}, coluna {tor.top()}-{tor.bottom()})")
    fora = abs((cap.left() + cap.right()) / 2 - j.width() / 2)
    conf("a capa continua no centro da janela", fora <= 2, f"(fora do centro por {fora:.0f}px)")

    # a capa nao pode ter encolhido: era o motivo do pedido
    conf("a capa usa o teto de 62% da altura da janela", cap.height() >= int(767 * 0.62),
         f"(lado da capa = {cap.height()}px)")

    # o preenchimento cresce PARA CIMA: com volume alto, o pedaco ambar fica em cima
    from PySide6.QtWidgets import QStyle
    from PySide6.QtCore import QRect
    def y_do_handle(v):
        j.vol_palco.setValue(v); bombear(60)
        return j.vol_palco.style().sliderPositionFromValue(
            j.vol_palco.minimum(), j.vol_palco.maximum(), v,
            j.vol_palco.height(), True)   # upsideDown=True: eixo de tela
    alto, baixo = y_do_handle(90), y_do_handle(10)
    conf("volume alto deixa o punho em cima", alto < baixo,
         f"(y do punho: 90%={alto}, 10%={baixo})")
    j.vol.setValue(80); bombear(60)

    foto = os.path.join(RAIZ, "tmp", "palco_volume.png")
    os.makedirs(os.path.dirname(foto), exist_ok=True)
    j.palco.grab().save(foto)
    print("\n   foto do palco: " + foto)

    print(f"\n{len([f for f in [1] if not falhas]) and ''}"
          f"{'TUDO OK' if not falhas else 'FALHAS: ' + str(falhas)}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
