# -*- coding: utf-8 -*-
"""Conferencias do cache negativo de capas.

Por que este teste existe: em 27/09/2026 o Roger relatou o som PICOTANDO ao tocar.
O arquivo nao estava corrompido (decodificava limpo no ffmpeg). A causa provavel era
leitura de disco: o Capeiro roda capas.gerar() quando o app abre, e gerar() relia
TODA faixa sem miniatura procurando imagem embutida -- 320 faixas do acervo antigo,
~26 s de disco, disputando com o audio.

Nenhuma delas tem imagem embutida, e isso nao muda; mas gerar() nao guardava esse
"ja procurei aqui e nao tem", entao a leitura se repetia a cada abertura, para sempre.

Conserto: um registro (sem_capa.json) guarda nome -> mtime:tamanho de quem foi
verificado e nao tem capa. Se o carimbo bate, o arquivo NAO e aberto. Se a musica
mudar (mtime/tamanho diferentes), e reverificada. forcar=True ignora o registro.

CONTROLE POSITIVO: o mesmo caso roda contra o gerar() ANTIGO (embutido aqui), que
abre o arquivo sempre. Um teste que passa nos dois lados nao prova nada.

    python testes/teste_cache_negativo.py
"""
import io, json, os, shutil, sys, tempfile, time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import capas as CP

falhas = []


def conferir(nome, ok, detalhe=""):
    print(("  ok   " if ok else "  FALHA") + "  " + nome + (("  -> " + str(detalhe)) if not ok else ""))
    if not ok:
        falhas.append(nome)


# ---------------------------------------------- cenario de mentira, em pasta temp
tmp = tempfile.mkdtemp(prefix="roxin_teste_")
musica = os.path.join(tmp, "Music")
cache = os.path.join(tmp, "cache", "capas")
os.makedirs(musica)
os.makedirs(cache)

for n in ("A sem capa.mp3", "B sem capa.mp3", "C sem capa.m4a"):
    io.open(os.path.join(musica, n), "wb").write(b"\x00" * 4096)

MUSICA_REAL, CACHE_REAL = CP.MUSICA, CP.pasta_cache
CP.MUSICA = musica
CP.pasta_cache = lambda: cache

# conta quantas vezes o arquivo e ABERTO para procurar imagem
leituras = {"n": 0}
_embutida_real = CP.imagem_embutida


def embutida_contando(caminho):
    leituras["n"] += 1
    return None                     # nenhuma tem imagem embutida


CP.imagem_embutida = embutida_contando

print("\n1. primeira passada: le todos os arquivos")
leituras["n"] = 0
CP.gerar(quieto=True)
primeira = leituras["n"]
conferir("abriu os 3 arquivos", primeira == 3, primeira)
conferir("registro foi criado", os.path.isfile(CP.arquivo_sem_capa()))
reg = json.load(io.open(CP.arquivo_sem_capa(), encoding="utf-8"))
conferir("registro tem os 3", len(reg) == 3, len(reg))

print("\n2. segunda passada: NAO deve reler nada")
leituras["n"] = 0
com, sem, erro = CP.gerar(quieto=True)
conferir("zero leituras de disco", leituras["n"] == 0, leituras["n"])
conferir("ainda reporta as 3 como sem capa", sem == 3, sem)

print("\n3. CONTROLE POSITIVO: o gerar() ANTIGO relia sempre")


def gerar_antigo():
    """Como era antes de 27/09/2026: sem registro, abre o arquivo toda vez."""
    n = 0
    for nome in sorted(os.listdir(CP.MUSICA)):
        if os.path.splitext(nome)[1].lower() not in (".mp3", ".m4a"):
            continue
        if os.path.exists(os.path.join(CP.pasta_cache(), CP.chave(nome))):
            continue
        CP.imagem_embutida(os.path.join(CP.MUSICA, nome))
        n += 1
    return n


leituras["n"] = 0
gerar_antigo()
conferir("o antigo abre os 3 de novo", leituras["n"] == 3, leituras["n"])
conferir("antes e depois sao diferentes", leituras["n"] != 0)

print("\n4. musica que MUDA volta a ser verificada")
alvo = os.path.join(musica, "B sem capa.mp3")
time.sleep(1.1)
io.open(alvo, "wb").write(b"\x01" * 8192)      # tamanho e mtime diferentes
leituras["n"] = 0
CP.gerar(quieto=True)
conferir("releu so a que mudou", leituras["n"] == 1, leituras["n"])

print("\n5. forcar=True ignora o registro")
leituras["n"] = 0
CP.gerar(forcar=True, quieto=True)
conferir("com forcar, le todas de novo", leituras["n"] == 3, leituras["n"])

print("\n6. faixa que GANHA capa sai do registro")
CP.imagem_embutida = _embutida_real
io.open(os.path.join(cache, CP.chave("C sem capa.m4a")), "wb").write(b"x")
CP.gerar(quieto=True)
reg = json.load(io.open(CP.arquivo_sem_capa(), encoding="utf-8"))
conferir("a que ganhou capa saiu do registro", "c sem capa.m4a" not in reg, list(reg))

CP.MUSICA, CP.pasta_cache, CP.imagem_embutida = MUSICA_REAL, CACHE_REAL, _embutida_real
shutil.rmtree(tmp, ignore_errors=True)

print("\n" + ("TUDO OK" if not falhas else "FALHOU: " + ", ".join(falhas)))
sys.exit(1 if falhas else 0)
