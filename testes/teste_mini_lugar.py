# -*- coding: utf-8 -*-
"""Conferencias do lugar do miniplayer (24/09/2026).

O que elas travam: a janelinha do mini de vidro e MAIOR do que o vidro que se ve
-- em volta ha uma margem transparente onde a sombra cai (ver mini_pagina.MARGEM).
Por isso o lugar guardado em `ajustes.json` e o canto do VIDRO, nao o da janela:
assim, se a margem mudar de tamanho de novo, o vidro fica onde o Roger deixou.

    python testes/teste_mini_lugar.py
"""
import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def montar():
    os.chdir(RAIZ); sys.path.insert(0, RAIZ)
    from PySide6.QtCore import QCoreApplication, Qt
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    spec = importlib.util.spec_from_file_location("roxin_app", os.path.join(RAIZ, "Musica.pyw"))
    mod = importlib.util.module_from_spec(spec); sys.modules["roxin_app"] = mod
    spec.loader.exec_module(mod)
    # teste NAO mexe nas preferencias de verdade do Roger: o ajustes.json vira um
    # de mentira em tmp/ (montar o Player ja grava nele, pelo botao Mini)
    mod.arquivo_ajustes = lambda: os.path.join(RAIZ, "tmp", "ajustes_de_teste.json")
    os.makedirs(os.path.join(RAIZ, "tmp"), exist_ok=True)
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyleSheet(mod.ESTILO)
    j = mod.Player(); j.resize(1100, 700); j.show()
    for _ in range(60): app.processEvents()
    return app, j


def main():
    app, j = montar()          # e ele quem poe a raiz no sys.path
    from mini_pagina import MARGEM
    falhas = []

    def conf(nome, cond, extra=""):
        print(f"  [{'OK   ' if cond else 'FALHA'}] {nome} {extra}")
        if not cond: falhas.append(nome)

    m = j._garante_mini()
    print(f"   mini em uso: {j._tipo_mini}\n")

    de_vidro = j._tipo_mini.startswith("vidro")
    margem = MARGEM if de_vidro else 0
    conf("a janela e o vidro mais a margem dos dois lados",
         (m.width(), m.height()) == (400 + 2 * margem, 74 + 2 * margem),
         f"(janela {m.width()}x{m.height()}, margem {margem})")

    m.poe_lugar_do_vidro(500, 400)
    p = m.lugar_do_vidro()
    conf("o lugar que se poe e o lugar que se le", (p.x(), p.y()) == (500, 400),
         f"(leu {p.x()},{p.y()})")
    conf("e a janela fica a margem acima e a esquerda disso",
         (m.pos().x(), m.pos().y()) == (500 - margem, 400 - margem),
         f"(janela em {m.pos().x()},{m.pos().y()})")

    j._ajustes["mini_lugar"] = [1, 1]          # o formato velho, de antes da margem
    j._guarda_lugar_do_mini()
    conf("grava o canto do VIDRO em ajustes.json",
         j._ajustes.get("mini_lugar_vidro") == [500, 400],
         f"({j._ajustes.get('mini_lugar_vidro')})")
    conf("e apaga a chave velha, que poria o vidro fora do lugar",
         "mini_lugar" not in j._ajustes)

    from PySide6.QtWidgets import QApplication as QA
    m.no_cantinho()
    a = (m.screen() or QA.primaryScreen()).availableGeometry()
    v = m.lugar_do_vidro()
    folga_dir = a.right() - (v.x() + 400)
    folga_bai = a.bottom() - (v.y() + 74)
    conf("no cantinho, quem fica a ~18px da borda e o VIDRO",
         abs(folga_dir - 18) <= 1 and abs(folga_bai - 18) <= 1,
         f"(direita {folga_dir}px, fundo {folga_bai}px)")

    j.close()
    print("\n" + ("TUDO OK" if not falhas else "FALHAS: " + str(falhas)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
