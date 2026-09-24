# -*- coding: utf-8 -*-
"""Conferencia da sombra do miniplayer de vidro (24/09/2026).

O que ela trava: a janelinha e transparente e a sombra do vidro e desenhada DENTRO
dela (CSS box-shadow). Se a sombra pedir mais espaco do que a margem transparente
oferece, o Windows a corta na borda da janela -- e o corte aparece como um QUADRADO
escuro em volta do vidro arredondado, que foi a queixa do Roger.

A medida e o CANAL ALFA da foto da pagina: se a sombra couber, os pixels da borda
da janela sao transparentes de verdade (alfa ~ 0). Alfa alto na borda = quadrado.

    python testes/teste_sombra_mini.py
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

TETO_BORDA = 2      # alfa (0-255) tolerado nos 2 pixels extremos da janela
TMP = os.path.join(RAIZ, "tmp")


def foto_da_pagina():
    from mini_pagina import PAGINA, MARGEM
    from mini_vidro import MiniVidro

    os.makedirs(TMP, exist_ok=True)
    html = os.path.join(TMP, "mini_sombra.html")
    png = os.path.join(TMP, "mini_sombra.png")
    with open(html, "w", encoding="utf-8") as f:
        f.write(PAGINA)
    r = subprocess.run(
        ["node", os.path.join(RAIZ, "testes", "_foto_pagina.js"), html,
         str(MiniVidro.LARGURA), str(MiniVidro.ALTURA), png, "700"],
        capture_output=True, text=True)
    print("   " + (r.stdout or r.stderr).strip().replace("\n", "\n   "))
    if not os.path.exists(png):
        print("ERRO: a foto nao saiu — sem foto nao ha veredito (nao e 'passou').")
        sys.exit(2)
    return np.array(Image.open(png).convert("RGBA")), MARGEM


def main():
    print("Sombra do miniplayer — o quadrado em volta do vidro\n")
    img, margem = foto_da_pagina()
    a = img[:, :, 3].astype(int)
    alt, larg = a.shape
    print(f"   janela {larg}x{alt}, margem transparente declarada: "
          f"{margem}px de cada lado\n")

    bordas = {
        "topo":     a[0:2, :],
        "base":     a[-2:, :],
        "esquerda": a[:, 0:2],
        "direita":  a[:, -2:],
    }
    falhas = []
    for nome, faixa in bordas.items():
        pico = int(faixa.max())
        ok = pico <= TETO_BORDA
        print(f"  [{'OK   ' if ok else 'FALHA'}] borda {nome}: alfa maximo {pico} "
              f"(teto {TETO_BORDA})")
        if not ok:
            falhas.append(f"borda {nome} (alfa {pico})")

    # perfil de baixo para cima no meio da janela: onde a sombra comeca e termina
    col = a[:, larg // 2]
    print("\n   perfil do alfa na coluna do meio, de baixo para cima (12 px):")
    print("   " + " ".join(f"{int(v):3d}" for v in col[-12:][::-1]))

    print()
    if falhas:
        print("FALHAS: " + ", ".join(falhas))
        print("  -> a sombra e cortada na borda da janela: e isso que o Roger ve "
              "como quadrado.")
        return 1
    print("TUDO OK — a sombra morre antes da borda; nao ha quadrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
