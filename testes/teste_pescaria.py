# -*- coding: utf-8 -*-
"""Conferencias da aba de baixar (a "pescaria") do Roxin.

Por que este teste existe: em 24/09/2026 o Roger baixou um audio de 298 MB. O
arquivo ficou inteiro em D:\\Music e a tela disse "Nao deu certo." em laranja.

Causa: a tela tratava como "em andamento" uma lista FECHADA de status
("iniciando", "baixando", "convertendo") e caia no ramo de erro para qualquer
outro. Mas o nucleo do Anzol nunca escreve "convertendo" -- ele escreve
"processando" (assim que o download termina e comeca o pos-processamento) e
"cancelando". Em arquivo pequeno a conclusao chegava dentro dos 400 ms do
relogio e ninguem via; em arquivo grande, o tique caia em "processando" e a
pescaria declarava erro com o download bem-sucedido no disco.

Conserto: a lista passa a ser a dos status de FIM. Tudo que nao e fim e
trabalho em andamento -- vocabulario novo no motor nunca mais vira erro falso.

Segundo caso: a caixa "por tambem em X" so era calculada no instante em que o
painel abria; quem abria o painel e depois entrava numa playlist ficava com ela
cinza dizendo "abra uma primeiro".

CONTROLE POSITIVO: os mesmos casos rodam contra o codigo ANTIGO (embutido aqui
literalmente). Um teste que passa nos dois lados nao prova nada.

    python testes/teste_pescaria.py
"""
import io, os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTE = io.open(os.path.join(RAIZ, "Musica.pyw"), encoding="utf-8").read()

FIM_DA_PESCA = ("concluido", "erro", "cancelado")
FASE_PESCA = {"processando": "convertendo\u2026", "cancelando": "cancelando\u2026"}

ARQUIVO_DA_LISTA = {"Noturnas": r"D:\Music\Playlists\Noturnas.m3u"}

# ------------------------------------------------ o codigo ANTIGO, ipsis litteris
OLHAR_ANTIGO = '''
def _olhar_pesca(self):
    n = anzol()
    if not (n and self._job):
        self._relogio_pesca.stop(); return
    j = n.ler_job(self._job)
    if not j:
        self._relogio_pesca.stop(); self._fim_da_pesca(); return
    titulo = j.get("titulo") or ""
    st = j.get("status")
    if st in ("iniciando", "baixando", "convertendo"):
        partes = [titulo or "baixando..."]
        if j.get("pct"):
            partes.append("%.0f%%" % j["pct"])
        if j.get("velocidade"):
            partes.append(str(j["velocidade"]))
        if j.get("eta"):
            partes.append("faltam %s" % j["eta"])
        self._recado("  -  ".join(partes))
        return
    self._relogio_pesca.stop()
    if st == "concluido":
        nomes = [a["nome"] for a in (j.get("arquivos") or [])]
        entraram = [x for x in (self._guardar_pescado(nm) for nm in nomes) if x is not None]
        if entraram:
            self._recado("Pronto.", "amb")
            self.link.clear()
        else:
            self._recado("Baixou, mas nao consegui por na lista.", "#e8834a")
    elif st == "cancelado":
        self._recado("Cancelado.")
    else:
        self._recado(j.get("erro") or "N\u00e3o deu certo.", "#e8834a")
    self._fim_da_pesca()
'''


class Bobo(object):
    """Aceita qualquer coisa sem reclamar: Qt de mentira."""
    def __getattr__(self, _):
        return Bobo()

    def __call__(self, *a, **k):
        return Bobo()


class Motor(object):
    """O Anzol falso: devolve o job que o caso quer."""
    def __init__(self):
        self.job = {}

    def ler_job(self, _):
        return dict(self.job)


MOTOR = Motor()


