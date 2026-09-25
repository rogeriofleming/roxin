# -*- coding: utf-8 -*-
"""A playlist tem que dar a volta NELA MESMA -- e o rodapé tem que dizer de qual
lista a música que toca veio.

Nasceu do relato do Roger em 25/09/2026: "toquei a última música da playlist e ele
começou a rodar música de fora". Era verdade, por dois caminhos diferentes:
  1. o play tinha nascido de "Todas as músicas", que vinha na ordem de leitura do
     disco -- playlist por playlist. Tocar o acervo do início era indistinguível de
     tocar a 1a playlist, até ela acabar e entrar a próxima;
  2. o rodapé mostrava o nome da lista que estava NA TELA, não a de onde a música
     tocando veio -- então dizia "Brasil" enquanto tocava faixa de outra lista.
E de lambuja: faixa posta com "Tocar a seguir" ficava na ordem PARA SEMPRE, e
voltava a tocar em toda volta da playlist.

Roda offscreen, com acervo falso, e simula o sinal EndOfMedia na mão:
    python testes/teste_loop_playlist.py
"""
import os, sys, io, tempfile, importlib.util, importlib.machinery
os.environ["QT_QPA_PLATFORM"] = "offscreen"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

ROXA, VERDE, SOLTAS = ["A1.mp3", "A3.mp3", "A2.mp3"], ["B1.mp3", "B2.mp3"], ["Z1.mp3", "Z2.mp3"]


def acervo_falso():
    base = tempfile.mkdtemp(prefix="roxin_teste_")
    pls = os.path.join(base, "Playlists"); os.makedirs(pls)
    for n in ROXA + VERDE + SOLTAS:
        io.open(os.path.join(base, n), "wb").write(b"\x00" * 64)
    for nome, ns in (("Roxa", ROXA), ("Verde", VERDE)):
        with io.open(os.path.join(pls, nome + ".m3u"), "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for n in ns:
                f.write("#EXTINF:180,%s\n%s\n" % (os.path.splitext(n)[0], os.path.join(base, n)))
    return base, pls


def main():
    base, pls = acervo_falso()
    spec = importlib.util.spec_from_loader(
        "mr", importlib.machinery.SourceFileLoader("mr", os.path.join(RAIZ, "Musica.pyw")))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.MUSICA, mod.PLAYLISTS = base, pls

    from PySide6.QtWidgets import QApplication
    from PySide6.QtMultimedia import QMediaPlayer
    QApplication([])
    j = mod.Player()
    I = {n: i for i, (n, _) in enumerate(j.listas)}
    nomes = lambda ns: [j.faixas[n]["t"] for n in ns]
    toca = lambda: j.faixas[j.tocando]["t"] if 0 <= j.tocando < len(j.faixas) else None
    na_roxa = nomes(j.listas[I["Roxa"]][1])
    falhas = []

    def checa(ok, o_que):
        print(("  OK   " if ok else "  FALHA") + "  " + o_que)
        if not ok: falhas.append(o_que)

    # 1) "Todas as musicas" em ordem alfabetica, nao agrupada por playlist
    todas = nomes(j.listas[I["Todas as músicas"]][1])
    checa(todas == sorted(todas), '"Todas as músicas" em ordem alfabética (%s)' % ", ".join(todas))
    checa(todas[:len(na_roxa)] != nomes(j.listas[I["Roxa"]][1]),
          'o começo de "Todas as músicas" não é a 1a playlist inteira')

    # 2) tocando da playlist, a volta e nela mesma -- inclusive com a tela em outra lista
    for rotulo, prep in (("tela na própria playlist", lambda: None),
                         ("tela trocada para 'Todas as músicas'", lambda: j._abre(I["Todas as músicas"])),
                         ("com filtro na busca", lambda: j.busca.setText("a"))):
        j.busca.clear(); j._abre(I["Roxa"]); j._toca_linha(0); prep()
        seq = []
        for _ in range(len(na_roxa) * 2 + 1):
            j._status(QMediaPlayer.EndOfMedia); seq.append(toca())
        fora = sorted(set(s for s in seq if s not in na_roxa))
        checa(not fora, "loop fica na playlist (%s)%s"
              % (rotulo, "" if not fora else " -- vazou: %s" % fora))
        checa(j.lista_tocando == "Roxa", "rodapé diz de onde a música veio (%s): %r"
              % (rotulo, j.sub_atual.text()))

    # 3) faixa da fila nao vira moradora da playlist
    j.busca.clear(); j._abre(I["Roxa"]); j._toca_linha(0)
    j._enfileira(j.listas[I["Fora das playlists"]][1][0], True)
    for _ in range(len(na_roxa) * 3):
        j._status(QMediaPlayer.EndOfMedia)
    intrusas = [t for t in nomes(j.ordem) if t not in na_roxa]
    checa(not intrusas, "a fila não deixa intrusa permanente na ordem%s"
          % ("" if not intrusas else " -- ficou: %s" % intrusas))

    # 4) a volta cai na PRIMEIRA da playlist
    j._abre(I["Roxa"]); j._toca_linha(len(na_roxa) - 1)      # ultima faixa
    j._status(QMediaPlayer.EndOfMedia)
    checa(toca() == na_roxa[0], "depois da última, volta para a primeira (caiu em %r)" % toca())

    print("\n%s" % ("TUDO PASSOU" if not falhas else "%d FALHA(S)" % len(falhas)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
