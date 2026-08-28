import tkinter as tk
from tkinter import ttk, messagebox

from interfaces.style.style import BG, BG2, FG, FG_SEC, ACCENT, BORDER, FONT
from interfaces.helper.utils import get_categories


class ViewDocumentation:

    def build_sub(self, parent: tk.Frame):
        from interfaces.style.style import SUB_BG
        self.sub_documentation = tk.Frame(parent, bg=SUB_BG)

        self._doc_filter_cat_var = tk.StringVar(value="All")
        self._doc_filter_cat_combo = ttk.Combobox(
            self.sub_documentation, textvariable=self._doc_filter_cat_var,
            values=["All"] + get_categories(), state="readonly")
        self._doc_filter_cat_combo.pack(fill=tk.X, padx=(10, 4), pady=(6, 2))
        self._doc_filter_cat_combo.bind("<<ComboboxSelected>>",
                                        lambda _: self._refresh_doc_tc_list())

        self.doc_tc_listbox = ttk.Treeview(
            self.sub_documentation, style="SubList.Treeview",
            columns=("name",), show="", selectmode="extended")
        self.doc_tc_listbox.column("name", anchor="w", stretch=True)
        self.doc_tc_listbox.pack(fill=tk.BOTH, expand=True, padx=(10, 4), pady=4)

    def build_content(self, parent: tk.Frame):
        self.content_documentation = tk.Frame(parent, bg=BG)

        outer = tk.Frame(self.content_documentation, bg=BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=32, pady=24)

        tk.Label(outer, text="User Documentation", bg=BG, fg=FG,
                 font=(FONT, 13, "bold"), anchor="w").pack(fill=tk.X, pady=(0, 4))
        tk.Frame(outer, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 16))

        tk.Label(outer,
                 text="Runs the selected testcase(s) in a visible browser and turns "
                      "each step into a page of a Word document, for handing to end users.",
                 bg=BG, fg=FG_SEC, font=(FONT, 10), anchor="w",
                 wraplength=480, justify="left").pack(anchor="w", pady=(0, 16))

        self._doc_opt_screenshot = tk.BooleanVar(value=True)
        tk.Checkbutton(
            outer, text="Screenshot for every step", variable=self._doc_opt_screenshot,
            bg=BG, fg=FG, selectcolor=BG2, activebackground=BG,
            font=(FONT, 10), anchor="w").pack(anchor="w", pady=(0, 4))

        self._doc_opt_title = tk.BooleanVar(value=True)
        tk.Checkbutton(
            outer, text="Description as title", variable=self._doc_opt_title,
            bg=BG, fg=FG, selectcolor=BG2, activebackground=BG,
            font=(FONT, 10), anchor="w").pack(anchor="w", pady=(0, 4))

        self._doc_opt_caption = tk.BooleanVar(value=False)
        tk.Checkbutton(
            outer, text="Description as caption (below the screenshot)",
            variable=self._doc_opt_caption,
            bg=BG, fg=FG, selectcolor=BG2, activebackground=BG,
            font=(FONT, 10), anchor="w").pack(anchor="w", pady=(0, 16))

        self.doc_generate_btn = tk.Label(
            outer, text="Generate", bg=ACCENT, fg="#ffffff",
            font=(FONT, 11, "bold"), cursor="hand2",
            padx=16, pady=8, relief="flat")
        self.doc_generate_btn.pack(anchor="w")
        self.doc_generate_btn.bind("<Button-1>", lambda _: self._on_generate_userguide())

        self._doc_status_var = tk.StringVar(value="")
        tk.Label(outer, textvariable=self._doc_status_var, bg=BG, fg=FG_SEC,
                 font=(FONT, 9), anchor="w").pack(fill=tk.X, pady=(10, 0))

    # ------------------------------------------------------------------
    # Testcase list
    # ------------------------------------------------------------------

    def _refresh_doc_tc_list(self):
        from adapters.database.testcases import list_testcases
        filter_cat = self._doc_filter_cat_var.get()
        self.doc_tc_listbox.delete(*self.doc_tc_listbox.get_children())
        names = sorted(
            (name for name, cat in list_testcases()
             if filter_cat == "All" or cat == filter_cat),
            key=str.casefold)
        for name in names:
            self.doc_tc_listbox.insert("", tk.END, iid=name, values=(name,))

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    def _on_generate_userguide(self):
        import threading
        from usecases.userguide_generator import generate_user_guide

        if self.running:
            messagebox.showwarning("", "Already running.")
            return
        sel = self.doc_tc_listbox.selection()
        if not sel:
            messagebox.showinfo("", "Please select one or more testcases.\n"
                                   "(Multi-select with Ctrl+Click)")
            return
        names = list(sel)
        options = {
            "screenshot": self._doc_opt_screenshot.get(),
            "title":      self._doc_opt_title.get(),
            "caption":    self._doc_opt_caption.get(),
        }

        self._set_running(True)
        self._doc_status_var.set("Generating…")

        def _run():
            try:
                path = generate_user_guide(self, names, options)
                self.root.after(0, self._on_userguide_done, path, "")
            except Exception as e:
                self.root.after(0, self._on_userguide_done, "", str(e))

        threading.Thread(target=_run, daemon=True).start()

    def _on_userguide_done(self, path: str, error: str):
        self._set_running(False)
        self._doc_status_var.set("")
        if error:
            messagebox.showerror("Documentation Error", error)
            return
        self._show_report_popup(path, title="Documentation created")
