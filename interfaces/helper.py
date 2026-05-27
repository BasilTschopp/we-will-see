import os
import sys
import tkinter as tk

from interfaces.style import BG, FG_SEC, BORDER, FONT


def add_tooltip(widget: tk.Widget, text: str):
    tip = None

    def show(event):
        nonlocal tip
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        tk.Label(tip, text=text, bg="#333", fg="#fff",
                 font=("Segoe UI", 9), padx=6, pady=3).pack()

    def hide(event):
        nonlocal tip
        if tip:
            tip.destroy()
            tip = None

    widget.bind("<Enter>", show)
    widget.bind("<Leave>", hide)


def form_row(parent: tk.Widget, label_text: str,
             width: int = 14) -> tk.Frame:
    row = tk.Frame(parent, bg=BG)
    row.pack(fill=tk.X, pady=3)
    tk.Label(row, text=label_text, bg=BG, fg=FG_SEC,
             font=(FONT, 9), width=width, anchor="w").pack(side=tk.LEFT)
    return row


def divider(parent: tk.Widget, pady: int = 10):
    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=pady)


def get_categories() -> list[str]:
    from adapters.database.settings import get_categories as _db_cats
    return _db_cats()


def results_dir() -> str:
    d = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                     "files", "testresults")
    os.makedirs(d, exist_ok=True)
    return d


