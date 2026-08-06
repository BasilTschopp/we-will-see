import tkinter as tk
from tkinter import ttk

from interfaces.style.style import BG, BG2, FG, FONT, RED


class ViewPerformance:

    def build_sub(self, parent: tk.Frame):
        from interfaces.style.style import SUB_BG
        self.sub_performance = tk.Frame(parent, bg=SUB_BG)

        self.performance_listbox = ttk.Treeview(
            self.sub_performance, style="SubList.Treeview",
            columns=("name",), show="", selectmode="browse")
        self.performance_listbox.column("name", anchor="w", stretch=True)
        self.performance_listbox.pack(fill=tk.BOTH, expand=True,
                                      padx=(10, 4), pady=4)
        self.performance_listbox.bind("<<TreeviewSelect>>", self._on_performance_select)

    def build_content(self, parent: tk.Frame):
        self.content_performance = tk.Frame(parent, bg=BG)

        inner = tk.Frame(self.content_performance, bg=BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=(8, 12), pady=(8, 8))

        header = tk.Frame(inner, bg=BG)
        header.pack(fill=tk.X, pady=(0, 4))

        self.performance_title = tk.Label(
            header, text="No testcase selected", bg=BG,
            fg=FG, font=(FONT, 10, "bold"), anchor="w", padx=10, pady=8)
        self.performance_title.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tree_frame = tk.Frame(inner, bg=BG)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.performance_tree = ttk.Treeview(
            tree_frame, columns=("release", "duration", "vs_prev", "vs_first"),
            show="headings", selectmode="browse")
        self.performance_tree.heading("release",  text="Release")
        self.performance_tree.heading("duration", text="Total Duration")
        self.performance_tree.heading("vs_prev",  text="Previous")
        self.performance_tree.heading("vs_first", text="First Release")
        self.performance_tree.column("release",  width=160, minwidth=100, anchor="w")
        self.performance_tree.column("duration", width=100, minwidth=80, stretch=False, anchor="e")
        self.performance_tree.column("vs_prev",  width=110, minwidth=80, stretch=False, anchor="e")
        self.performance_tree.column("vs_first", width=130, minwidth=80, stretch=False, anchor="e")
        self.performance_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(tree_frame, orient="vertical",
                           command=self.performance_tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.performance_tree.configure(yscrollcommand=sb.set)
        self.performance_tree.tag_configure("stripe", background=BG2)
        self.performance_tree.tag_configure("alert", foreground=RED)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _refresh_performance_list(self):
        from adapters.database.testresults import list_testcase_keys

        sel = self.performance_listbox.selection()
        selected_key = sel[0] if sel else None

        keys = list_testcase_keys()
        self.performance_listbox.delete(*self.performance_listbox.get_children())
        for key in keys:
            self.performance_listbox.insert("", tk.END, iid=key, values=(key,))

        children = self.performance_listbox.get_children()
        if not children:
            self.performance_title.configure(text="No testcase selected")
            self.performance_tree.delete(*self.performance_tree.get_children())
            return

        target = selected_key if selected_key in children else children[0]
        self.performance_listbox.selection_set(target)
        self.performance_listbox.focus(target)
        self._on_performance_select()

    def _on_performance_select(self, _=None):
        sel = self.performance_listbox.selection()
        if not sel:
            return
        tc_key = sel[0]
        self.performance_title.configure(text=tc_key)

        from adapters.database.testresults import fetch_performance
        from adapters.database.settings import (
            get_performance_threshold_prev, get_performance_threshold_first,
        )
        threshold_prev  = get_performance_threshold_prev()
        threshold_first = get_performance_threshold_first()
        data = fetch_performance(tc_key)

        self.performance_tree.delete(*self.performance_tree.get_children())
        for idx, (release, duration, pct_prev, pct_first) in enumerate(data):
            alert = (
                (threshold_prev > 0 and pct_prev is not None and pct_prev >= threshold_prev)
                or (threshold_first > 0 and pct_first is not None and pct_first >= threshold_first)
            )
            tags = []
            if idx % 2 == 1:
                tags.append("stripe")
            if alert:
                tags.append("alert")
            self.performance_tree.insert(
                "", tk.END,
                values=(release, _format_duration(duration),
                       _format_pct(pct_prev), _format_pct(pct_first)),
                tags=tuple(tags))


def _format_duration(seconds: float) -> str:
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _format_pct(pct: float | None) -> str:
    if pct is None:
        return "–"
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"
