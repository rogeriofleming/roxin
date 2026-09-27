# -*- coding: utf-8 -*-
"""Os 7 casos do coracao do Roxin Mobile -- cada um com CONTROLE POSITIVO.

    python testes/teste_empacotar.py

Controle positivo = uma versao quebrada de proposito que o teste TEM que reprovar.
Sem isso um teste verde nao prova nada: pode estar verde por nao olhar.

Tudo roda num acervo DE MENTIRA, em pasta temporaria. Este teste nunca toca em
D:\\Music nem na pasta de capas de verdade -- em 24/09/2026 um teste meu gravou no
ajustes.json real do Roger, e a licao foi essa.
"""
import hashlib
import io
import json
import os
import random
import shutil
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import empacotar as E

VERDES = []
VERMELHOS = []


def checa(ok, titulo, detalhe=""):
    (VERDES if ok else VERMELHOS).append(titulo)
    print("  %s %s%s" % ("OK  " if ok else "FALHA", titulo,
                         ("  -- " + detalhe) if detalhe and not ok else ""))
    return ok


# ---------------------------------------------------------------- o cenario

# Nomes escolhidos a dedo: acento, &, #, parenteses, apostrofo e um par que colide
# depois de trocar os caracteres proibidos por "_".
FAIXAS = [
    "Chihiro - Uma Manhã de Verão.mp3",
    "Totoro - Hey Let's Go & Walk.mp3",
    "Howl - Merry-go-round #1 (Piano).mp3",
    "Kiki - O Vôo (Official Audio).m4a",
    "Sussurros - Country Road [dQw4w9WgXcQ].mp3",
    "AC_DC - Back in Black.mp3",
    "Barravento - a_b.mp3",          # colide com o de baixo depois de sanitizar
    "Barravento - a/b.mp3",          # "/" e proibido -> vira "a_b"
]