def extrair(nome):
    """Pega o metodo REAL do Musica.pyw e o devolve como funcao solta."""
    m = re.search(r"^    def %s\(self.*?(?=^    def )" % nome, FONTE, re.S | re.M)
    if not m:
        raise SystemExit("nao achei o metodo %s em Musica.pyw" % nome)
    corpo = "\n".join(l[4:] if l.startswith("    ") else l
                      for l in m.group(0).splitlines())
    ns = {"anzol": lambda: MOTOR, "FIM_DA_PESCA": FIM_DA_PESCA,
          "FASE_PESCA": FASE_PESCA, "QGraphicsOpacityEffect": lambda *a: Bobo(),
          "QEasingCurve": Bobo(), "MOV_PADRAO": 1, "suave": lambda *a, **k: None,
          "ARQUIVO_DA_LISTA": ARQUIVO_DA_LISTA, "M": Bobo()}   # M = a paleta
    exec(compile(corpo, nome, "exec"), ns)
    return ns[nome]


class Relogio(object):
    def __init__(self):
        self.parado = False

    def stop(self):
        self.parado = True


class Caixa(object):
    def __init__(self):
        self.texto, self.ligada, self.marcada = "", None, True

    def setEnabled(self, v):
        self.ligada = v

    def setText(self, t):
        self.texto = t

    def setChecked(self, v):
        self.marcada = v

    def isChecked(self):
        return self.marcada


class Pescaria(Bobo):
    def __init__(self, visivel):
        self._v = visivel

    def isVisible(self):
        return self._v


class Tela(object):
    """Um 'self' de mentira com o minimo que os metodos tocam."""
    def __init__(self, lista="Noturnas", pescaria_visivel=True):
        self._job = "abc"
        self._relogio_pesca = Relogio()
        self.recados = []
        self.na_playlist = Caixa()
        self.lista = lista
        self.pescaria = Pescaria(pescaria_visivel)
        self.busca, self.tab, self.link = Bobo(), Bobo(), Bobo()
        self.guardados = []
        self.fim = False
        self.chamou_alvo = False
        self.pediu_capa = None
        self.faixas = [{"t": "faixa"}]

    # -- o que os metodos reais chamam
    def _recado(self, texto, cor=None):
        self.recados.append((texto, cor))

    def _fim_da_pesca(self):
        self.fim = True

    def _guardar_pescado(self, nome):
        self.guardados.append(nome)
        return 0

    def _busca_capas(self, nomes):
        self.pediu_capa = list(nomes)

    def _lista_atual(self):
        return self.lista, [], ARQUIVO_DA_LISTA.get(self.lista)

    def _filtra(self):
        pass

    def _alvo_na_tela(self):
        self.chamou_alvo = True


CASOS = []


def caso(nome):
    def deco(f):
        CASOS.append((nome, f))
        return f
    return deco


# ---------------------------------------------------------------- os casos
@caso("status 'processando' nao e erro (o caso do .m4a de 298 MB)")
def c1(olhar, alvo, abre):
    t = Tela()
    MOTOR.job = {"status": "processando", "titulo": "Campfire", "pct": 100.0}
    olhar(t)
    assert not t.fim, "declarou fim da pesca com o trabalho em andamento"
    assert not t._relogio_pesca.parado, "parou de olhar o job"
    assert not any("deu certo" in x for x, _ in t.recados), t.recados
    assert "convertendo" in t.recados[-1][0], t.recados


@caso("status 'cancelando' tambem nao e erro")
def c2(olhar, alvo, abre):
    t = Tela()
    MOTOR.job = {"status": "cancelando", "titulo": "Campfire"}
    olhar(t)
    assert not t.fim and not t._relogio_pesca.parado, t.recados
    assert not any("deu certo" in x for x, _ in t.recados), t.recados


@caso("status desconhecido do motor nao vira erro falso")
def c3(olhar, alvo, abre):
    t = Tela()
    MOTOR.job = {"status": "esperando_vaga", "titulo": "Campfire"}
    olhar(t)
    assert not any("deu certo" in x for x, _ in t.recados), t.recados


@caso("baixando continua mostrando porcentagem e ETA")
def c4(olhar, alvo, abre):
    t = Tela()
    MOTOR.job = {"status": "baixando", "titulo": "Campfire", "pct": 42.0, "eta": "3min"}
    olhar(t)
    txt = t.recados[-1][0]
    assert "42%" in txt and "3min" in txt, txt
    assert not t.fim


@caso("concluido ainda guarda o arquivo e encerra")
def c5(olhar, alvo, abre):
    t = Tela()
    MOTOR.job = {"status": "concluido", "arquivos": [{"nome": "x.m4a"}]}
    olhar(t)
    assert t.guardados == ["x.m4a"], t.guardados
    assert t.fim and t._relogio_pesca.parado


