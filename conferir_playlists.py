# -*- coding: utf-8 -*-
"""Confere se TODA entrada das playlists aponta para arquivo que existe.

Roda em ~1 segundo e existe por um motivo: em 27/09/2026 uma limpeza de nomes
renomeou 29 arquivos do acervo e quebrou 17 entradas em 8 playlists. O .m3u guarda
caminho ABSOLUTO -- renomear o arquivo nao da erro nenhum, a musica so desaparece
da lista. Dano silencioso pede verificador, nao boa intencao.

    python conferir_playlists.py            # confere e resume
    python conferir_playlists.py --detalhe  # mostra cada entrada quebrada

Sai 0 se tudo aponta certo, 1 se houver quebra (serve pra rodar antes de fechar
qualquer trabalho que tenha mexido em nome de arquivo).
"""
import glob
import io
import os
import sys

MUSICA = r"D:\Music"
PLAYLISTS = r"D:\Music\Playlists"


def conferir(detalhe=False):
    if not os.path.isdir(PLAYLISTS):
        print("pasta de playlists nao encontrada: %s" % PLAYLISTS)
        return 1

    total = quebradas = 0
    ruins_por_lista = {}

    for m3u in sorted(glob.glob(os.path.join(PLAYLISTS, "*.m3u")) +
                      glob.glob(os.path.join(PLAYLISTS, "*.m3u8"))):
        nome = os.path.splitext(os.path.basename(m3u))[0]
        faltando = []
        n = 0
        for linha in io.open(m3u, encoding="utf-8", errors="replace"):
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            n += 1
            if not os.path.isfile(linha):
                faltando.append(linha)
        total += n
        quebradas += len(faltando)
        marca = "" if not faltando else "   <-- %d QUEBRADA(S)" % len(faltando)
        print("  %-24s %4d faixas%s" % (nome, n, marca))
        if faltando:
            ruins_por_lista[nome] = faltando

    print()
    print("entradas conferidas: %d | quebradas: %d" % (total, quebradas))

    if quebradas and detalhe:
        print()
        print("=== as quebradas, por playlist ===")
        for nome, faltando in ruins_por_lista.items():
            print("  [%s]" % nome)
            for f in faltando:
                print("      %s" % os.path.basename(f))

    if quebradas:
        print()
        print("COMO CONSERTAR: o caminho quebrado E o nome antigo do arquivo. Se a musica")
        print("foi renomeada, o nome original esta ali na playlist -- basta renomear de volta.")
        print("O duracoes.json do Roxin tambem guarda nomes antigos e serve de segunda fonte.")
        return 1

    # ---- orfas: arquivo no acervo que nenhuma playlist cita (informativo) ----
    citados = set()
    for m3u in glob.glob(os.path.join(PLAYLISTS, "*.m3u")) + glob.glob(os.path.join(PLAYLISTS, "*.m3u8")):
        for linha in io.open(m3u, encoding="utf-8", errors="replace"):
            linha = linha.strip()
            if linha and not linha.startswith("#"):
                citados.add(os.path.normcase(linha))
    no_disco = [os.path.join(MUSICA, f) for f in os.listdir(MUSICA)
                if f.lower().endswith((".mp3", ".m4a"))] if os.path.isdir(MUSICA) else []
    fora = [p for p in no_disco if os.path.normcase(p) not in citados]
    print("faixas no acervo sem playlist nenhuma: %d (normal -- o app junta numa lista a parte)"
          % len(fora))
    print()
    print("TUDO OK")
    return 0


if __name__ == "__main__":
    sys.exit(conferir(detalhe="--detalhe" in sys.argv))
