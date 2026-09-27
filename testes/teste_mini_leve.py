# -*- coding: utf-8 -*-
"""Conferencias da escolha do miniplayer (peso do app).

Por que este teste existe: em 27/09/2026 o Roger pediu o app "tao leve que nao
consuma quase nada de RAM". Medido offscreen, via tasklist:

    com o miniplayer de VIDRO : 190,8 MB  (135,6 principal + 55,3 QtWebEngineProcess)
    com o miniplayer PINTADO  :  66,9 MB  (nenhum processo filho)

O vidro e um QWebEngineView -- um Chromium dentro do app -- e responde por 124 MB,
65% do consumo. O app ja tinha o miniplayer pintado a mao como plano B para maquina
sem QtWebEngine; agora ele tambem e ESCOLHA, pela chave "mini_vidro" do ajustes.json.

O padrao continua sendo o VIDRO: sem a chave, nada muda. Desligar e decisao do Roger,
porque o custo e visual (perde o vidro liquido, que e trabalho dele).

CONTROLE POSITIVO: o _garante_mini() ANTIGO (embutido aqui) ignora o ajuste e sempre
tenta o vidro. Um teste que passa nos dois lados nao prova nada.

    python testes/teste_mini_leve.py
"""
import io, os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTE = io.open(os.path.join(RAIZ, "Musica.pyw"), encoding="utf-8").read()

falhas = []


def conferir(nome, ok, detalhe=""):
    print(("  ok   " if ok else "  FALHA") + "  " + nome + (("  -> " + str(detalhe)) if not ok else ""))
    if not ok:
        falhas.append(nome)


# ------------------------------------------- o codigo de hoje, extraido do fonte
m = re.search(r"def _garante_mini\(self\):(.*?)\n    def ", FONTE, re.S)
corpo = m.group(1) if m else ""

print("\n1. o ajuste manda na escolha")
conferir("le a chave mini_vidro", '_ajustes.get("mini_vidro", True)' in corpo)
conferir("o padrao e o VIDRO (default True)", '"mini_vidro", True' in corpo)
conferir("desligado, usa Mini (pintado a mao)", "self.mini = Mini(self)" in corpo)
conferir("o fallback antigo continua existindo",
         "sem QtWebEngine" in corpo and "except Exception" in corpo)
conferir("so importa mini_vidro dentro do ramo do vidro",
         corpo.index('_ajustes.get("mini_vidro"') < corpo.index("from mini_vidro import MiniVidro"))

print("\n2. CONTROLE POSITIVO: o codigo ANTIGO ignorava o ajuste")
ANTIGO = '''
        if self.mini is not None:
            return self.mini
        try:
            from mini_vidro import MiniVidro
            self.mini = MiniVidro(self)
        except Exception as e:
            self.mini = Mini(self)
'''
conferir("o antigo nao consulta mini_vidro", "mini_vidro" not in ANTIGO.replace("from mini_vidro", ""))
conferir("antigo e novo sao diferentes", ANTIGO.strip() != corpo.strip())

print("\n3. teto do cache de miniaturas")
conferir("QPixmapCache.setCacheLimit chamado", "QPixmapCache.setCacheLimit(" in FONTE)
mm = re.search(r"QPixmapCache\.setCacheLimit\((\d+)\s*\*\s*1024\)", FONTE)
conferir("teto entre 8 e 64 MB", bool(mm) and 8 <= int(mm.group(1)) <= 64,
         mm.group(1) if mm else "nao achei")

print("\n4. o que NAO devia mudar")
conferir("mini_lugar_vidro continua sendo lido", 'mini_lugar_vidro' in FONTE)
conferir("a chave 'mini' (liga/desliga) segue intacta", '_ajustes["mini"] = bool(on)' in FONTE)
conferir("MiniVidro nao foi apagado do projeto",
         os.path.isfile(os.path.join(RAIZ, "mini_vidro.py")))
conferir("a classe Mini continua existindo", "class Mini(" in FONTE)

print("\n" + ("TUDO OK" if not falhas else "FALHOU: " + ", ".join(falhas)))
sys.exit(1 if falhas else 0)
