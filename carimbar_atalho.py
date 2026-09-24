# -*- coding: utf-8 -*-
"""Carimba o AppUserModelID no atalho (.lnk) do Roxin.

O app declara `SetCurrentProcessExplicitAppUserModelID("Roger.Roxin.Player")`.
Se o atalho nao declarar o MESMO id, o Windows trata atalho e janela como dois
aplicativos: o atalho fixado abre um segundo icone, e "fixar" a partir da janela
gera um atalho sem o argumento do script (Roxin.exe sozinho = pythonw sem script,
que abre e morre calado).

Sem dependencia externa: COM na unha, via ctypes.
Uso:  python carimbar_atalho.py            (grava e confere)
      python carimbar_atalho.py --conferir (so le, nao grava)
"""

import ctypes, os, sys
from ctypes import wintypes, POINTER, byref, c_void_p

AUMID = "Roger.Roxin.Player"

ole32 = ctypes.oledll.ole32
propsys_dll = ctypes.oledll.propsys
ole32_c = ctypes.windll.ole32


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]

    def __init__(self, texto):
        super().__init__()
        ole32.CLSIDFromString(texto, byref(self))


class PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", ctypes.c_ulong)]


class PROPVARIANT(ctypes.Structure):
    _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort),
                ("r2", ctypes.c_ushort), ("r3", ctypes.c_ushort),
                ("data", ctypes.c_byte * 16)]


CLSID_ShellLink    = GUID("{00021401-0000-0000-C000-000000000046}")
IID_IPersistFile   = GUID("{0000010B-0000-0000-C000-000000000046}")
IID_IPropertyStore = GUID("{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}")

# PKEY_AppUserModel_ID
PKEY_AUMID = PROPERTYKEY()
PKEY_AUMID.fmtid = GUID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}")
PKEY_AUMID.pid = 5

CLSCTX_INPROC_SERVER = 1
STGM_READ = 0x00000000
STGM_READWRITE = 0x00000002


def _metodo(ponteiro, indice, *argtypes):
    """Pega o metodo `indice` da vtable COM e devolve um callable ctypes."""
    vtbl = ctypes.cast(ponteiro, POINTER(POINTER(c_void_p)))[0]
    proto = ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, *argtypes)
    return proto(vtbl[indice])


VT_LPWSTR = 31
ole32_c.CoTaskMemAlloc.restype = c_void_p


def _propvariant_texto(texto):
    """InitPropVariantFromString e inline no header (nao exportada pela DLL),
    entao o PROPVARIANT VT_LPWSTR se monta na mao: a string tem que viver em
    memoria do COM, porque quem a libera depois e o PropVariantClear."""
    pv = PROPVARIANT()
    pv.vt = VT_LPWSTR
    buf = ctypes.create_unicode_buffer(texto)
    n = (len(texto) + 1) * ctypes.sizeof(ctypes.c_wchar)
    mem = ole32_c.CoTaskMemAlloc(n)
    if not mem:
        raise MemoryError("CoTaskMemAlloc falhou")
    ctypes.memmove(mem, buf, n)
    ctypes.memmove(ctypes.byref(pv, PROPVARIANT.data.offset),
                   ctypes.byref(c_void_p(mem)), ctypes.sizeof(c_void_p))
    return pv


def _release(p):
    if p:
        _metodo(p, 2)(p)


def _abrir_link(caminho, escrita):
    """Devolve (ponteiro_shelllink, ipersistfile, ipropertystore) com o .lnk carregado."""
    psl = c_void_p()
    ole32.CoCreateInstance(byref(CLSID_ShellLink), None, CLSCTX_INPROC_SERVER,
                           byref(IID_IPersistFile), byref(psl))
    # psl ja veio como IPersistFile (pedimos essa interface direto)
    ppf = psl
    modo = STGM_READWRITE if escrita else STGM_READ
    _metodo(ppf, 5, wintypes.LPCWSTR, ctypes.c_ulong)(ppf, caminho, modo)  # Load

    pps = c_void_p()
    _metodo(ppf, 0, POINTER(GUID), POINTER(c_void_p))(ppf, byref(IID_IPropertyStore),
                                                      byref(pps))  # QueryInterface
    return ppf, pps


def ler(caminho):
    ppf, pps = _abrir_link(caminho, escrita=False)
    try:
        pv = PROPVARIANT()
        _metodo(pps, 5, POINTER(PROPERTYKEY), POINTER(PROPVARIANT))(
            pps, byref(PKEY_AUMID), byref(pv))            # GetValue
        if pv.vt == 0:                                     # VT_EMPTY
            return None
        buf = ctypes.c_wchar_p()
        propsys_dll.PropVariantToStringAlloc(byref(pv), byref(buf))
        valor = buf.value
        ole32_c.CoTaskMemFree(buf)
        ole32_c.PropVariantClear(byref(pv))
        return valor
    finally:
        _release(pps); _release(ppf)


def gravar(caminho, aumid=AUMID):
    ppf, pps = _abrir_link(caminho, escrita=True)
    try:
        pv = _propvariant_texto(aumid)
        _metodo(pps, 6, POINTER(PROPERTYKEY), POINTER(PROPVARIANT))(
            pps, byref(PKEY_AUMID), byref(pv))            # SetValue
        _metodo(pps, 7)(pps)                               # Commit
        ole32_c.PropVariantClear(byref(pv))
        # Save(NULL, TRUE) grava o .lnk no mesmo caminho
        _metodo(ppf, 6, wintypes.LPCWSTR, wintypes.BOOL)(ppf, None, True)
    finally:
        _release(pps); _release(ppf)


def alvos():
    barra = os.path.join(os.environ["APPDATA"], "Microsoft", "Internet Explorer",
                         "Quick Launch", "User Pinned", "TaskBar", "Roxin.lnk")
    aqui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Roxin.lnk")
    menu = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows",
                        "Start Menu", "Programs", "Roxin.lnk")
    desktop = os.path.join(os.path.expanduser("~"), "Desktop", "Roxin.lnk")
    return [p for p in (aqui, barra, menu, desktop) if os.path.isfile(p)]


if __name__ == "__main__":
    ole32.CoInitialize(None)
    so_conferir = "--conferir" in sys.argv
    lista = alvos()
    if not lista:
        print("Nenhum Roxin.lnk encontrado."); sys.exit(1)
    falhou = False
    for p in lista:
        antes = ler(p)
        if not so_conferir and antes != AUMID:
            try:
                gravar(p)
            except OSError as e:
                print(f"[ERRO ] {p}\n        {e}"); falhou = True; continue
        depois = ler(p)
        marca = "OK  " if depois == AUMID else "FALHA"
        if depois != AUMID:
            falhou = True
        print(f"[{marca}] {p}\n        antes: {antes!r}  ->  agora: {depois!r}")
    sys.exit(1 if falhou else 0)
