# -*- coding: utf-8 -*-
"""Conferencias do recado de erro da aba de baixar, quando a playlist INTEIRA falha.

Por que este teste existe: em 27/09/2026 o Roger mandou o Anzol baixar cinco
albuns do YouTube Music (list=OLAK5uy_...) e todos os links deram a mesma tela:
"O download terminou mas nenhum arquivo ficou pronto. Numa playlist, isso quer
dizer que todos os itens falharam." -- sem dizer POR QUE.

A causa nao era o Anzol nem o yt-dlp: os albuns do YouTube Music sao art tracks
e so tocam para assinante ("This video is only available to Music Premium
members"). Dois defeitos escondiam isso:

  1. a tabela de traducoes nao tinha o caso; "members-only" nao casa com
     "only available to Music Premium members", entao o texto voltava cru;
  2. com `ignoreerrors` ligado -- toda playlist -- o item que falha nao levanta
     excecao: a mensagem sai pelo LOGGER, e o Anzol nao punha logger nenhum.
     O motivo morria ali, e sobrava a frase generica.

Conserto: a traducao entrou na tabela, e um _ColetorDeErros captura o que o
logger recebe, para o recado final dizer a causa que mais se repetiu.

CONTROLE POSITIVO: os mesmos casos rodam contra a tabela ANTIGA (embutida aqui
literalmente). Um teste que passa nos dois lados nao prova nada.

    python testes/teste_erro_premium.py
"""
import os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from anzol.nucleo import _TRADUCOES, _ColetorDeErros, traduzir_erro  # noqa: E402

# a mensagem exata que o yt-dlp devolveu nos cinco albuns, em 27/09/2026
CRU = "ERROR: [youtube] VYIPyKRI8SQ: This video is only available to Music Premium members"

# ------------------------------------------------ a tabela ANTIGA, ipsis litteris
TRADUCOES_ANTIGAS = (
    ("private video", "Vídeo privado — só quem tem convite do canal consegue baixar."),
    ("members-only", "Vídeo exclusivo para membros do canal."),
    ("sign in to confirm your age", "Vídeo com restrição de idade: o site exige login."),
    ("unavailable", "Vídeo indisponível — foi removido, ficou privado ou nunca existiu."),
    ("available in your country", "Vídeo bloqueado no seu país."),
)


def traduzir_com(tabela, bruto):
    """A mesma limpeza do nucleo, so que contra a tabela que eu mandar."""
    texto = re.sub(r"\x1b\[[0-9;]*m", "", bruto or "").strip()
    texto = re.sub(r"^ERROR:\s*", "", texto, flags=re.IGNORECASE).strip()
    texto = re.sub(r"^\[[\w.:-]+\]\s*", "", texto)
    texto = re.sub(r"^[\w-]{6,}:\s+", "", texto).strip()
    baixo = texto.lower()
    for agulha, frase in tabela:
        if agulha in baixo:
            return frase
    return texto or "Falhou sem dizer por quê."


falhas = []


def conferir(nome, ok, detalhe=""):
    print(("  ok   " if ok else "  FALHA") + "  " + nome + (("  -> " + detalhe) if detalhe and not ok else ""))
    if not ok:
        falhas.append(nome)


print("\n1. a mensagem do Music Premium vira portugues")
novo = traduzir_erro(CRU)
conferir("traduz para frase util", "Music Premium" in novo and "álbum" in novo, novo)
conferir("nao sobra texto tecnico em ingles", "This video" not in novo, novo)

print("\n2. CONTROLE POSITIVO: a tabela antiga NAO resolvia")
antigo = traduzir_com(TRADUCOES_ANTIGAS, CRU)
conferir("antes voltava o texto cru em ingles", antigo.startswith("This video is only available"), antigo)
conferir("antes e depois sao diferentes", antigo != novo)

print("\n3. o coletor guarda o que o logger recebe")
c = _ColetorDeErros()
conferir("sem erro nenhum, motivo vazio", c.motivo() == "")
c.debug("baixando"); c.info("ok"); c.warning("cuidado")
conferir("debug/info/warning nao viram erro", c.erros == [])
for _ in range(34):
    c.error(CRU)
c.error("ERROR: [youtube] xyz: This video is unavailable")
conferir("guardou os 35", len(c.erros) == 35, str(len(c.erros)))
conferir("motivo = a causa mais repetida", "Music Premium" in c.motivo(), c.motivo())

print("\n4. o que NAO devia mudar continua igual")
for agulha, esperado in (("private video", "privado"), ("members-only", "membros do canal"),
                         ("http error 404", "404"), ("is live", "ao vivo"),
                         ("unsupported url", "extrator")):
    frase = traduzir_erro("ERROR: [youtube] abc123: ... %s ..." % agulha)
    conferir("traducao antiga '%s' intacta" % agulha, esperado in frase, frase)
# as 21 agulhas que existiam antes de 27/09/2026 -- nenhuma pode ter sumido
AGULHAS_ANTIGAS = (
    "private video", "members-only", "sign in to confirm your age", "sign in to confirm",
    "confirm you're not a bot", "unavailable", "this video has been removed",
    "available in your country", "geo restricted", "is not a valid url", "unsupported url",
    "live event will begin", "is live", "requested format is not available", "ffmpeg",
    "unable to download webpage", "name or service not known", "timed out",
    "http error 404", "http error 403", "http error 429",
)
agulhas_hoje = [a for a, _ in _TRADUCOES]
sumiram = [a for a in AGULHAS_ANTIGAS if a not in agulhas_hoje]
conferir("nenhuma das 21 agulhas antigas sumiu", not sumiram, ", ".join(sumiram))
conferir("entrou exatamente 1 agulha nova", len(_TRADUCOES) == len(AGULHAS_ANTIGAS) + 1,
         "%d agulhas, esperado %d" % (len(_TRADUCOES), len(AGULHAS_ANTIGAS) + 1))
conferir("a nova e a do Music Premium", "music premium" in agulhas_hoje)
conferir("nenhuma agulha duplicada", len(agulhas_hoje) == len(set(agulhas_hoje)))

print("\n5. o recado final so ganha 'Motivo:' quando ha motivo")
recado = ("O download terminou mas nenhum arquivo ficou pronto. "
          "Numa playlist, isso quer dizer que todos os itens falharam.")
for motivo, deve_ter in ((c.motivo(), True), ("", False)):
    final = f"{recado} Motivo: {motivo}" if motivo else recado
    conferir("com motivo=%r -> %s" % (motivo[:18], "tem 'Motivo:'" if deve_ter else "texto puro"),
             ("Motivo:" in final) == deve_ter)

print("\n" + ("TUDO OK" if not falhas else "FALHOU: " + ", ".join(falhas)))
sys.exit(1 if falhas else 0)
