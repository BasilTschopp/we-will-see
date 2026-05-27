import tkinter as tk
from tkinter import ttk

from interfaces.style import BG, FG, FG_SEC, ACCENT, RED, BORDER, FONT
from interfaces.helper import divider, get_categories


class ViewRecording:

    def build_content(self, parent: tk.Frame):
        self.content_record = tk.Frame(parent, bg=BG)

        outer = tk.Frame(self.content_record, bg=BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=32, pady=24)

        tk.Label(outer, text="Record Session", bg=BG, fg=FG,
                 font=(FONT, 13, "bold"), anchor="w").pack(
            fill=tk.X, pady=(0, 16))

        def _row(label_text):
            row = tk.Frame(outer, bg=BG)
            row.pack(fill=tk.X, pady=4)
            tk.Label(row, text=label_text, bg=BG, fg=FG_SEC,
                     font=(FONT, 9), width=14, anchor="w").pack(side=tk.LEFT)
            return row

        r = _row("URL *")
        self._rec_url = tk.StringVar()
        ttk.Entry(r, textvariable=self._rec_url).pack(
            side=tk.LEFT, fill=tk.X, expand=True)

        r = _row("Save as")
        self._rec_name = tk.StringVar(value="recording")
        ttk.Entry(r, textvariable=self._rec_name).pack(
            side=tk.LEFT, fill=tk.X, expand=True)

        r = _row("Category")
        self._rec_category = tk.StringVar()
        categories = get_categories()
        self._rec_cat_combo = ttk.Combobox(r, textvariable=self._rec_category,
                                           values=categories, state="readonly")
        self._rec_cat_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if categories:
            self._rec_category.set(categories[0])

        r = _row("Browser")
        self._rec_browser = tk.StringVar(value="chrome")
        browser_frame = tk.Frame(r, bg=BG)
        browser_frame.pack(side=tk.LEFT)
        for b in ("chrome", "edge", "firefox"):
            tk.Radiobutton(
                browser_frame, text=b.capitalize(),
                variable=self._rec_browser, value=b,
                bg=BG, fg=FG, selectcolor=BG,
                activebackground=BG, activeforeground=ACCENT,
                font=(FONT, 10)).pack(side=tk.LEFT, padx=(0, 10))



        divider(outer, pady=12)
        tk.Label(outer, text="Login (optional)", bg=BG, fg=FG_SEC,
                 font=(FONT, 9), anchor="w").pack(fill=tk.X)

        r = _row("Username")
        self._rec_user = tk.StringVar()
        ttk.Entry(r, textvariable=self._rec_user).pack(
            side=tk.LEFT, fill=tk.X, expand=True)

        r = _row("Password")
        self._rec_pass = tk.StringVar()
        ttk.Entry(r, textvariable=self._rec_pass, show="•").pack(
            side=tk.LEFT, fill=tk.X, expand=True)

        divider(outer, pady=16)

        btn_row = tk.Frame(outer, bg=BG)
        btn_row.pack(fill=tk.X)

        self.rec_start_btn = tk.Label(
            btn_row, text="Start", bg=ACCENT, fg="#ffffff",
            font=(FONT, 11, "bold"), cursor="hand2",
            padx=16, pady=8, relief="flat")
        self.rec_start_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.rec_start_btn.bind("<Button-1>", lambda _: self._on_record_start())

        self.rec_stop_btn = tk.Label(
            btn_row, text="Stop", bg=BORDER, fg=FG_SEC,
            font=(FONT, 11), cursor="hand2",
            padx=16, pady=8, relief="flat")
        self.rec_stop_btn.pack(side=tk.LEFT)
        self.rec_stop_btn.bind("<Button-1>", lambda _: self._on_record_stop())

        self._rec_status_var = tk.StringVar(value="")
        self.rec_status_lbl = tk.Label(
            outer, textvariable=self._rec_status_var,
            bg=BG, fg=ACCENT, font=(FONT, 9), anchor="w")
        self.rec_status_lbl.pack(fill=tk.X, pady=(10, 0))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_record_start(self):
        import threading
        from usecases.testcase_runner import run_record
        from tkinter import messagebox

        if self.running:
            messagebox.showwarning("", "Already running.")
            return
        url = self._rec_url.get().strip()
        if not url:
            messagebox.showwarning("", "Please enter a URL.")
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self._rec_url.set(url)

        name     = self._rec_name.get().strip().replace(" ", "_") or "recording"
        category = self._rec_category.get()
        browser  = self._rec_browser.get()
        private  = True

        username = self._rec_user.get().strip()
        password = self._rec_pass.get()

        self._set_running(True)
        self.rec_start_btn.configure(bg=BORDER, fg=FG_SEC)
        self.rec_stop_btn.configure(bg=RED, fg="#ffffff")
        self._rec_status_var.set("Opening browser...")

        threading.Thread(
            target=run_record,
            args=(self, url, name, browser, username, password, private, category, True),
            daemon=True,
        ).start()

    def _on_record_stop(self):
        from adapters.browser.driver import quit_browser
        if not self.running:
            return
        self.running = False
        quit_browser(self.driver)
        self.rec_start_btn.configure(bg=ACCENT, fg="#ffffff")
        self.rec_stop_btn.configure(bg=BORDER, fg=FG_SEC)
        self._rec_status_var.set("")

    def _update_record_status(self, text: str):
        self._rec_status_var.set(text)

    def _on_record_saved(self, name: str):
        self._rec_status_var.set(f"Saved: {name}")
        self.rec_start_btn.configure(bg=ACCENT, fg="#ffffff")
        self.rec_stop_btn.configure(bg=BORDER, fg=FG_SEC)
        self._show_section("testing")
        self._refresh_tc_list()
        for i in range(self.tc_listbox.size()):
            if self.tc_listbox.get(i) == name:
                self.tc_listbox.selection_clear(0, tk.END)
                self.tc_listbox.selection_set(i)
                self.tc_listbox.activate(i)
                self.tc_listbox.see(i)
                self._load_into_editor(name)
                break


