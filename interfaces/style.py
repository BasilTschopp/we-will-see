import os
import sys
import tkinter as tk
from tkinter import ttk
import yaml


def _style_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                        "ui", "style.yaml")


def _load() -> dict:
    try:
        with open(_style_path(), "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return {}


_S = _load()
_C = _S.get("colors", {})
_N = _S.get("nav",    {})
_U = _S.get("sub",    {})
_F = _S.get("fonts",  {})

BG      = _C.get("bg",     "#f2f3f5")
BG2     = _C.get("bg2",    "#ffffff")
FG      = _C.get("fg",     "#2c3e50")
FG_SEC  = _C.get("fg_sec", "#8899a6")
ACCENT  = _C.get("accent", "#4db6a0")
RED     = _C.get("red",    "#d47272")
BORDER  = _C.get("border", "#dfe3e8")
SEL     = _C.get("sel",    "#e0f2ef")

NAV_BG        = _N.get("bg",        "#34495e")
NAV_FG        = _N.get("fg",        "#94a3b8")
NAV_ACTIVE_BG = _N.get("active_bg", ACCENT)
NAV_ACTIVE_FG = _N.get("active_fg", "#ffffff")

SUB_BG     = _U.get("bg",     "#f2f3f5")
SUB_SEL_BG = _U.get("sel_bg", ACCENT)
SUB_SEL_FG = _U.get("sel_fg", "#ffffff")

FONT = _F.get("ui_mac"   if sys.platform == "darwin" else "ui",   "Segoe UI")
MONO = _F.get("mono_mac" if sys.platform == "darwin" else "mono", "Cascadia Code")


def apply_theme():
    s = ttk.Style()
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=FG, font=(FONT, 10))
    s.configure("TFrame", background=BG)
    s.configure("TEntry", fieldbackground=BG2, foreground=FG,
                borderwidth=0, padding=(10, 7), font=(MONO, 10),
                insertcolor=ACCENT)
    s.map("TEntry", fieldbackground=[("focus", "#f8fffe")])
    s.configure("Treeview", background=BG2, foreground=FG,
                fieldbackground=BG2, borderwidth=0,
                font=(FONT, 10), rowheight=26)
    s.map("Treeview", background=[("selected", SEL)],
          foreground=[("selected", ACCENT)])
    s.configure("Treeview.Heading", background=BG, foreground=FG,
                font=(FONT, 9), borderwidth=0, relief="flat")


def color_titlebar(root: tk.Tk):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        r, g, b = 0x2c, 0x3e, 0x50
        color = r | (g << 8) | (b << 16)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 35, ctypes.byref(ctypes.c_int(color)), 4)
        tr, tg, tb = 0xc0, 0xcc, 0xd4
        text_color = tr | (tg << 8) | (tb << 16)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 36, ctypes.byref(ctypes.c_int(text_color)), 4)
    except Exception:
        pass