@caso("concluido vai atras da capa do que baixou")
def c5b(olhar, alvo, abre):
    t = Tela()
    MOTOR.job = {"status": "concluido", "arquivos": [{"nome": "x [abcdefghijk].m4a"}]}
    olhar(t)
    assert t.pediu_capa == ["x [abcdefghijk].m4a"], t.pediu_capa


@caso("erro de verdade continua aparecendo, com a frase do motor")
def c6(olhar, alvo, abre):
    t = Tela()
    MOTOR.job = {"status": "erro", "erro": "Video privado."}
    olhar(t)
    assert t.recados[-1] == ("Video privado.", "#e8834a"), t.recados
    assert t.fim and t._relogio_pesca.parado


@caso("cancelado continua sendo cancelado, nao erro")
def c7(olhar, alvo, abre):
    t = Tela()
    MOTOR.job = {"status": "cancelado"}
    olhar(t)
    assert t.recados[-1][0] == "Cancelado." and t.fim, t.recados


@caso("playlist aberta liga a caixa com o nome dela")
def c8(olhar, alvo, abre):
    t = Tela(lista="Noturnas")
    alvo(t)
    assert t.na_playlist.ligada is True, t.na_playlist.texto
    assert "Noturnas" in t.na_playlist.texto, t.na_playlist.texto


@caso("lista virtual desliga a caixa, desmarca e diz por que")
def c9(olhar, alvo, abre):
    t = Tela(lista="Todas as m\u00fasicas")
    alvo(t)
    assert t.na_playlist.ligada is False
    assert t.na_playlist.marcada is False, "ficou marcada numa lista sem .m3u"
    assert "Todas as m\u00fasicas" in t.na_playlist.texto, t.na_playlist.texto


@caso("trocar de lista com o painel aberto re-le o alvo")
def c10(olhar, alvo, abre):
    t = Tela(pescaria_visivel=True)
    abre(t, 3)
    assert t.chamou_alvo, "trocou de playlist e a caixa ficou congelada"


@caso("sem painel aberto, trocar de lista nao explode")
def c11(olhar, alvo, abre):
    t = Tela(pescaria_visivel=False)
    abre(t, 2)
    assert t.lista_idx == 2


def rodar(rotulo, olhar, alvo, abre):
    print("\n== %s ==" % rotulo)
    ok = 0
    for nome, f in CASOS:
        try:
            f(olhar, alvo, abre)
            print("  [ok]    %s" % nome)
            ok += 1
        except AssertionError as e:
            print("  [FALHA] %s -> %s" % (nome, e))
        except Exception as e:
            print("  [ERRO]  %s -> %s: %s" % (nome, type(e).__name__, e))
    print("  %d/%d" % (ok, len(CASOS)))
    return ok


if __name__ == "__main__":
    novo = (extrair("_olhar_pesca"), extrair("_alvo_na_tela"), extrair("_abre"))
    ok_novo = rodar("CODIGO DE HOJE (Musica.pyw)", *novo)

    ns = {"anzol": lambda: MOTOR}
    exec(compile(OLHAR_ANTIGO, "antigo", "exec"), ns)

    def alvo_antigo(t):          # antes: texto fixo, sem desmarcar
        nome, _i, arq = t._lista_atual()
        t.na_playlist.setEnabled(bool(arq))
        t.na_playlist.setText("p\u00f4r tamb\u00e9m em %s" % nome if arq
                              else "p\u00f4r numa playlist (abra uma primeiro)")

    def abre_antigo(t, i):       # antes: _abre nao mexia na caixa
        t.lista_idx = i
        t._filtra()

    ok_velho = rodar("CONTROLE POSITIVO (codigo de antes)",
                     ns["_olhar_pesca"], alvo_antigo, abre_antigo)

    print("\nhoje %d/%d  ·  antes %d/%d"
          % (ok_novo, len(CASOS), ok_velho, len(CASOS)))
    if ok_velho == len(CASOS):
        print("!! o teste nao reprova o defeito -- nao prova nada")
        sys.exit(2)
    sys.exit(0 if ok_novo == len(CASOS) else 1)
