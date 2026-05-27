import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from interfaces.style import BG, BG2, FG, FG_SEC, ACCENT, RED, BORDER, FONT, MONO
from interfaces.helper import add_tooltip, get_categories


class ViewTesting:

    def build_sub(self, parent: tk.Frame):
        from interfaces.style import SUB_BG, SUB_SEL_BG, SUB_SEL_FG
        self.sub_testing = tk.Frame(parent, bg=SUB_BG)

        self._filter_cat_var = tk.StringVar(value="All")
        self._filter_cat_combo = ttk.Combobox(
            self.sub_testing, textvariable=self._filter_cat_var,
            values=["All"] + get_categories(), state="readonly")
        self._filter_cat_combo.pack(fill=tk.X, padx=(10, 4), pady=(6, 2))
        self._filter_cat_combo.bind("<<ComboboxSelected>>",
                                    lambda _: self._refresh_tc_list())

        self.tc_listbox = tk.Listbox(
            self.sub_testing, bg=SUB_BG, fg=FG,
            selectbackground=SUB_SEL_BG, selectforeground=SUB_SEL_FG,
            font=(FONT, 11), borderwidth=0, highlightthickness=0,
            activestyle="none", relief="flat", exportselection=False,
            selectmode="extended")
        self.tc_listbox.pack(fill=tk.BOTH, expand=True, padx=(10, 4), pady=4)
        self.tc_listbox.bind("<<ListboxSelect>>", self._on_tc_select)
        self.tc_listbox.bind("<Button-3>", self._on_tc_rightclick)

        bar = tk.Frame(self.sub_testing, bg=SUB_BG)
        bar.pack(fill=tk.X, padx=(10, 4), pady=(0, 6))

        tk.Label(bar, text="+", bg=SUB_BG, fg=FG, font=(FONT, 14, "bold"),
                 cursor="hand2").pack(side=tk.LEFT, padx=(0, 6))
        bar.winfo_children()[-1].bind("<Button-1>", lambda _: self._on_create())

        tk.Label(bar, text="−", bg=SUB_BG, fg=FG, font=(FONT, 14, "bold"),
                 cursor="hand2").pack(side=tk.LEFT)
        bar.winfo_children()[-1].bind("<Button-1>", lambda _: self._on_delete())

        self.tc_menu = tk.Menu(self.root, tearoff=0,
                               font=(FONT, 10), bg=BG2, fg=FG,
                               activebackground=ACCENT,
                               activeforeground="#ffffff")
        self.tc_menu.add_command(label="Create",          command=self._on_create)
        self.tc_menu.add_command(label="Rename",          command=self._on_rename)
        self.tc_menu.add_command(label="Change Category", command=self._on_change_category)
        self.tc_menu.add_command(label="Delete",          command=self._on_delete)

    def build_content(self, parent: tk.Frame):
        self.content_testing = tk.Frame(parent, bg=BG)

        editor_frame = tk.Frame(self.content_testing, bg=BG)
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=(8, 12), pady=(8, 8))

        header = tk.Frame(editor_frame, bg=BG)
        header.pack(fill=tk.X, pady=(0, 4))

        self.editor_title = tk.Label(
            header, text="No testcase selected", bg=BG,
            fg=FG, font=(FONT, 10, "bold"), anchor="w", padx=10, pady=8)
        self.editor_title.pack(side=tk.LEFT, fill=tk.X, expand=True)

        icon_frame = tk.Frame(header, bg=BG)
        icon_frame.pack(side=tk.RIGHT)

        self.run_hl_btn = tk.Label(icon_frame, text="⚡", bg=BG, fg=ACCENT,
                                   font=(FONT, 16), cursor="hand2")
        self.run_hl_btn.pack(side=tk.LEFT, padx=(0, 2))
        self.run_hl_btn.bind("<Button-1>",
                             lambda _: self._on_run_test(headless=True))

        self.run_btn = tk.Label(icon_frame, text="▶", bg=BG, fg=ACCENT,
                                font=(FONT, 14), cursor="hand2")
        self.run_btn.pack(side=tk.LEFT, padx=(0, 2))
        self.run_btn.bind("<Button-1>",
                          lambda _: self._on_run_test(headless=False))

        self.stop_btn = tk.Label(icon_frame, text="■", bg=BG, fg=BORDER,
                                 font=(FONT, 14), cursor="hand2")
        self.stop_btn.pack(side=tk.LEFT, padx=(4, 0))
        self.stop_btn.bind("<Button-1>", lambda _: self._on_stop())

        add_tooltip(self.run_hl_btn, "Run headless")
        add_tooltip(self.run_btn,    "Run (visible)")
        add_tooltip(self.stop_btn,   "Stop")

        txt_frame = tk.Frame(editor_frame, bg=BORDER)
        txt_frame.pack(fill=tk.BOTH, expand=True)

        self.editor = tk.Text(
            txt_frame, bg=BG2, fg=FG, insertbackground=FG,
            font=(MONO, 10), relief="flat", borderwidth=0,
            highlightthickness=0, selectbackground=BORDER,
            selectforeground=FG, padx=10, pady=8,
            undo=True, wrap=tk.NONE)
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.editor.bind("<FocusOut>", self._on_editor_focusout)

        editor_sb = ttk.Scrollbar(txt_frame, orient="vertical",
                                  command=self.editor.yview)
        editor_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.editor.configure(yscrollcommand=editor_sb.set)

        footer = tk.Frame(editor_frame, bg=BG)
        footer.pack(fill=tk.X, pady=(4, 0))

        self._automated_var = tk.BooleanVar()
        tk.Checkbutton(
            footer, text="Automated", variable=self._automated_var,
            bg=BG, fg=FG, selectcolor=BG,
            activebackground=BG, activeforeground=ACCENT,
            font=(FONT, 9), command=self._on_automated_toggle
        ).pack(side=tk.LEFT, padx=(4, 0))

        self.save_btn = tk.Label(footer, text="💾", bg=BG, fg=FG,
                                 font=(FONT, 14), cursor="hand2")
        self.save_btn.pack(side=tk.RIGHT)
        self.save_btn.bind("<Button-1>", lambda _: self._on_save())
        add_tooltip(self.save_btn, "Save")

    # ------------------------------------------------------------------
    # Testcase list
    # ------------------------------------------------------------------

    def _refresh_tc_list(self):
        from adapters.database.testcases import list_testcases
        filter_cat = self._filter_cat_var.get()
        self.tc_listbox.delete(0, tk.END)
        for name, cat in list_testcases():
            if filter_cat == "All" or cat == filter_cat:
                self.tc_listbox.insert(tk.END, name)
        if self.tc_listbox.size() > 0:
            self.tc_listbox.selection_set(0)
            self.tc_listbox.activate(0)
            self._on_tc_select()

    def _on_tc_select(self, _=None):
        sel = self.tc_listbox.curselection()
        if not sel:
            return
        self._on_editor_focusout()
        name = self.tc_listbox.get(sel[0])
        self._load_into_editor(name)

    def _on_tc_rightclick(self, event):
        idx = self.tc_listbox.nearest(event.y)
        if idx >= 0 and idx not in self.tc_listbox.curselection():
            self.tc_listbox.selection_clear(0, tk.END)
            self.tc_listbox.selection_set(idx)
            self.tc_listbox.activate(idx)
        multi = len(self.tc_listbox.curselection()) > 1
        self.tc_menu.entryconfigure("Rename",          state="disabled" if multi else "normal")
        self.tc_menu.entryconfigure("Change Category", state="disabled" if multi else "normal")
        try:
            self.tc_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.tc_menu.grab_release()

    # ------------------------------------------------------------------
    # Testcase CRUD
    # ------------------------------------------------------------------

    def _on_create(self):
        name = simpledialog.askstring(
            "New testcase", "Name:", parent=self.root)
        if not name:
            return
        name = name.strip().replace(" ", "_")
        from adapters.database.testcases import list_testcases, upsert_testcase
        if name in [n for n, _ in list_testcases()]:
            messagebox.showwarning("", f"'{name}' already exists.")
            return
        cat = self._filter_cat_var.get()
        upsert_testcase(name, "", "" if cat == "All" else cat)
        self._refresh_tc_list()
        self._load_into_editor(name)

    def _on_rename(self):
        sel = self.tc_listbox.curselection()
        if not sel:
            messagebox.showinfo("", "Please select a testcase.")
            return
        old_name = self.tc_listbox.get(sel[0])
        new_name = simpledialog.askstring(
            "Rename", f"New name for '{old_name}':",
            initialvalue=old_name, parent=self.root)
        if not new_name or new_name == old_name:
            return
        new_name = new_name.strip().replace(" ", "_")
        from adapters.database.testcases import list_testcases, rename_testcase
        if new_name in [n for n, _ in list_testcases()]:
            messagebox.showwarning("", f"'{new_name}' already exists.")
            return
        rename_testcase(old_name, new_name)
        if self._current_tc_name == old_name:
            self._current_tc_name = new_name
        self._refresh_tc_list()
        self.editor_title.configure(text=new_name, fg=FG)

    def _on_change_category(self):
        sel = self.tc_listbox.curselection()
        if not sel:
            messagebox.showinfo("", "Please select a testcase.")
            return
        name = self.tc_listbox.get(sel[0])
        categories = get_categories()
        if not categories:
            messagebox.showinfo("", "No categories defined in BUGULA_CATEGORIES.")
            return
        from adapters.database.testcases import fetch_testcase_yaml, update_category
        _, current_cat = fetch_testcase_yaml(name)
        dialog = tk.Toplevel(self.root)
        dialog.title("Change Category")
        dialog.resizable(False, False)
        dialog.grab_set()

        tk.Label(dialog, text=f"Category for '{name}':",
                 font=(FONT, 10)).pack(anchor="w", padx=16, pady=(12, 4))

        cat_var = tk.StringVar(value=current_cat if current_cat in categories else categories[0])
        ttk.Combobox(dialog, textvariable=cat_var,
                     values=categories, state="readonly", width=30).pack(padx=16, pady=(0, 8))

        def _apply():
            update_category(name, cat_var.get())
            self._refresh_tc_list()
            dialog.destroy()

        tk.Button(dialog, text="OK", command=_apply,
                  font=(FONT, 10), padx=12).pack(pady=(4, 12))
        dialog.bind("<Return>", lambda _: _apply())

    def _on_delete(self):
        sel = self.tc_listbox.curselection()
        if not sel:
            messagebox.showinfo("", "Please select a testcase.")
            return
        names = [self.tc_listbox.get(i) for i in sel]
        msg = (f"Delete '{names[0]}'?" if len(names) == 1
               else f"Delete {len(names)} testcases?\n" + "\n".join(f"  • {n}" for n in names))
        if not messagebox.askyesno("Delete", msg):
            return
        from adapters.database.testcases import delete_testcase
        for name in names:
            delete_testcase(name)
            if self._current_tc_name == name:
                self.editor.delete("1.0", tk.END)
                self._current_tc_name = ""
                self.editor_title.configure(text="No testcase selected", fg=FG_SEC)
        self._refresh_tc_list()

    # ------------------------------------------------------------------
    # Editor
    # ------------------------------------------------------------------

    def _load_into_editor(self, name: str):
        from adapters.database.testcases import fetch_testcase_yaml, fetch_automated
        yaml_text, _ = fetch_testcase_yaml(name)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", yaml_text)
        self.editor.edit_modified(False)
        self._current_tc_name = name
        self.editor_title.configure(text=name, fg=FG)
        self._automated_var.set(fetch_automated(name))

    def _on_automated_toggle(self):
        if not self._current_tc_name:
            return
        from adapters.database.testcases import update_automated
        update_automated(self._current_tc_name, self._automated_var.get())

    def _on_save(self):
        if not self._current_tc_name:
            return
        content = self.editor.get("1.0", tk.END).rstrip()
        from adapters.database.testcases import fetch_testcase_yaml, upsert_testcase
        _, category = fetch_testcase_yaml(self._current_tc_name)
        upsert_testcase(self._current_tc_name, content, category)
        self.save_btn.configure(fg=ACCENT)
        self.root.after(800, lambda: self.save_btn.configure(fg=FG))

    def _on_editor_focusout(self, _=None):
        if not self._current_tc_name:
            return
        try:
            content = self.editor.get("1.0", tk.END).rstrip()
            from adapters.database.testcases import fetch_testcase_yaml, upsert_testcase
            old_yaml, category = fetch_testcase_yaml(self._current_tc_name)
            if old_yaml.rstrip() != content:
                upsert_testcase(self._current_tc_name, content, category)
        except Exception:
            pass



    # ------------------------------------------------------------------
    # Test run
    # ------------------------------------------------------------------

    def _on_run_test(self, headless: bool = True):
        import threading
        from usecases.testcase_runner import run_test
        if self.running:
            return
        self._on_editor_focusout()
        sel = self.tc_listbox.curselection()
        if not sel:
            messagebox.showinfo("", "Please select testcases.\n"
                                   "(Multi-select with Ctrl+Click)")
            return
        names = [self.tc_listbox.get(i) for i in sel]
        self._set_running(True)
        threading.Thread(target=run_test,
                         args=(self, names, headless), daemon=True).start()

    def _on_stop(self):
        from adapters.browser.driver import quit_browser
        self.running = False
        quit_browser(self.driver)
        self.driver = None

    def _set_running(self, running: bool):
        self.running = running
        if running:
            self.stop_btn.configure(fg=RED)
            self.run_hl_btn.configure(fg=BORDER)
            self.run_btn.configure(fg=BORDER)
        else:
            self.stop_btn.configure(fg=BORDER)
            self.run_hl_btn.configure(fg=ACCENT)
            self.run_btn.configure(fg=ACCENT)


