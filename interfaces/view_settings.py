import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from datetime import datetime

from interfaces.style import BG, BG2, FG, FG_SEC, ACCENT, BORDER, FONT
from interfaces.helper import add_tooltip


_NAV_ITEMS = ["Backup", "Presets"]


class ViewSettings:

    def build_sub(self, parent: tk.Frame):
        from interfaces.style import SUB_BG, SUB_SEL_BG, SUB_SEL_FG
        self.sub_settings = tk.Frame(parent, bg=SUB_BG)

        self._settings_nav = tk.Listbox(
            self.sub_settings, bg=SUB_BG, fg=FG,
            selectbackground=SUB_SEL_BG, selectforeground=SUB_SEL_FG,
            font=(FONT, 11), borderwidth=0, highlightthickness=0,
            activestyle="none", relief="flat", exportselection=False)
        self._settings_nav.pack(fill=tk.BOTH, expand=True, padx=(10, 4), pady=4)
        for item in _NAV_ITEMS:
            self._settings_nav.insert(tk.END, item)
        self._settings_nav.bind("<<ListboxSelect>>", self._on_settings_nav_select)

    def build_content(self, parent: tk.Frame):
        self.content_settings = tk.Frame(parent, bg=BG)

        self._settings_backup_frame   = self._build_backup_panel(self.content_settings)
        self._settings_categories_frame = self._build_categories_panel(self.content_settings)

    # ------------------------------------------------------------------
    # Backup panel
    # ------------------------------------------------------------------

    def _build_backup_panel(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg=BG)
        inner = tk.Frame(frame, bg=BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

        tk.Label(inner, text="Database Backup", bg=BG, fg=FG,
                 font=(FONT, 13, "bold"), anchor="w").pack(anchor="w", pady=(0, 4))
        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 16))

        tk.Label(inner, text="Save a copy of the current database to a file.",
                 bg=BG, fg=FG_SEC, font=(FONT, 10), anchor="w").pack(anchor="w", pady=(0, 10))

        backup_btn = tk.Label(inner, text="⬇  Save backup…", bg=ACCENT, fg="#ffffff",
                              font=(FONT, 10, "bold"), cursor="hand2", padx=12, pady=6)
        backup_btn.pack(anchor="w")
        backup_btn.bind("<Button-1>", lambda _: self._on_backup_db())

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=20)

        tk.Label(inner, text="Database Restore", bg=BG, fg=FG,
                 font=(FONT, 13, "bold"), anchor="w").pack(anchor="w", pady=(0, 4))
        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 16))

        tk.Label(inner,
                 text="Load a backup file. The current database will be overwritten.",
                 bg=BG, fg=FG_SEC, font=(FONT, 10), anchor="w").pack(anchor="w", pady=(0, 10))

        restore_btn = tk.Label(inner, text="⬆  Restore backup…", bg=BG2, fg=FG,
                               font=(FONT, 10, "bold"), cursor="hand2", padx=12, pady=6,
                               relief="flat", highlightthickness=1,
                               highlightbackground=BORDER)
        restore_btn.pack(anchor="w")
        restore_btn.bind("<Button-1>", lambda _: self._on_restore_db())

        return frame

    def _on_backup_db(self):
        from adapters.database.connection import _db_path
        default = "bugula-backup-" + datetime.now().strftime("%Y%m%d-%H%M") + ".db"
        dest = filedialog.asksaveasfilename(
            title="Save database backup",
            defaultextension=".db",
            filetypes=[("SQLite database", "*.db"), ("All files", "*.*")],
            initialfile=default)
        if not dest:
            return
        try:
            src = sqlite3.connect(_db_path())
            dst = sqlite3.connect(dest)
            src.backup(dst)
            dst.close()
            src.close()
            messagebox.showinfo("Backup", f"Backup saved:\n{dest}")
        except Exception as e:
            messagebox.showerror("Backup failed", str(e))

    def _on_restore_db(self):
        from adapters.database.connection import _db_path
        src_path = filedialog.askopenfilename(
            title="Select backup to restore",
            filetypes=[("SQLite database", "*.db"), ("All files", "*.*")])
        if not src_path:
            return
        if not messagebox.askyesno(
                "Restore",
                "The current database will be overwritten.\n\nContinue?"):
            return
        try:
            src = sqlite3.connect(src_path)
            dst = sqlite3.connect(_db_path())
            src.backup(dst)
            dst.close()
            src.close()
            messagebox.showinfo("Restore", "Database restored successfully.")
            self._refresh_tc_list()
            self._refresh_results_list()
        except Exception as e:
            messagebox.showerror("Restore failed", str(e))

    # ------------------------------------------------------------------
    # Categories panel
    # ------------------------------------------------------------------

    def _build_categories_panel(self, parent: tk.Frame) -> tk.Frame:
        from interfaces.style import SUB_SEL_BG, SUB_SEL_FG
        frame = tk.Frame(parent, bg=BG)
        inner = tk.Frame(frame, bg=BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

        tk.Label(inner, text="Categories", bg=BG, fg=FG,
                 font=(FONT, 13, "bold"), anchor="w").pack(anchor="w", pady=(0, 4))
        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=(0, 16))

        tk.Label(inner, text="Categories available when assigning testcases.",
                 bg=BG, fg=FG_SEC, font=(FONT, 10), anchor="w").pack(anchor="w", pady=(0, 10))

        list_frame = tk.Frame(inner, bg=BG)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self._cat_listbox = tk.Listbox(
            list_frame, bg=BG2, fg=FG,
            selectbackground=SUB_SEL_BG, selectforeground=SUB_SEL_FG,
            font=(FONT, 11), borderwidth=0, highlightthickness=1,
            highlightbackground=BORDER,
            activestyle="none", relief="flat", exportselection=False)
        self._cat_listbox.pack(fill=tk.BOTH, expand=True)

        bar = tk.Frame(inner, bg=BG)
        bar.pack(fill=tk.X, pady=(6, 0))

        add_lbl = tk.Label(bar, text="+", bg=BG, fg=FG,
                           font=(FONT, 14, "bold"), cursor="hand2")
        add_lbl.pack(side=tk.LEFT, padx=(0, 6))
        add_lbl.bind("<Button-1>", lambda _: self._on_cat_add())
        add_tooltip(add_lbl, "Add category")

        del_lbl = tk.Label(bar, text="−", bg=BG, fg=FG,
                           font=(FONT, 14, "bold"), cursor="hand2")
        del_lbl.pack(side=tk.LEFT)
        del_lbl.bind("<Button-1>", lambda _: self._on_cat_delete())
        add_tooltip(del_lbl, "Delete selected")

        return frame

    def _refresh_cat_listbox(self):
        from adapters.database.settings import get_categories
        self._cat_listbox.delete(0, tk.END)
        for cat in get_categories():
            self._cat_listbox.insert(tk.END, cat)

    def _on_cat_add(self):
        name = simpledialog.askstring("Add category", "Name:", parent=self.root)
        if not name or not name.strip():
            return
        name = name.strip()
        from adapters.database.settings import get_categories, set_categories
        cats = get_categories()
        if name in cats:
            messagebox.showwarning("", f"'{name}' already exists.")
            return
        cats.append(name)
        set_categories(cats)
        self._refresh_cat_listbox()
        self._sync_category_combo()

    def _on_cat_delete(self):
        sel = self._cat_listbox.curselection()
        if not sel:
            return
        name = self._cat_listbox.get(sel[0])
        if not messagebox.askyesno("Delete", f"Delete category '{name}'?"):
            return
        from adapters.database.settings import get_categories, set_categories
        cats = [c for c in get_categories() if c != name]
        set_categories(cats)
        self._refresh_cat_listbox()
        self._sync_category_combo()

    def _sync_category_combo(self):
        from interfaces.helper import get_categories
        cats = get_categories()
        try:
            self._filter_cat_combo.configure(values=["All"] + cats)
        except Exception:
            pass
        try:
            self._rec_cat_combo.configure(values=cats)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_settings_nav_select(self, _=None):
        sel = self._settings_nav.curselection()
        if not sel:
            return
        item = _NAV_ITEMS[sel[0]]
        self._settings_backup_frame.pack_forget()
        self._settings_categories_frame.pack_forget()
        if item == "Backup":
            self._settings_backup_frame.pack(fill=tk.BOTH, expand=True)
        elif item == "Presets":
            self._refresh_cat_listbox()
            self._settings_categories_frame.pack(fill=tk.BOTH, expand=True)

    def _settings_show_first(self):
        self._settings_nav.selection_clear(0, tk.END)
        self._settings_nav.selection_set(0)
        self._on_settings_nav_select()
