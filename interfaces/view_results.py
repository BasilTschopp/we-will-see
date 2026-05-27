import tkinter as tk
from tkinter import ttk, messagebox

from models.models import NavigationResult
from interfaces.style import BG, FG, RED, FONT


class ViewResults:

    def build_sub(self, parent: tk.Frame):
        from interfaces.style import SUB_BG, SUB_SEL_BG, SUB_SEL_FG
        self.sub_results = tk.Frame(parent, bg=SUB_BG)

        self.results_listbox = tk.Listbox(
            self.sub_results, bg=SUB_BG, fg=FG,
            selectbackground=SUB_SEL_BG, selectforeground=SUB_SEL_FG,
            font=(FONT, 11), borderwidth=0, highlightthickness=0,
            activestyle="none", relief="flat", exportselection=False,
            selectmode=tk.EXTENDED)
        self.results_listbox.pack(fill=tk.BOTH, expand=True,
                                  padx=(10, 4), pady=4)
        self.results_listbox.bind("<<ListboxSelect>>", self._on_result_select)
        self.results_listbox.bind("<Delete>", lambda _: self._on_delete_result())
        self.results_listbox.bind("<Button-3>", self._on_results_rightclick)

        self._results_context_menu = tk.Menu(
            self.results_listbox, tearoff=0,
            bg=SUB_BG, fg=FG, activebackground=SUB_SEL_BG,
            activeforeground=SUB_SEL_FG, borderwidth=0,
            font=(FONT, 10))
        self._results_context_menu.add_command(
            label="Delete", command=self._on_delete_result)

        bar = tk.Frame(self.sub_results, bg=SUB_BG)
        bar.pack(fill=tk.X, padx=(10, 4), pady=(0, 6))
        tk.Label(bar, text="−", bg=SUB_BG, fg=FG, font=(FONT, 14, "bold"),
                 cursor="hand2").pack(side=tk.LEFT)
        bar.winfo_children()[-1].bind("<Button-1>",
                                      lambda _: self._on_delete_result())

    def build_content(self, parent: tk.Frame):
        self.content_results = tk.Frame(parent, bg=BG)

        inner = tk.Frame(self.content_results, bg=BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=(8, 12), pady=(8, 8))

        header = tk.Frame(inner, bg=BG)
        header.pack(fill=tk.X, pady=(0, 4))

        self.result_title = tk.Label(
            header, text="No result selected", bg=BG,
            fg=FG, font=(FONT, 10, "bold"), anchor="w", padx=10, pady=8)
        self.result_title.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tree_frame = tk.Frame(inner, bg=BG)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.csv_tree = ttk.Treeview(
            tree_frame,
            columns=("time", "status", "ms", "description", "error"),
            show="headings", selectmode="browse")
        self.csv_tree.heading("time",        text="Time")
        self.csv_tree.heading("status",      text="Status")
        self.csv_tree.heading("ms",          text="ms")
        self.csv_tree.heading("description", text="Description")
        self.csv_tree.heading("error",       text="Error")
        self.csv_tree.column("time",        width=80,  minwidth=60,  stretch=False, anchor="w")
        self.csv_tree.column("status",      width=70,  minwidth=60,  stretch=False, anchor="w")
        self.csv_tree.column("ms",          width=55,  minwidth=40,  stretch=False, anchor="e")
        self.csv_tree.column("description", width=300, minwidth=150, anchor="w")
        self.csv_tree.column("error",       width=350, minwidth=100, anchor="w")
        self.csv_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        csv_sb = ttk.Scrollbar(tree_frame, orient="vertical",
                               command=self.csv_tree.yview)
        csv_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.csv_tree.configure(yscrollcommand=csv_sb.set)
        self.csv_tree.tag_configure("err",    foreground=RED)
        self.csv_tree.tag_configure("ok",     foreground=FG)
        self.csv_tree.tag_configure("stripe", background=BG)

    # ------------------------------------------------------------------
    # Results list
    # ------------------------------------------------------------------

    def _refresh_results_list(self):
        from adapters.database.testresults import list_runs
        self.results_listbox.delete(0, tk.END)
        for name in list_runs():
            self.results_listbox.insert(tk.END, name)
        if self.results_listbox.size() > 0:
            self.results_listbox.selection_set(0)
            self.results_listbox.activate(0)
            self._on_result_select()

    def _on_results_rightclick(self, event):
        idx = self.results_listbox.nearest(event.y)
        if idx < 0:
            return
        if idx not in self.results_listbox.curselection():
            self.results_listbox.selection_clear(0, tk.END)
            self.results_listbox.selection_set(idx)
            self.results_listbox.activate(idx)
            self._on_result_select()
        self._results_context_menu.tk_popup(event.x_root, event.y_root)

    def _on_result_select(self, _=None):
        sel = self.results_listbox.curselection()
        if not sel:
            return
        if len(sel) > 1:
            self.result_title.configure(text=f"{len(sel)} results selected", fg=FG)
            self.csv_tree.delete(*self.csv_tree.get_children())
            return
        name = self.results_listbox.get(sel[0])
        self.result_title.configure(text=name, fg=FG)
        from adapters.database.testresults import fetch_results
        self._load_results_into_tree(fetch_results(name))

    def _on_delete_result(self):
        sel = self.results_listbox.curselection()
        if not sel:
            messagebox.showinfo("", "Please select a result.")
            return
        names = [self.results_listbox.get(i) for i in sel]
        if len(names) == 1:
            prompt = f"Delete '{names[0]}'?"
        else:
            prompt = f"Delete {len(names)} entries?"
        if not messagebox.askyesno("Delete", prompt):
            return
        from adapters.database.testresults import delete_run
        for name in names:
            delete_run(name)
        self.csv_tree.delete(*self.csv_tree.get_children())
        self.result_title.configure(text="No result selected", fg=FG)
        self._refresh_results_list()

    # ------------------------------------------------------------------
    # Tree
    # ------------------------------------------------------------------

    def _load_results_into_tree(self, results: list[NavigationResult]):
        self.csv_tree.delete(*self.csv_tree.get_children())
        for idx, r in enumerate(sorted(results, key=lambda x: x.timestamp)):
            time_str = r.timestamp.split(" ", 1)[1] if " " in r.timestamp else r.timestamp
            status   = "Error" if r.status == "FEHLER" else "OK"
            error    = r.error_detail.replace("\n", " ").replace("\r", "")
            desc     = r.description.replace("\n", " — ").replace("\r", "")
            ms       = str(r.load_time_ms) if r.load_time_ms else ""
            color_tag = "err" if r.status == "FEHLER" else "ok"
            tags = (color_tag, "stripe") if idx % 2 == 1 else (color_tag,)
            self.csv_tree.insert("", tk.END,
                                 values=(time_str, status, ms, desc, error),
                                 tags=tags)



