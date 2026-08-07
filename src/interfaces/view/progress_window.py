import tkinter as tk
from tkinter import ttk

from interfaces.style.style import BG, FG, ACCENT, RED, FONT


class RunProgressWindow:
    """Live step progress for headless test runs, where there is no visible
    browser to show the in-page overlay.

    One instance is shared for the whole run, so several testcases running
    in parallel (headless) are consolidated into a single window — one row
    per testcase — instead of popping up separately.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self._rows: dict[str, str] = {}
        self._closed = False

        self.win = tk.Toplevel(root)
        self.win.title("Testlauf – Fortschritt")
        self.win.configure(bg=BG)
        self.win.geometry("720x280")
        self.win.transient(root)
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        tk.Label(self.win, text="Headless-Testlauf läuft …", bg=BG,
                 fg=FG, font=(FONT, 10, "bold"), anchor="w",
                 padx=12, pady=8).pack(fill=tk.X)

        tree_frame = tk.Frame(self.win, bg=BG)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.tree = ttk.Treeview(
            tree_frame, columns=("step", "desc", "status"),
            show="tree headings", selectmode="none")
        self.tree.heading("#0",     text="Testcase")
        self.tree.heading("step",   text="Schritt")
        self.tree.heading("desc",   text="Aktueller Schritt")
        self.tree.heading("status", text="Status")
        self.tree.column("#0",     width=170, stretch=False, anchor="w")
        self.tree.column("step",   width=70,  stretch=False, anchor="center")
        self.tree.column("desc",   width=340, stretch=True,  anchor="w")
        self.tree.column("status", width=100, stretch=False, anchor="center")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.tag_configure("running", foreground=FG)
        self.tree.tag_configure("ok",      foreground=ACCENT)
        self.tree.tag_configure("error",   foreground=RED)

    def _on_close(self):
        # The run keeps going in the background; closing just hides the window.
        try:
            self.win.withdraw()
        except Exception:
            pass

    def update_step(self, key: str, idx: int, total: int, description: str) -> None:
        self.root.after(0, self._update_step_ui, key, idx, total, description)

    def _update_step_ui(self, key, idx, total, description):
        if self._closed:
            return
        try:
            values = (f"{idx}/{total}", (description or "")[:100], "läuft")
            if key in self._rows:
                self.tree.item(self._rows[key], values=values, tags=("running",))
            else:
                iid = self.tree.insert("", tk.END, text=key, values=values,
                                       tags=("running",))
                self._rows[key] = iid
        except Exception:
            pass

    def set_status(self, key: str, ok_count: int, err_count: int) -> None:
        self.root.after(0, self._set_status_ui, key, ok_count, err_count)

    def _set_status_ui(self, key, ok_count, err_count):
        if self._closed or key not in self._rows:
            return
        try:
            tag   = "error" if err_count else "ok"
            label = f"{ok_count} OK" + (f", {err_count} Fehler" if err_count else "")
            iid = self._rows[key]
            step_val, desc_val, _ = self.tree.item(iid, "values")
            self.tree.item(iid, values=(step_val, desc_val, label), tags=(tag,))
        except Exception:
            pass

    def close(self) -> None:
        self.root.after(0, self._close_ui)

    def _close_ui(self):
        self._closed = True
        try:
            self.win.destroy()
        except Exception:
            pass
