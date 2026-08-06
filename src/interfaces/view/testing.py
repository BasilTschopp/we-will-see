import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from interfaces.style.style import BG, BG2, FG, FG_SEC, ACCENT, BLUE, RED, BORDER, FONT, MONO
from interfaces.helper.widgets import add_tooltip
from interfaces.helper.utils import get_categories


class ViewTesting:

    def build_sub(self, parent: tk.Frame):
        from interfaces.style.style import SUB_BG, SUB_SEL_BG, SUB_SEL_FG
        self.sub_testing = tk.Frame(parent, bg=SUB_BG)

        self._filter_cat_var = tk.StringVar(value="All")
        self._filter_cat_combo = ttk.Combobox(
            self.sub_testing, textvariable=self._filter_cat_var,
            values=["All"] + get_categories(), state="readonly")
        self._filter_cat_combo.pack(fill=tk.X, padx=(10, 4), pady=(6, 2))
        self._filter_cat_combo.bind("<<ComboboxSelected>>",
                                    lambda _: self._refresh_tc_list())

        self.tc_listbox = ttk.Treeview(
            self.sub_testing, style="SubList.Treeview",
            columns=("name",), show="", selectmode="extended")
        self.tc_listbox.column("name", anchor="w", stretch=True)
        self.tc_listbox.pack(fill=tk.BOTH, expand=True, padx=(10, 4), pady=4)
        self.tc_listbox.bind("<<TreeviewSelect>>", self._on_tc_select)
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
        self.editor.tag_configure('search_match',   background='#4a4a10')
        self.editor.tag_configure('search_current', background=ACCENT, foreground='#ffffff')
        self.editor.bind('<Control-f>', lambda e: self._search_show() or 'break')

        self._search_frame = tk.Frame(editor_frame, bg=BG2)
        self._search_var   = tk.StringVar()
        self._search_var.trace_add('write', lambda *_: self._search_update())
        self._search_entry = tk.Entry(
            self._search_frame, textvariable=self._search_var,
            bg=BG, fg=FG, insertbackground=FG, relief='flat',
            borderwidth=0, highlightthickness=1,
            highlightcolor=ACCENT, highlightbackground=BORDER,
            font=(MONO, 10))
        self._search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 4), pady=4)
        self._search_entry.bind('<Return>',       lambda _: self._search_next())
        self._search_entry.bind('<Shift-Return>', lambda _: self._search_prev())
        self._search_entry.bind('<Escape>',       lambda _: self._search_hide())
        self._search_count_label = tk.Label(
            self._search_frame, text='', bg=BG2, fg=FG_SEC, font=(FONT, 9), width=8)
        self._search_count_label.pack(side=tk.LEFT)
        for sym, cmd in [('↑', self._search_prev), ('↓', self._search_next)]:
            lbl = tk.Label(self._search_frame, text=sym, bg=BG2, fg=FG,
                           font=(FONT, 11), cursor='hand2')
            lbl.pack(side=tk.LEFT, padx=2)
            lbl.bind('<Button-1>', lambda _, c=cmd: c())
        close_lbl = tk.Label(self._search_frame, text='✕', bg=BG2, fg=FG_SEC,
                             font=(FONT, 10), cursor='hand2', padx=8)
        close_lbl.pack(side=tk.RIGHT)
        close_lbl.bind('<Button-1>', lambda _: self._search_hide())

        footer = tk.Frame(editor_frame, bg=BG)
        self._footer_frame = footer
        footer.pack(fill=tk.X, pady=(4, 0))

        self._search_matches: list = []
        self._search_idx:     int  = -1

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _search_show(self):
        if not self._search_frame.winfo_manager():
            self._search_frame.pack(fill=tk.X, before=self._footer_frame)
        self._search_entry.focus_set()
        self._search_entry.select_range(0, tk.END)

    def _search_hide(self):
        self._search_frame.pack_forget()
        self.editor.tag_remove('search_match',   '1.0', tk.END)
        self.editor.tag_remove('search_current', '1.0', tk.END)
        self._search_matches = []
        self._search_idx     = -1
        self._search_count_label.configure(text='')
        self.editor.focus_set()

    def _search_update(self):
        self.editor.tag_remove('search_match',   '1.0', tk.END)
        self.editor.tag_remove('search_current', '1.0', tk.END)
        term = self._search_var.get()
        if not term:
            self._search_matches = []
            self._search_idx     = -1
            self._search_count_label.configure(text='')
            return
        matches = []
        start   = '1.0'
        length  = len(term)
        while True:
            pos = self.editor.search(term, start, stopindex=tk.END, nocase=True)
            if not pos:
                break
            end = f'{pos}+{length}c'
            matches.append((pos, end))
            self.editor.tag_add('search_match', pos, end)
            start = end
        self._search_matches = matches
        if not matches:
            self._search_count_label.configure(text='no match')
            self._search_idx = -1
        else:
            self._search_idx = 0
            self._search_highlight_current()

    def _search_highlight_current(self):
        self.editor.tag_remove('search_current', '1.0', tk.END)
        if not self._search_matches or self._search_idx < 0:
            return
        pos, end = self._search_matches[self._search_idx]
        self.editor.tag_add('search_current', pos, end)
        self.editor.see(pos)
        self._search_count_label.configure(
            text=f'{self._search_idx + 1}/{len(self._search_matches)}')

    def _search_next(self):
        if not self._search_matches:
            return
        self._search_idx = (self._search_idx + 1) % len(self._search_matches)
        self._search_highlight_current()

    def _search_prev(self):
        if not self._search_matches:
            return
        self._search_idx = (self._search_idx - 1) % len(self._search_matches)
        self._search_highlight_current()

    # ------------------------------------------------------------------
    # Testcase list
    # ------------------------------------------------------------------

    def _refresh_tc_list(self):
        from adapters.database.testcases import list_testcases
        filter_cat = self._filter_cat_var.get()
        self.tc_listbox.delete(*self.tc_listbox.get_children())
        names = sorted(
            (name for name, cat in list_testcases()
             if filter_cat == "All" or cat == filter_cat),
            key=str.casefold)
        for name in names:
            self.tc_listbox.insert("", tk.END, iid=name, values=(name,))
        children = self.tc_listbox.get_children()
        if children:
            self.tc_listbox.selection_set(children[0])
            self.tc_listbox.focus(children[0])
            self._on_tc_select()

    def _on_tc_select(self, _=None):
        sel = self.tc_listbox.selection()
        if not sel:
            return
        self._on_editor_focusout()
        name = sel[0]
        self._load_into_editor(name)

    def _on_tc_rightclick(self, event):
        iid = self.tc_listbox.identify_row(event.y)
        if iid and iid not in self.tc_listbox.selection():
            self.tc_listbox.selection_set(iid)
            self.tc_listbox.focus(iid)
        multi = len(self.tc_listbox.selection()) > 1
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
        sel = self.tc_listbox.selection()
        if not sel:
            messagebox.showinfo("", "Please select a testcase.")
            return
        old_name = sel[0]
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
        sel = self.tc_listbox.selection()
        if not sel:
            messagebox.showinfo("", "Please select a testcase.")
            return
        name = sel[0]
        categories = get_categories()
        if not categories:
            messagebox.showinfo("", "No categories defined in APP_CATEGORIES.")
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
        sel = self.tc_listbox.selection()
        if not sel:
            messagebox.showinfo("", "Please select a testcase.")
            return
        names = list(sel)
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
        from adapters.database.testcases import fetch_testcase_yaml
        yaml_text, _ = fetch_testcase_yaml(name)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", yaml_text)
        self.editor.edit_modified(False)
        self._current_tc_name = name
        self.editor_title.configure(text=name, fg=FG)

    def _on_save(self):
        if not self._current_tc_name:
            return
        content = self.editor.get("1.0", tk.END).rstrip()
        from adapters.database.testcases import fetch_testcase_yaml, upsert_testcase
        _, category = fetch_testcase_yaml(self._current_tc_name)
        upsert_testcase(self._current_tc_name, content, category)

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
        self._on_save()
        sel = self.tc_listbox.selection()
        if not sel:
            messagebox.showinfo("", "Please select testcases.\n"
                                   "(Multi-select with Ctrl+Click)")
            return
        names = list(sel)
        self._set_running(True)
        threading.Thread(target=run_test,
                         args=(self, names, headless), daemon=True).start()

    def _on_stop(self):
        from adapters.browser.driver import quit_browser
        self.running = False
        for driver in list(self.drivers):
            quit_browser(driver)
        self.drivers.clear()
        quit_browser(self.driver)
        self.driver = None
        self._set_running(False)

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
