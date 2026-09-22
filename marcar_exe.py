# -*- coding: utf-8 -*-
"""Poe a identidade do Roxin DENTRO do executavel: icone e nome.

Por que existe: o Roxin roda por uma copia do pythonw.exe chamada Roxin.exe (o
Smart App Control desta maquina bloqueia .exe novo sem reputacao, e a copia herda
a assinatura da Python Software Foundation). Mas o Windows nao le o nome do
ARQUIVO: a barra de tarefas usa o icone embutido no binario, e o Gerenciador de
Tarefas mostra o campo FileDescription dos metadados de versao - que no pythonw.exe
dizem "Python". Renomear nao resolve; e preciso reescrever os recursos.

    python marcar_exe.py            # marca D:\\Player Musica\\Roxin.exe
    python marcar_exe.py --refazer  # recria do pythonw e marca de novo

Reescrever recursos invalida a assinatura digital. Medido em 22/09/2026 nesta
maquina: mesmo sem assinatura o executavel continua abrindo (o Smart App Control
deixou passar). Se algum dia bloquear, as saidas sao voltar ao binario assinado
(com o nome errado) ou desligar o SAC - decisao do Roger, sem volta sem reinstalar
o Windows.
"""

import ctypes
import os
import shutil
import struct
import sys
from ctypes import wintypes

EXE = r"D:\Player Musica\Roxin.exe"
ICO = r"D:\Player Musica\roxin.ico"
NOME = "Roxin"

RT_ICON = 3
RT_GROUP_ICON = 14
NULO2 = b"\x00\x00"

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

k32.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
k32.BeginUpdateResourceW.restype = wintypes.HANDLE
k32.UpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                wintypes.WORD, wintypes.LPVOID, wintypes.DWORD]
k32.UpdateResourceW.restype = wintypes.BOOL
k32.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
k32.EndUpdateResourceW.restype = wintypes.BOOL


def _id(n):
    """Recurso por numero, no formato que a API espera (ponteiro fingido)."""
    return ctypes.cast(ctypes.c_void_p(n), wintypes.LPCWSTR)


def ler_ico(caminho):
    """Devolve [(entrada de 14 bytes sem o id, bytes da imagem), ...]."""
    dados = open(caminho, "rb").read()
    reservado, tipo, qtd = struct.unpack("<HHH", dados[:6])
    if reservado != 0 or tipo != 1 or qtd == 0:
        raise ValueError("nao parece um .ico: %s" % caminho)
    saida = []
    for i in range(qtd):
        base = 6 + i * 16
        (larg, alt, cores, res, planos, bits, tam, off) = struct.unpack(
            "<BBBBHHII", dados[base:base + 16])
        imagem = dados[off:off + tam]
        entrada = struct.pack("<BBBBHHI", larg, alt, cores, res, planos, bits, tam)
        saida.append((entrada, imagem))
    return saida


def marcar_icone(exe, ico):
    imagens = ler_ico(ico)
    h = k32.BeginUpdateResourceW(exe, False)
    if not h:
        raise OSError("BeginUpdateResource falhou: %s" % ctypes.get_last_error())
    # ids 1..N substituem os icones existentes; o grupo 1 e o que a shell usa
    grupo = struct.pack("<HHH", 0, 1, len(imagens))
    for i, (entrada, imagem) in enumerate(imagens, start=1):
        buf = ctypes.create_string_buffer(imagem, len(imagem))
        if not k32.UpdateResourceW(h, _id(RT_ICON), _id(i), 1033,
                                   ctypes.cast(buf, wintypes.LPVOID), len(imagem)):
            raise OSError("UpdateResource(icone %d) falhou" % i)
        grupo += entrada + struct.pack("<H", i)
    gbuf = ctypes.create_string_buffer(grupo, len(grupo))
    if not k32.UpdateResourceW(h, _id(RT_GROUP_ICON), _id(1), 1033,
                               ctypes.cast(gbuf, wintypes.LPVOID), len(grupo)):
        raise OSError("UpdateResource(grupo de icones) falhou")
    if not k32.EndUpdateResourceW(h, False):
        raise OSError("EndUpdateResource falhou: %s" % ctypes.get_last_error())
    return len(imagens)


def marcar_nome(exe, nome=NOME):
    """Troca o texto dos metadados sem mexer no tamanho da estrutura.

    Cada campo do bloco de versao e:
        wLength(2) | wValueLength(2) | wType(2) | chave UTF-16 + fim | pad | valor + fim

    O valor cabe no mesmo espaco: "Python" (6 caracteres) e "Roxin" (5 mais o
    terminador) ocupam os mesmos 12 bytes, entao nada precisa ser recalculado. O
    wValueLength, que conta CARACTERES, e corrigido junto.

    O terminador do valor tem que ser procurado DE 2 EM 2 bytes: procurar dois
    zeros byte a byte casa no meio de um caractere UTF-16 e devolve "Pytho" em vez
    de "Python" - foi esse o bug da primeira versao, que deixou o campo intacto.
    """
    dados = bytearray(open(exe, "rb").read())
    trocas = 0
    for chave in ("FileDescription", "ProductName", "InternalName", "OriginalFilename"):
        marca = chave.encode("utf-16-le") + NULO2
        de = 0
        while True:
            i = dados.find(marca, de)
            if i < 0:
                break
            de = i + len(marca)
            j = de
            while (j + 1 < len(dados) and dados[j] == 0 and dados[j + 1] == 0
                   and (j - de) < 4):
                j += 2                       # pula o alinhamento de 4 bytes
            ini = j
            fim = ini
            while fim + 1 < len(dados):       # de 2 em 2: e UTF-16
                if dados[fim] == 0 and dados[fim + 1] == 0:
                    break
                fim += 2
            espaco = fim - ini
            if espaco <= 0 or espaco > 120:
                continue
            atual = bytes(dados[ini:fim]).decode("utf-16-le", "ignore")
            if "python" not in atual.lower():
                continue
            texto = nome if len(nome.encode("utf-16-le")) <= espaco else nome[: espaco // 2]
            cru = texto.encode("utf-16-le")
            dados[ini:fim] = cru + bytes(espaco - len(cru))
            pos_vl = i - 4                    # wValueLength, em caracteres
            if pos_vl >= 0:
                dados[pos_vl:pos_vl + 2] = (len(texto) + 1).to_bytes(2, "little")
            trocas += 1
            print("   %-18s '%s' -> '%s'" % (chave, atual, texto))
    if trocas:
        open(exe, "wb").write(bytes(dados))
    return trocas


def main():
    if "--refazer" in sys.argv or not os.path.isfile(EXE):
        origem = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.isfile(origem):
            raise SystemExit("nao achei o pythonw.exe em %s" % origem)
        shutil.copy2(origem, EXE)
        print("copiado de %s" % origem)
    print("marcando %s" % EXE)
    print("   icone: %d tamanhos gravados" % marcar_icone(EXE, ICO))
    print("   metadados: %d campos trocados" % marcar_nome(EXE))
    print("pronto")


if __name__ == "__main__":
    main()