def monta_acervo(raiz):
    """Cria acervo, playlists e capas de mentira. Devolve o que foi criado."""
    musica = os.path.join(raiz, "Music")
    listas = os.path.join(musica, "Playlists")
    capas = os.path.join(raiz, "capas")
    for p in (musica, listas, capas):
        os.makedirs(p, exist_ok=True)

    rnd = random.Random(42)          # mesmo conteudo em toda rodada
    caminhos = []
    for nome in FAIXAS:
        seguro = nome.replace("/", "\u2215")   # o "/" real nao cabe num nome de arquivo
        c = os.path.join(musica, seguro)
        with open(c, "wb") as f:
            f.write(bytes(rnd.getrandbits(8) for _ in range(2048)))
        caminhos.append(c)

    # capa para todos MENOS os dois ultimos: o caso 5 exige faixa sem capa
    for c in caminhos[:-2]:
        alvo = os.path.join(capas, E.chave_capa(os.path.basename(c)))
        with open(alvo, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"capa de mentira")

    def escreve_m3u(nome, indices, titulos=None):
        with io.open(os.path.join(listas, nome + ".m3u"), "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for k, i in enumerate(indices):
                t = (titulos or {}).get(i) or E.limpar(os.path.basename(caminhos[i]))
                f.write("#EXTINF:%d,%s\n%s\n" % (120 + i, t, caminhos[i]))

    escreve_m3u("Ghibli melhores", [0, 1, 2, 3, 4])
    escreve_m3u("Rock", [5, 0])          # a 0 repete de proposito (caso 4)
    escreve_m3u("Colisao", [6, 7])       # os dois que colidem no nome
    # uma playlist com entrada apontando para arquivo que nao existe
    with io.open(os.path.join(listas, "Quebrada.m3u"), "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n#EXTINF:100,Fantasma\n%s\n"
                % os.path.join(musica, "nao existe.mp3"))
        f.write("#EXTINF:%d,Real\n%s\n" % (130, caminhos[0]))
    return musica, listas, capas, caminhos


# ---------------------------------------------------------------- os 7 casos


def roda():
    raiz = tempfile.mkdtemp(prefix="roxin_teste_")
    try:
        musica, listas, capas, caminhos = monta_acervo(raiz)
        saida = os.path.join(raiz, "pacotes")
        base_dur = raiz          # nao existe duracoes.json aqui: tem que aguentar

        print("\n1. Empacotar uma playlist inteira")
        rel = E.empacotar(["Ghibli melhores"], saida=saida, pasta_playlists=listas,
                          capas=capas, base_duracoes=base_dur, quieto=True)
        zip1 = rel["arquivo"]
        checa(rel["faixas"] == 5, "as 5 faixas entraram", "entraram %d" % rel["faixas"])
        checa(rel["capas"] == 5, "as 5 capas entraram", "entraram %d" % rel["capas"])
        ind = E.ler_indice(zip1)
        checa(len(ind["playlists"][0]["faixas"]) == 5, "a playlist aponta as 5")
        checa(rel["faltando_no_pc"].get("Quebrada") and
              len(rel["faltando_no_pc"]["Quebrada"]) == 1,
              "entrada quebrada do PC foi DENUNCIADA, nao engolida")

        print("\n2. Conferir o pacote (o analogo do conferir_playlists)")
        checa(E.conferir(zip1, quieto=True) == [], "0 problema no pacote")
        #    controle positivo: trocar um byte de uma musica dentro do zip
        zip_ruim = os.path.join(raiz, "corrompido.zip")
        corromper(zip1, zip_ruim, ind["faixas"][0]["arquivo"])
        probs = E.conferir(zip_ruim, quieto=True)
        checa(any("sha256" in p for p in probs),
              "CONTROLE: musica corrompida e acusada", "acusou %s" % probs)

        print("\n3. Nome com acento, &, # e parenteses")
        nomes = {f["arquivo"] for f in ind["faixas"]}
        titulos = {f["titulo"] for f in ind["faixas"]}
        checa(all(not any(c in os.path.basename(n) for c in E.PROIBIDOS)
                  for n in nomes),
              "nenhum caractere proibido no nome dentro do pacote")
        checa("Uma Manhã de Verão" in " | ".join(titulos),
              "acento preservado no TITULO da tela", " | ".join(sorted(titulos)))
        checa(any("&" in t for t in titulos), "o & sobreviveu no titulo")
        checa(any("#1" in t for t in titulos), "o # sobreviveu no titulo")
        checa(not any("dQw4w9WgXcQ" in t for t in titulos),
              "o [id do video] saiu do titulo, como no app de mesa")
        with zipfile.ZipFile(zip1) as z:
            dentro = set(z.namelist())
        checa(all(f["arquivo"] in dentro for f in ind["faixas"]),
              "toda faixa do indice existe de fato dentro do pacote")

        print("\n4. Mesma faixa em duas playlists")
        rel2 = E.empacotar(["Ghibli melhores", "Rock"], saida=saida,
                           pasta_playlists=listas, capas=capas,
                           base_duracoes=base_dur, quieto=True)
        i2 = E.ler_indice(rel2["arquivo"])
        checa(len(i2["faixas"]) == 6,
              "5 + 2 com 1 repetida = 6 faixas, nao 7", "deu %d" % len(i2["faixas"]))
        arquivos = [f["arquivo"] for f in i2["faixas"]]
        checa(len(arquivos) == len(set(arquivos)), "nenhum arquivo duplicado")
        alvo = i2["playlists"][0]["faixas"][0]
        checa(alvo in i2["playlists"][1]["faixas"],
              "as duas playlists apontam para a MESMA faixa")
        with zipfile.ZipFile(rel2["arquivo"]) as z:
            musicas_dentro = [n for n in z.namelist() if n.startswith("musicas/")]
        checa(len(musicas_dentro) == 6, "o pacote guarda 6 arquivos, sem bytes repetidos")

        print("\n5. Faixa sem capa")
        rel3 = E.empacotar(["Colisao"], saida=saida, pasta_playlists=listas,
                           capas=capas, base_duracoes=base_dur, quieto=True)
        i3 = E.ler_indice(rel3["arquivo"])
        checa(len(i3["faixas"]) == 2, "as 2 faixas sem capa entraram na mesma")
        checa(all(f["capa"] is None for f in i3["faixas"]),
              "capa marcada como ausente, e a faixa NAO desapareceu")
        checa(E.conferir(rel3["arquivo"], quieto=True) == [],
              "pacote sem capa nenhuma passa na conferencia")
        #    e o par que colide depois de sanitizar nao pode se sobrescrever
        n3 = [f["arquivo"] for f in i3["faixas"]]
        checa(len(set(n3)) == 2,
              "os dois nomes que colidiam ganharam arquivos DIFERENTES", str(n3))

        print("\n6. Empacotar 2 vezes")
        rel4 = E.empacotar(["Ghibli melhores"], saida=saida, pasta_playlists=listas,
                           capas=capas, base_duracoes=base_dur, quieto=True)
        checa(rel4["mudou"] is not None, "o 2o diz o que mudou em relacao ao 1o")
        checa(rel4["mudou"]["iguais"] == 5 and not rel4["mudou"]["entraram"]
              and not rel4["mudou"]["sairam"],
              "nada mudou: 5 iguais, 0 entraram, 0 sairam", str(rel4["mudou"]))
        checa(E.conferir(rel4["arquivo"], quieto=True) == [],
              "o pacote refeito continua valido")
        #    controle positivo: tirar uma faixa da playlist e ver se ele NOTA
        with io.open(os.path.join(listas, "Ghibli melhores.m3u"), encoding="utf-8") as f:
            guardado = f.read()
        linhas = guardado.strip().split("\n")
        with io.open(os.path.join(listas, "Ghibli melhores.m3u"), "w",
                     encoding="utf-8") as f:
            f.write("\n".join(linhas[:-2]) + "\n")
        rel5 = E.empacotar(["Ghibli melhores"], saida=saida, pasta_playlists=listas,
                           capas=capas, base_duracoes=base_dur, quieto=True)
        checa(len(rel5["mudou"]["sairam"]) == 1,
              "CONTROLE: faixa tirada da playlist aparece como SAIU",
              str(rel5["mudou"]))
        with io.open(os.path.join(listas, "Ghibli melhores.m3u"), "w",
                     encoding="utf-8") as f:
            f.write(guardado)

        print("\n7. SHA256 de cada faixa, pacote x original")
        #  pacote PROPRIO, em pasta propria: o caso 6 sobrescreve o zip1 (mesmo nome de
        #  arquivo), e reler zip1 aqui mediria 4 faixas achando que mede 5. O numero
        #  esperado e LITERAL de proposito -- derivar do dado e teste que se autoconfirma.
        saida7 = os.path.join(raiz, "pacotes7")
        rel7 = E.empacotar(["Ghibli melhores"], saida=saida7, pasta_playlists=listas,
                           capas=capas, base_duracoes=base_dur, quieto=True)
        ind7 = E.ler_indice(rel7["arquivo"])
        checa(len(ind7["faixas"]) == 5, "o pacote do caso 7 tem as 5 faixas",
              "tem %d" % len(ind7["faixas"]))
        iguais = 0
        with zipfile.ZipFile(rel7["arquivo"]) as z:
            for f in ind7["faixas"]:
                if hashlib.sha256(z.read(f["arquivo"])).hexdigest() == f["sha256"]:
                    iguais += 1
        checa(iguais == 5, "as 5 faixas saem do pacote com o sha256 do indice",
              "bateram %d" % iguais)
        #    e o indice tem que bater com o ARQUIVO ORIGINAL no disco, nao so consigo
        por_titulo = {E.limpar(os.path.basename(c)): c for c in caminhos}
        conferidas = 0
        for f in ind7["faixas"]:
            c = por_titulo.get(f["titulo"])
            if c and E.sha256(c) == f["sha256"]:
                conferidas += 1
        checa(conferidas == 5,
              "os 5 sha256 do indice batem com o arquivo ORIGINAL no disco",
              "bateu em %d de 5" % conferidas)
        #    controle positivo: pacote com sha256 mentiroso tem que ser reprovado
        zip_mentira = os.path.join(raiz, "mentira.zip")
        mentir_no_indice(rel7["arquivo"], zip_mentira)
        checa(any("sha256" in p for p in E.conferir(zip_mentira, quieto=True)),
              "CONTROLE: indice com sha256 falso e reprovado")

        print("\nExtras -- as travas que o plano exige")
        checa(all(not os.path.isabs(f["arquivo"]) for f in ind7["faixas"]),
              "nenhum caminho absoluto no indice (a razao de existir do pacote)")
        bruto = json.dumps(ind7, ensure_ascii=False)
        checa("D:\\Music" not in bruto and "D:\\\\Music" not in bruto,
              "o indice nao carrega NENHUM caminho do PC")
        #    controle positivo: indice com caminho absoluto e reprovado
        zip_abs = os.path.join(raiz, "absoluto.zip")
        por_caminho_absoluto(rel7["arquivo"], zip_abs)
        checa(any("ABSOLUTO" in p for p in E.conferir(zip_abs, quieto=True)),
              "CONTROLE: caminho absoluto no indice e reprovado")
        #    controle positivo: arquivo dentro do pacote fora do indice
        zip_orfao = os.path.join(raiz, "orfao.zip")
        por_orfao(rel7["arquivo"], zip_orfao)
        checa(any("fora do indice" in p for p in E.conferir(zip_orfao, quieto=True)),
              "CONTROLE: arquivo clandestino no pacote e acusado")

        print("\nA LEI: o acervo nao pode ter sido tocado")
        checa(sorted(os.listdir(musica)) == sorted(
                  [f.replace("/", "\u2215") for f in FAIXAS] + ["Playlists"]),
              "nenhum arquivo do acervo renomeado, movido ou apagado")
        checa(len([n for n in os.listdir(listas) if n.endswith(".m3u")]) == 4,
              "as 4 playlists continuam inteiras")

    finally:
        shutil.rmtree(raiz, ignore_errors=True)

    print("\n" + "-" * 62)
    print("  %d verdes, %d vermelhos" % (len(VERDES), len(VERMELHOS)))
    if VERMELHOS:
        print("\n  FALHOU:")
        for t in VERMELHOS:
            print("   - %s" % t)
    return 1 if VERMELHOS else 0


# --------------------------------------------- fabricas de pacote quebrado


def _recria(origem, destino, troca):
    """Copia o zip aplicando `troca(nome, dados) -> (nome, dados) ou None`."""
    with zipfile.ZipFile(origem) as z_in, \
         zipfile.ZipFile(destino, "w", allowZip64=True) as z_out:
        for info in z_in.infolist():
            r = troca(info.filename, z_in.read(info.filename))
            if r is None:
                continue
            nome, dados = r
            z_out.writestr(nome, dados, compress_type=zipfile.ZIP_STORED)


def corromper(origem, destino, alvo):
    def troca(nome, dados):
        if nome == alvo:
            b = bytearray(dados)
            b[0] ^= 0xFF
            return nome, bytes(b)
        return nome, dados
    _recria(origem, destino, troca)


def mentir_no_indice(origem, destino):
    def troca(nome, dados):
        if nome == "roxin.json":
            ind = json.loads(dados.decode("utf-8"))
            ind["faixas"][0]["sha256"] = "0" * 64
            return nome, json.dumps(ind, ensure_ascii=False).encode("utf-8")
        return nome, dados
    _recria(origem, destino, troca)


def por_caminho_absoluto(origem, destino):
    def troca(nome, dados):
        if nome == "roxin.json":
            ind = json.loads(dados.decode("utf-8"))
            ind["faixas"][0]["arquivo"] = r"D:\Music\alguma.mp3"
            return nome, json.dumps(ind, ensure_ascii=False).encode("utf-8")
        return nome, dados
    _recria(origem, destino, troca)


def por_orfao(origem, destino):
    _recria(origem, destino, lambda n, d: (n, d))
    with zipfile.ZipFile(destino, "a") as z:
        z.writestr("musicas/clandestina.mp3", b"nao estou no indice")


if __name__ == "__main__":
    sys.exit(roda())
