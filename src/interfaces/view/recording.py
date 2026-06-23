import tkinter as tk
from tkinter import ttk

from interfaces.style.style import BG, FG, FG_SEC, ACCENT, RED, BORDER, FONT
from interfaces.helper.widgets import divider
from interfaces.helper.utils import get_categories


class ViewRecording:

    def build_sub(self, parent: tk.Frame):
        from interfaces.style.style import SUB_BG, SUB_SEL_BG, SUB_SEL_FG
        self.sub_record = tk.Frame(parent, bg=SUB_BG)

        tk.Label(self.sub_record, text="URL Presets", bg=SUB_BG, fg=FG_SEC,
                 font=(FONT, 9), anchor="w").pack(
            anchor="w", padx=(10, 4), pady=(8, 2))

        self._rec_preset_listbox = tk.Listbox(
            self.sub_record, bg=SUB_BG, fg=FG,
            selectbackground=SUB_SEL_BG, selectforeground=SUB_SEL_FG,
            font=(FONT, 11), borderwidth=0, highlightthickness=0,
            activestyle="none", relief="flat", exportselection=False)
        self._rec_preset_listbox.pack(
            fill=tk.BOTH, expand=True, padx=(10, 4), pady=4)
        self._rec_preset_listbox.bind(
            "<<ListboxSelect>>", self._on_rec_preset_select)

    def _refresh_record_presets(self):
        from adapters.database.presets import list_presets
        self._rec_preset_listbox.delete(0, tk.END)
        for name in list_presets():
            self._rec_preset_listbox.insert(tk.END, name)

    def _on_rec_preset_select(self, _=None):
        sel = self._rec_preset_listbox.curselection()
        if not sel:
            return
        name = self._rec_preset_listbox.get(sel[0])
        from adapters.database.presets import get_preset
        preset = get_preset(name)
        if not preset:
            return
        self._rec_url.set(preset["url"])
        self._rec_user.set(preset["username"])
        self._rec_pass.set(preset["password"])

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

    def _show_saving_popup(self):
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)

        # Accent-coloured border via outer frame
        outer = tk.Frame(popup, bg=ACCENT, padx=2, pady=2)
        outer.pack()

        inner = tk.Frame(outer, bg=BG, padx=50, pady=30)
        inner.pack()

        tk.Label(inner, text="⏳", bg=BG, fg=FG,
                 font=("Segoe UI Emoji", 48)).pack()
        tk.Label(inner, text="Saving...", bg=BG, fg=FG,
                 font=(FONT, 13)).pack(pady=(12, 0))

        popup.update_idletasks()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        pw, ph = popup.winfo_width(), popup.winfo_height()
        popup.geometry(f"+{rx + (rw - pw) // 2}+{ry + (rh - ph) // 2}")

        self._saving_popup = popup

    def _hide_saving_popup(self):
        if popup := getattr(self, "_saving_popup", None):
            popup.destroy()
            self._saving_popup = None

    def _on_record_stop(self):
        from adapters.browser.driver import quit_browser
        if not self.running:
            return
        self.running = False
        quit_browser(self.driver)
        self.rec_start_btn.configure(bg=ACCENT, fg="#ffffff")
        self.rec_stop_btn.configure(bg=BORDER, fg=FG_SEC)
        self._rec_status_var.set("")
        self._show_saving_popup()

    def _update_record_status(self, text: str):
        self._rec_status_var.set(text)

    def _on_record_saved(self, name: str):
        self._hide_saving_popup()
        self._rec_status_var.set(f"Saved: {name}")
        self.rec_start_btn.configure(bg=ACCENT, fg="#ffffff")
        self.rec_stop_btn.configure(bg=BORDER, fg=FG_SEC)
        self._show_section("testing")
        self._refresh_tc_list()
        if name in self.tc_listbox.get_children():
            self.tc_listbox.selection_set(name)
            self.tc_listbox.focus(name)
            self.tc_listbox.see(name)
            self._load_into_editor(name)
