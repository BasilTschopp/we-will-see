import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from interfaces.style.style import BG, BG2, FG, FG_SEC, ACCENT, BLUE, NAV_BG, RED, BORDER, FONT, MONO
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

        self._automated_var = tk.BooleanVar()
        self._screenshot_on_error_var = tk.BooleanVar()
        self._tc_run_timeout    = 0
        self._tc_step_timeout   = 0
        self._tc_parallel       = False
        self._tc_stop_on_error  = False

        self._settings_btn = tk.Label(footer, text="🔧", bg=BG, fg=FG,
                                      font=(FONT, 13), cursor="hand2")
        self._settings_btn.pack(side=tk.LEFT, padx=(4, 0))
        self._settings_btn.bind("<Button-1>", lambda _: self._on_tc_settings())
        add_tooltip(self._settings_btn, "Testcase Settings")

        self.save_btn = tk.Label(footer, text="💾", bg=BG, fg=FG,
                                 font=(FONT, 13), cursor="hand2")
        self.save_btn.pack(side=tk.LEFT, padx=(4, 0), pady=2)
        self.save_btn.bind("<Button-1>", lambda _: self._on_save())
        add_tooltip(self.save_btn, "Save")
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
        self.tc_listbox.delete(0, tk.END)
        names = sorted(
            (name for name, cat in list_testcases()
             if filter_cat == "All" or cat == filter_cat),
            key=str.casefold)
        for name in names:
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
        from adapters.database.testcases import (
            fetch_testcase_yaml, fetch_automated,
            fetch_screenshot_on_error, fetch_run_timeout, fetch_step_timeout,
            fetch_parallel, fetch_stop_on_error,
        )
        yaml_text, _ = fetch_testcase_yaml(name)
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", yaml_text)
        self.editor.edit_modified(False)
        self._current_tc_name = name
        self.editor_title.configure(text=name, fg=FG)
        self._automated_var.set(fetch_automated(name))
        self._screenshot_on_error_var.set(fetch_screenshot_on_error(name))
        self._tc_run_timeout   = fetch_run_timeout(name)
        self._tc_step_timeout  = fetch_step_timeout(name)
        self._tc_parallel      = fetch_parallel(name)
        self._tc_stop_on_error = fetch_stop_on_error(name)
        self._refresh_settings_icon()

    def _on_tc_settings(self):
        if not self._current_tc_name:
            return
        popup = tk.Toplevel(self.root)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.configure(bg=BORDER)
        popup.transient(self.root)

        inner = tk.Frame(popup, bg=BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        header = tk.Label(inner, text="Testcase Settings", bg=NAV_BG, fg="#ffffff",
                          font=(FONT, 10, "bold"), anchor="w",
                          padx=14, pady=10, cursor="fleur")
        header.pack(fill=tk.X)

        def _start_drag(e):
            popup._drag_x = e.x_root - popup.winfo_x()
            popup._drag_y = e.y_root - popup.winfo_y()

        def _drag(e):
            popup.geometry(f"+{e.x_root - popup._drag_x}+{e.y_root - popup._drag_y}")

        header.bind("<ButtonPress-1>", _start_drag)
        header.bind("<B1-Motion>",     _drag)

        body = tk.Frame(inner, bg=BG)
        body.pack(fill=tk.X, padx=14, pady=(10, 4))

        tc_name = self._current_tc_name

        auto_var          = tk.BooleanVar(value=self._automated_var.get())
        sce_var           = tk.BooleanVar(value=self._screenshot_on_error_var.get())
        parallel_var      = tk.BooleanVar(value=self._tc_parallel)
        stop_on_error_var = tk.BooleanVar(value=self._tc_stop_on_error)

        def _save_to_db():
            from adapters.database.testcases import (
                update_automated, update_screenshot_on_error,
                update_run_timeout, update_step_timeout, update_parallel,
                update_stop_on_error,
            )
            update_automated(tc_name, auto_var.get())
            update_screenshot_on_error(tc_name, sce_var.get())
            update_parallel(tc_name, parallel_var.get())
            update_stop_on_error(tc_name, stop_on_error_var.get())
            try:
                rt = max(0, int(run_timeout_entry.get().strip() or "0"))
            except ValueError:
                rt = 0
            try:
                st = max(0, int(step_timeout_entry.get().strip() or "0"))
            except ValueError:
                st = 0
            update_run_timeout(tc_name, rt)
            update_step_timeout(tc_name, st)
            self._automated_var.set(auto_var.get())
            self._screenshot_on_error_var.set(sce_var.get())
            self._tc_run_timeout   = rt
            self._tc_step_timeout  = st
            self._tc_parallel      = parallel_var.get()
            self._tc_stop_on_error = stop_on_error_var.get()
            self._refresh_settings_icon()

        tk.Checkbutton(
            body, text="Automated", variable=auto_var,
            bg=BG, fg=FG, selectcolor=BG,
            activebackground=BG, activeforeground=ACCENT,
            font=(FONT, 9), command=_save_to_db,
        ).pack(anchor="w")

        tk.Checkbutton(
            body, text="Screenshot on Error", variable=sce_var,
            bg=BG, fg=FG, selectcolor=BG,
            activebackground=BG, activeforeground=ACCENT,
            font=(FONT, 9), command=_save_to_db,
        ).pack(anchor="w", pady=(4, 0))

        tk.Checkbutton(
            body, text="Parallel matrix execution", variable=parallel_var,
            bg=BG, fg=FG, selectcolor=BG,
            activebackground=BG, activeforeground=ACCENT,
            font=(FONT, 9), command=_save_to_db,
        ).pack(anchor="w", pady=(4, 0))

        tk.Checkbutton(
            body, text="Stop on Error", variable=stop_on_error_var,
            bg=BG, fg=FG, selectcolor=BG,
            activebackground=BG, activeforeground=ACCENT,
            font=(FONT, 9), command=_save_to_db,
        ).pack(anchor="w", pady=(4, 0))

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=(10, 6))

        def _timeout_row(label, unit, default_val):
            row = tk.Frame(body, bg=BG)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label, bg=BG, fg=FG_SEC,
                     font=(FONT, 9), width=14, anchor="w").pack(side=tk.LEFT)
            e = tk.Entry(row, bg=BG2, fg=FG, font=(FONT, 9),
                         insertbackground=ACCENT, relief="flat",
                         highlightthickness=1, highlightbackground=BORDER, width=5)
            e.insert(0, str(default_val))
            e.pack(side=tk.LEFT, ipady=3)
            e.bind("<FocusOut>", lambda _: _save_to_db())
            tk.Label(row, text=unit, bg=BG, fg=FG_SEC,
                     font=(FONT, 9)).pack(side=tk.LEFT, padx=(5, 0))
            return e

        run_timeout_entry  = _timeout_row("Run Timeout",  "min", self._tc_run_timeout)
        step_timeout_entry = _timeout_row("Step Timeout", "s",   self._tc_step_timeout)

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=(10, 0))

        btn_row = tk.Frame(inner, bg=BG)
        btn_row.pack(fill=tk.X, padx=14, pady=10)

        close_lbl = tk.Label(btn_row, text="Close", bg=BG, fg=FG_SEC,
                             font=(FONT, 9), cursor="hand2")
        close_lbl.pack(side=tk.RIGHT)
        close_lbl.bind("<Button-1>", lambda _: popup.destroy())

        popup.update_idletasks()
        pw = popup.winfo_reqwidth()
        ph = popup.winfo_reqheight()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - pw) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - ph) // 2
        popup.geometry(f"{pw}x{ph}+{x}+{y}")
        popup.deiconify()
        popup.grab_set()
        popup.lift()
        popup.focus_force()

    def _refresh_settings_icon(self):
        self._settings_btn.configure(fg=FG)

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
        self._on_save()
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
