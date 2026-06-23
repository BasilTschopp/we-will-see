import os
import tkinter as tk
from tkinter import ttk, messagebox

from core.core import NavigationResult
from interfaces.style.style import BG, BG2, FG, RED, FONT
from interfaces.helper.widgets import add_tooltip


class ViewResults:

    def build_sub(self, parent: tk.Frame):
        from interfaces.style.style import SUB_BG, SUB_SEL_BG, SUB_SEL_FG
        self.sub_results = tk.Frame(parent, bg=SUB_BG)

        # Release filter
        self._results_release_var = tk.StringVar(value="All")
        self._results_release_combo = ttk.Combobox(
            self.sub_results, textvariable=self._results_release_var,
            values=["All"], state="readonly")
        self._results_release_combo.pack(fill=tk.X, padx=(10, 4), pady=(6, 2))
        self._results_release_combo.bind(
            "<<ComboboxSelected>>", lambda _: self._refresh_results_list())

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

        self.result_export_btn = tk.Label(header, text="⇩", bg=BG, fg=FG,
                                          font=(FONT, 13), cursor="hand2")
        self.result_export_btn.pack(side=tk.RIGHT, padx=(0, 4), pady=2)
        self.result_export_btn.bind("<Button-1>", lambda _: self._on_export_result())
        add_tooltip(self.result_export_btn, "Export YAML")

        tree_frame = tk.Frame(inner, bg=BG)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.csv_tree = ttk.Treeview(
            tree_frame,
            columns=("time", "status", "ms", "description", "img", "error"),
            show="headings", selectmode="browse")
        self.csv_tree.heading("time",        text="Time")
        self.csv_tree.heading("status",      text="Status")
        self.csv_tree.heading("ms",          text="ms")
        self.csv_tree.heading("description", text="Description")
        self.csv_tree.heading("img",         text="")
        self.csv_tree.heading("error",       text="Error")
        self.csv_tree.column("time",        width=80,  minwidth=60,  stretch=False, anchor="w")
        self.csv_tree.column("status",      width=70,  minwidth=60,  stretch=False, anchor="w")
        self.csv_tree.column("ms",          width=55,  minwidth=40,  stretch=False, anchor="e")
        self.csv_tree.column("description", width=300, minwidth=150, anchor="w")
        self.csv_tree.column("img",         width=24,  minwidth=24,  stretch=False, anchor="center")
        self.csv_tree.column("error",       width=350, minwidth=100, anchor="w")
        self.csv_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._csv_sb = ttk.Scrollbar(tree_frame, orient="vertical",
                                     command=self.csv_tree.yview)
        self._csv_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.csv_tree.configure(yscrollcommand=self._on_tree_scroll)
        self.csv_tree.tag_configure("err",    foreground=RED)
        self.csv_tree.tag_configure("ok",     foreground=FG)
        self.csv_tree.tag_configure("stripe", background=BG)

        self._screenshot_icon  = self._make_screenshot_icon()
        self._screenshot_paths: dict[str, tuple] = {}
        self._img_labels: list[tk.Label] = []
        self.csv_tree.bind("<MouseWheel>",
                           lambda e: self.csv_tree.after(5, self._update_img_labels))

    # ------------------------------------------------------------------
    # Results list
    # ------------------------------------------------------------------

    def _refresh_results_list(self):
        from adapters.database.testresults import list_runs, list_releases

        releases = list_releases()
        self._results_release_combo.configure(values=["All"] + releases)

        sel_release = self._results_release_var.get()
        if sel_release not in ["All"] + releases:
            sel_release = "All"
            self._results_release_var.set("All")

        filtered = list_runs(release="" if sel_release == "All" else sel_release)

        self.results_listbox.delete(0, tk.END)
        for name in filtered:
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

    def _on_export_result(self):
        sel = self.results_listbox.curselection()
        if not sel or len(sel) > 1:
            return
        name = self.results_listbox.get(sel[0])
        from tkinter import filedialog
        import yaml
        from dataclasses import asdict
        from adapters.database.testresults import fetch_results, fetch_release
        results = fetch_results(name)
        release = fetch_release(name)
        _FIELDS = ['description', 'status', 'error_detail']
        sorted_results = sorted(results, key=lambda x: x.timestamp)
        def _to_dict(r):
            raw = asdict(r)
            return {k: raw[k] for k in _FIELDS if raw.get(k)}
        data = [_to_dict(r) for r in sorted_results if r.method != 'wait']
        date = sorted_results[0].timestamp if sorted_results else ""
        safe_name = name.replace(":", "-").replace("/", "-").replace("\\", "-")
        path = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            initialfile=f"{safe_name}.yaml",
            title="Export Result")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            if date:
                f.write(f"date: {date}\n")
            if release:
                f.write(f"release: {release}\n")
            if date or release:
                f.write("\n")
            f.write('\n'.join(
                yaml.dump(item, allow_unicode=True, sort_keys=False, width=float('inf'))
                for item in data
            ))

    def _make_screenshot_icon(self) -> tk.PhotoImage:
        img = tk.PhotoImage(width=14, height=11)
        b = RED
        w = BG2
        img.put(w, to=(1, 1, 13, 10))        # white fill
        img.put(b, to=(0, 0, 14, 1))          # top border
        img.put(b, to=(0, 10, 14, 11))        # bottom border
        img.put(b, to=(0, 0, 1, 11))          # left border
        img.put(b, to=(13, 0, 14, 11))        # right border
        img.put(b, to=(2, 2, 4, 4))           # sun
        img.put(b, to=(3, 7, 4, 8))           # mountain left peak
        img.put(b, to=(2, 8, 5, 9))           # mountain left base
        img.put(b, to=(6, 6, 7, 7))           # mountain right peak
        img.put(b, to=(5, 7, 8, 8))           # mountain right mid
        img.put(b, to=(4, 8, 9, 9))           # mountain right base
        img.put(b, to=(9, 7, 13, 9))          # horizon line right
        return img

    def _on_tree_scroll(self, *args):
        self._csv_sb.set(*args)
        self._update_img_labels()

    def _update_img_labels(self):
        for lbl in self._img_labels:
            lbl.destroy()
        self._img_labels.clear()
        for iid, (path, row_bg) in self._screenshot_paths.items():
            bbox = self.csv_tree.bbox(iid, "img")
            if not bbox:
                continue
            bx, by, bw, bh = bbox
            lbl = tk.Label(self.csv_tree, image=self._screenshot_icon,
                           bg=row_bg, cursor="hand2",
                           borderwidth=0, padx=0, pady=0)
            lbl.place(x=bx + (bw - 14) // 2, y=by + (bh - 11) // 2)
            lbl.bind("<Button-1>", lambda e, p=path: os.startfile(p))
            self._img_labels.append(lbl)

    def _load_results_into_tree(self, results: list[NavigationResult]):
        for lbl in self._img_labels:
            lbl.destroy()
        self._img_labels.clear()
        self.csv_tree.delete(*self.csv_tree.get_children())
        self._screenshot_paths.clear()
        for idx, r in enumerate(sorted(results, key=lambda x: x.timestamp)):
            time_str = r.timestamp.split(" ", 1)[1] if " " in r.timestamp else r.timestamp
            status   = "Error" if r.status == "ERROR" else "OK"
            error    = r.error_detail.replace("\n", " ").replace("\r", "")
            title    = (r.page_title or "").strip()
            desc_raw = r.description.replace("\n", " — ").replace("\r", "")
            desc     = f"{desc_raw} — {title}" if title else desc_raw
            ms       = str(r.load_time_ms) if r.load_time_ms else ""
            color_tag = "err" if r.status == "ERROR" else "ok"
            tags      = (color_tag, "stripe") if idx % 2 == 1 else (color_tag,)
            row_bg    = BG if idx % 2 == 1 else BG2
            iid = self.csv_tree.insert(
                "", tk.END,
                values=(time_str, status, ms, desc, "", error),
                tags=tags)
            if r.screenshot_path and os.path.isfile(r.screenshot_path):
                self._screenshot_paths[iid] = (r.screenshot_path, row_bg)
        self.csv_tree.after(10, self._update_img_labels)
