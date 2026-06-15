import tkinter as tk
from tkinter import ttk

from interfaces.style.style import BG, BG2, FG, FG_SEC, ACCENT, RED, BORDER, FONT
from interfaces.style.style import SUB_BG, SUB_SEL_BG, SUB_SEL_FG


def _stat_card(parent: tk.Frame, title: str, value: str, color: str) -> tk.Frame:
    card = tk.Frame(parent, bg=BG2, bd=0, highlightthickness=1,
                    highlightbackground=BORDER)
    tk.Label(card, text=value, bg=BG2, fg=color,
             font=(FONT, 26, "bold"), anchor="w").pack(
        fill=tk.X, padx=16, pady=(12, 0))
    tk.Label(card, text=title, bg=BG2, fg=FG_SEC,
             font=(FONT, 9), anchor="w").pack(
        fill=tk.X, padx=16, pady=(0, 12))
    return card


class ViewDashboard:

    def build_sub(self, parent: tk.Frame):
        self.sub_dashboard = tk.Frame(parent, bg=SUB_BG)

        self.release_listbox = tk.Listbox(
            self.sub_dashboard, bg=SUB_BG, fg=FG,
            selectbackground=SUB_SEL_BG, selectforeground=SUB_SEL_FG,
            font=(FONT, 10), borderwidth=0, highlightthickness=0,
            activestyle="none", relief="flat", exportselection=False,
            selectmode=tk.SINGLE)
        self.release_listbox.pack(fill=tk.BOTH, expand=True,
                                  padx=(10, 4), pady=(0, 6))
        self.release_listbox.bind("<<ListboxSelect>>",
                                  self._on_release_select)

    def build_content(self, parent: tk.Frame):
        self.content_dashboard = tk.Frame(parent, bg=BG)

        inner = tk.Frame(self.content_dashboard, bg=BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        self._dash_release_label = tk.Label(inner, text="", bg=BG)

        # Stat cards row
        self._dash_cards_row = tk.Frame(inner, bg=BG)
        self._dash_cards_row.pack(fill=tk.X, pady=(0, 16))
        for i in range(2):
            self._dash_cards_row.columnconfigure(i, weight=1, uniform="card")
        self._dash_cards_row.rowconfigure(0, weight=1)

        self._card_runs      = None
        self._card_steps     = None
        self._card_passrate  = None

        tree_frame = tk.Frame(inner, bg=BG)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self._dash_tree = ttk.Treeview(
            tree_frame,
            columns=("date", "run", "total", "ok", "errors", "pct"),
            show="headings", selectmode="browse")
        self._dash_tree.heading("date",   text="Date")
        self._dash_tree.heading("run",    text="Run")
        self._dash_tree.heading("total",  text="Steps")
        self._dash_tree.heading("ok",     text="OK")
        self._dash_tree.heading("errors", text="Errors")
        self._dash_tree.heading("pct",    text="Pass %")
        self._dash_tree.column("date",   width=130, minwidth=100, stretch=False, anchor="w")
        self._dash_tree.column("run",    width=300, minwidth=120, anchor="w")
        self._dash_tree.column("total",  width=60,  minwidth=50,  stretch=False, anchor="e")
        self._dash_tree.column("ok",     width=60,  minwidth=50,  stretch=False, anchor="e")
        self._dash_tree.column("errors", width=60,  minwidth=50,  stretch=False, anchor="e")
        self._dash_tree.column("pct",    width=70,  minwidth=50,  stretch=False, anchor="e")
        self._dash_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._dash_tree.tag_configure("err",     foreground=FG)
        self._dash_tree.tag_configure("ok",      foreground=FG)
        self._dash_tree.tag_configure("neutral", foreground=FG)

        sb = ttk.Scrollbar(tree_frame, orient="vertical",
                           command=self._dash_tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._dash_tree.configure(yscrollcommand=sb.set)

    # ------------------------------------------------------------------

    def _refresh_dashboard(self):
        from adapters.database.testresults import fetch_run_summaries, list_releases

        summaries = fetch_run_summaries()
        releases  = list_releases()
        unnamed   = any(not s["release"] for s in summaries)

        # Rebuild listbox
        current_sel = self._current_release_selection()
        self.release_listbox.delete(0, tk.END)
        self.release_listbox.insert(tk.END, "All")
        for rel in releases:
            self.release_listbox.insert(tk.END, rel)
        if unnamed:
            self.release_listbox.insert(tk.END, "(no release)")

        # Restore or default selection
        items = list(self.release_listbox.get(0, tk.END))
        if current_sel in items:
            idx = items.index(current_sel)
        else:
            idx = 0
        self.release_listbox.selection_set(idx)
        self.release_listbox.activate(idx)

        self._render_dashboard(summaries)

    def _current_release_selection(self) -> str:
        try:
            sel = self.release_listbox.curselection()
            if sel:
                return self.release_listbox.get(sel[0])
        except Exception:
            pass
        return "All"

    def _on_release_select(self, _=None):
        from adapters.database.testresults import fetch_run_summaries
        self._render_dashboard(fetch_run_summaries())

    def _render_dashboard(self, summaries: list):
        sel_label = self._current_release_selection()

        if sel_label == "All":
            filtered = summaries
            self._dash_release_label.configure(text="— All Releases")
        elif sel_label == "(no release)":
            filtered = [s for s in summaries if not s["release"]]
            self._dash_release_label.configure(text="— (no release)")
        else:
            filtered = [s for s in summaries if s["release"] == sel_label]
            self._dash_release_label.configure(text=f"— {sel_label}")

        # Stat cards
        run_count = len(filtered)
        if filtered:
            all_total  = sum(s["total"]  for s in filtered)
            all_errors = sum(s["errors"] for s in filtered)
            all_ok     = all_total - all_errors
            overall_pct = round(all_ok / all_total * 100) if all_total else 0
            pct_text  = f"{overall_pct}%"
            pct_color = FG if overall_pct >= 80 else RED
        else:
            pct_text  = "—"
            pct_color = FG_SEC

        for w in self._dash_cards_row.winfo_children():
            w.destroy()

        _stat_card(self._dash_cards_row, "Runs", str(run_count), FG
                   ).grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        _stat_card(self._dash_cards_row, "Pass Rate", pct_text, pct_color
                   ).grid(row=0, column=1, sticky="nsew")

        # Runs table
        self._dash_tree.delete(*self._dash_tree.get_children())
        for s in filtered:
            tag = "ok" if s["pass_pct"] >= 80 else ("err" if s["errors"] > 0 else "neutral")
            display_name = s["run_name"]
            if sel_label == "All" and s["release"]:
                # Strip release prefix for brevity when showing all
                pass
            self._dash_tree.insert("", tk.END, values=(
                s["date"], display_name,
                s["total"], s["ok"], s["errors"],
                f"{s['pass_pct']}%",
            ), tags=(tag,))
