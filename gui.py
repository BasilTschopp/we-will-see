import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

import yaml

from models import log, NavigationResult
from browser import setup_logging, run_test, quit_browser
from testcases import TESTCASES_DIR


def _style_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "style")


def _load_style() -> dict:
    path = os.path.join(_style_dir(), "style.yaml")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return {}

_S = _load_style()
_C = _S.get("colors", {})
_N = _S.get("nav", {})
_U = _S.get("sub", {})
_F = _S.get("fonts", {})

BG      = _C.get("bg", "#f2f3f5")
BG2     = _C.get("bg2", "#ffffff")
FG      = _C.get("fg", "#2c3e50")
FG_SEC  = _C.get("fg_sec", "#8899a6")
ACCENT  = _C.get("accent", "#4db6a0")
RED     = _C.get("red", "#d47272")
BORDER  = _C.get("border", "#dfe3e8")
SEL     = _C.get("sel", "#e0f2ef")

NAV_BG        = _N.get("bg", "#34495e")
NAV_FG        = _N.get("fg", "#94a3b8")
NAV_ACTIVE_BG = _N.get("active_bg", ACCENT)
NAV_ACTIVE_FG = _N.get("active_fg", "#ffffff")

SUB_BG     = _U.get("bg", "#f2f3f5")
SUB_SEL_BG = _U.get("sel_bg", ACCENT)
SUB_SEL_FG = _U.get("sel_fg", "#ffffff")

FONT = _F.get("ui_mac" if sys.platform == "darwin" else "ui", "Segoe UI")
MONO = _F.get("mono_mac" if sys.platform == "darwin" else "mono", "Cascadia Code")


def _tc_dir() -> str:
    d = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                     TESTCASES_DIR)
    os.makedirs(d, exist_ok=True)
    return d


def _results_dir() -> str:
    d = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                     "results")
    os.makedirs(d, exist_ok=True)
    return d


class BugulaApp:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bugula")
        self.root.geometry("960x640")
        self.root.minsize(760, 480)
        self.root.resizable(True, True)
        self.root.configure(bg=BG)

        self.running = False
        self.driver = None
        self.results: list[NavigationResult] = []

        self._current_section = "testing"
        self._current_file = ""
        self._nav_buttons: dict[str, tk.Label] = {}

        self._apply_theme()
        setup_logging()
        self._color_titlebar()
        self._build_ui()
        self._show_section("testing")

    def _color_titlebar(self):
        if sys.platform != "win32":
            return
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            r, g, b = 0x2c, 0x3e, 0x50
            color = r | (g << 8) | (b << 16)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(ctypes.c_int(color)), 4)
            tr, tg, tb = 0xc0, 0xcc, 0xd4
            text_color = tr | (tg << 8) | (tb << 16)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 36, ctypes.byref(ctypes.c_int(text_color)), 4)
        except Exception:
            pass

    def _apply_theme(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, font=(FONT, 10))
        s.configure("TFrame", background=BG)
        s.configure("TEntry", fieldbackground=BG2, foreground=FG,
                     borderwidth=0, padding=(10, 7), font=(MONO, 10),
                     insertcolor=ACCENT)
        s.map("TEntry", fieldbackground=[("focus", "#f8fffe")])
        s.configure("Treeview", background=BG2, foreground=FG,
                     fieldbackground=BG2, borderwidth=0,
                     font=(FONT, 10), rowheight=26)
        s.map("Treeview", background=[("selected", SEL)],
               foreground=[("selected", ACCENT)])
        s.configure("Treeview.Heading", background=BG, foreground=FG,
                     font=(FONT, 9), borderwidth=0, relief="flat")

    def _build_ui(self):
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.nav_frame = tk.Frame(self.root, bg=NAV_BG, width=130)
        self.nav_frame.grid(row=0, column=0, sticky="ns")
        self.nav_frame.grid_propagate(False)

        tk.Frame(self.nav_frame, bg=NAV_BG, height=12).pack()

        for key, label in [("testing", "Testing"),
                           ("results", "Results")]:
            btn = tk.Label(
                self.nav_frame, text=label, bg=NAV_BG, fg=NAV_FG,
                font=(FONT, 11), anchor="w", padx=16, pady=10,
                cursor="hand2")
            btn.pack(fill=tk.X)
            btn.bind("<Button-1>", lambda e, k=key: self._show_section(k))
            self._nav_buttons[key] = btn

        self.paned = tk.PanedWindow(
            self.root, orient=tk.HORIZONTAL, bg=BORDER,
            sashwidth=4, sashrelief="flat", borderwidth=0,
            sashcursor="sb_h_double_arrow")
        self.paned.grid(row=0, column=1, sticky="nsew")

        self.sub_frame = tk.Frame(self.paned, bg=SUB_BG)
        self.sub_container = tk.Frame(self.sub_frame, bg=SUB_BG)
        self.sub_container.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.paned.add(self.sub_frame, minsize=140, width=210)

        self.content_frame = tk.Frame(self.paned, bg=BG)
        self.paned.add(self.content_frame, minsize=300)

        self._build_sub_testing()
        self._build_sub_results()
        self._build_content_testing()
        self._build_content_results()

    def _build_sub_testing(self):
        self.sub_testing = tk.Frame(self.sub_container, bg=SUB_BG)

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
        bar.winfo_children()[-1].bind("<Button-1>", lambda e: self._on_create())

        tk.Label(bar, text="−", bg=SUB_BG, fg=FG, font=(FONT, 14, "bold"),
                 cursor="hand2").pack(side=tk.LEFT)
        bar.winfo_children()[-1].bind("<Button-1>", lambda e: self._on_delete())

        self.tc_menu = tk.Menu(self.root, tearoff=0,
                               font=(FONT, 10), bg=BG2, fg=FG,
                               activebackground=ACCENT,
                               activeforeground="#ffffff")
        self.tc_menu.add_command(label="Create", command=self._on_create)
        self.tc_menu.add_command(label="Rename", command=self._on_rename)
        self.tc_menu.add_command(label="Delete", command=self._on_delete)

    def _build_sub_results(self):
        self.sub_results = tk.Frame(self.sub_container, bg=SUB_BG)

        self.results_listbox = tk.Listbox(
            self.sub_results, bg=SUB_BG, fg=FG,
            selectbackground=SUB_SEL_BG, selectforeground=SUB_SEL_FG,
            font=(FONT, 11), borderwidth=0, highlightthickness=0,
            activestyle="none", relief="flat", exportselection=False)
        self.results_listbox.pack(fill=tk.BOTH, expand=True,
                                   padx=(10, 4), pady=4)
        self.results_listbox.bind("<<ListboxSelect>>",
                                   self._on_result_select)

        bar = tk.Frame(self.sub_results, bg=SUB_BG)
        bar.pack(fill=tk.X, padx=(10, 4), pady=(0, 6))

        tk.Label(bar, text="−", bg=SUB_BG, fg=FG, font=(FONT, 14, "bold"),
                 cursor="hand2").pack(side=tk.LEFT)
        bar.winfo_children()[-1].bind("<Button-1>",
                                       lambda e: self._on_delete_result())

    def _build_content_testing(self):
        self.content_testing = tk.Frame(self.content_frame, bg=BG)

        editor_frame = tk.Frame(self.content_testing, bg=BG)
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=(8, 12),
                          pady=(8, 8))

        header = tk.Frame(editor_frame, bg=BG)
        header.pack(fill=tk.X, pady=(0, 4))

        self.editor_title = tk.Label(
            header, text="No testcase selected", bg=BG,
            fg=FG, font=(FONT, 10, "bold"), anchor="w", padx=10, pady=8)
        self.editor_title.pack(side=tk.LEFT, fill=tk.X, expand=True)

        icon_frame = tk.Frame(header, bg=BG)
        icon_frame.pack(side=tk.RIGHT)

        self.run_hl_btn = tk.Label(
            icon_frame, text="⚡", bg=BG, fg=ACCENT,
            font=(FONT, 16), cursor="hand2")
        self.run_hl_btn.pack(side=tk.LEFT, padx=(0, 2))
        self.run_hl_btn.bind("<Button-1>",
                             lambda e: self._on_run_test(headless=True))

        self.run_btn = tk.Label(
            icon_frame, text="▶", bg=BG, fg=ACCENT,
            font=(FONT, 14), cursor="hand2")
        self.run_btn.pack(side=tk.LEFT, padx=(0, 2))
        self.run_btn.bind("<Button-1>",
                          lambda e: self._on_run_test(headless=False))

        self.stop_btn = tk.Label(
            icon_frame, text="■", bg=BG, fg=BORDER,
            font=(FONT, 14), cursor="hand2")
        self.stop_btn.pack(side=tk.LEFT, padx=(4, 0))
        self.stop_btn.bind("<Button-1>", lambda e: self._on_stop())

        self._add_tooltip(self.run_hl_btn, "Run headless")
        self._add_tooltip(self.run_btn, "Run (visible)")
        self._add_tooltip(self.stop_btn, "Stop")

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

    @staticmethod
    def _add_tooltip(widget, text):
        tip = None

        def show(event):
            nonlocal tip
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            tk.Label(tip, text=text, bg="#333", fg="#fff",
                     font=("Segoe UI", 9), padx=6, pady=3).pack()

        def hide(event):
            nonlocal tip
            if tip:
                tip.destroy()
                tip = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def _build_content_results(self):
        self.content_results = tk.Frame(self.content_frame, bg=BG)

        inner = tk.Frame(self.content_results, bg=BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=(8, 12), pady=(8, 8))

        header = tk.Frame(inner, bg=BG)
        header.pack(fill=tk.X, pady=(0, 4))

        self.result_title = tk.Label(
            header, text="No result selected", bg=BG,
            fg=FG, font=(FONT, 10, "bold"), anchor="w",
            padx=10, pady=8)
        self.result_title.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.save_btn = tk.Label(
            header, text="↓", bg=BG, fg=ACCENT,
            font=(FONT, 16, "bold"), cursor="hand2")
        self.save_btn.pack(side=tk.RIGHT, padx=(0, 4))
        self.save_btn.bind("<Button-1>", lambda e: self._on_save_results())
        self._add_tooltip(self.save_btn, "Save as CSV")

        tree_frame = tk.Frame(inner, bg=BORDER)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("status", "description", "error")
        self.csv_tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            selectmode="browse", height=18)

        self.csv_tree.heading("status", text="Status", anchor="w")
        self.csv_tree.heading("description", text="Description", anchor="w")
        self.csv_tree.heading("error", text="Error", anchor="w")

        self.csv_tree.column("status", width=70, minwidth=60, stretch=False, anchor="w")
        self.csv_tree.column("description", width=300, minwidth=150, anchor="w")
        self.csv_tree.column("error", width=350, minwidth=100, anchor="w")

        self.csv_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        csv_sb = ttk.Scrollbar(tree_frame, orient="vertical",
                                command=self.csv_tree.yview)
        csv_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.csv_tree.configure(yscrollcommand=csv_sb.set)

        self.csv_tree.tag_configure("err", foreground=RED)
        self.csv_tree.tag_configure("ok", foreground=FG)

    def _show_section(self, section: str):
        if self._current_section == "testing":
            self._on_editor_focusout()

        self._current_section = section

        for key, btn in self._nav_buttons.items():
            if key == section:
                btn.configure(bg=NAV_ACTIVE_BG, fg=NAV_ACTIVE_FG)
            else:
                btn.configure(bg=NAV_BG, fg=NAV_FG)

        for w in self.sub_container.winfo_children():
            w.pack_forget()
        for w in self.content_frame.winfo_children():
            w.pack_forget()

        if section == "testing":
            self.sub_testing.pack(fill=tk.BOTH, expand=True)
            self.content_testing.pack(fill=tk.BOTH, expand=True)
            self._refresh_tc_list()
        elif section == "results":
            self.sub_results.pack(fill=tk.BOTH, expand=True)
            self.content_results.pack(fill=tk.BOTH, expand=True)
            self._refresh_results_list()

    def _refresh_tc_list(self):
        self.tc_listbox.delete(0, tk.END)
        yamls = sorted([f for f in os.listdir(_tc_dir())
                        if f.endswith(".yaml")], reverse=True)
        for fname in yamls:
            self.tc_listbox.insert(tk.END, fname.replace(".yaml", ""))
        if self.tc_listbox.size() > 0:
            self.tc_listbox.selection_set(0)
            self.tc_listbox.activate(0)
            self._on_tc_select()

    def _on_tc_select(self, event=None):
        sel = self.tc_listbox.curselection()
        if not sel:
            return
        self._on_editor_focusout()
        name = self.tc_listbox.get(sel[0])
        path = os.path.join(_tc_dir(), name + ".yaml")
        self._load_into_editor(path)

    def _on_tc_rightclick(self, event):
        idx = self.tc_listbox.nearest(event.y)
        if idx >= 0:
            self.tc_listbox.selection_clear(0, tk.END)
            self.tc_listbox.selection_set(idx)
            self.tc_listbox.activate(idx)
        try:
            self.tc_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.tc_menu.grab_release()

    def _refresh_results_list(self):
        self.results_listbox.delete(0, tk.END)
        csvs = sorted([f for f in os.listdir(_results_dir())
                        if f.endswith(".csv")], reverse=True)
        for fname in csvs:
            self.results_listbox.insert(tk.END, fname.replace(".csv", ""))
        if self.results_listbox.size() > 0:
            self.results_listbox.selection_set(0)
            self.results_listbox.activate(0)
            self._on_result_select()

    def _on_result_select(self, event=None):
        sel = self.results_listbox.curselection()
        if not sel:
            return
        name = self.results_listbox.get(sel[0])
        self.result_title.configure(text=name, fg=FG)
        path = os.path.join(_results_dir(), name + ".csv")
        self._load_csv_into_tree(path)

    def _on_delete_result(self):
        sel = self.results_listbox.curselection()
        if not sel:
            messagebox.showinfo("", "Please select a result.")
            return
        name = self.results_listbox.get(sel[0])
        if not messagebox.askyesno("Delete", f"Delete '{name}'?"):
            return
        path = os.path.join(_results_dir(), name + ".csv")
        try:
            os.remove(path)
            self.csv_tree.delete(*self.csv_tree.get_children())
            self.result_title.configure(text="No result selected", fg=FG)
            self._refresh_results_list()
        except Exception as e:
            messagebox.showerror("", f"Error: {e}")

    def _load_into_editor(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.editor.delete("1.0", tk.END)
            self.editor.insert("1.0", content)
            self.editor.edit_modified(False)
            self._current_file = path
            name = os.path.basename(path).replace(".yaml", "")
            self.editor_title.configure(text=name, fg=FG)
        except Exception as e:
            messagebox.showerror("", f"Failed to load file:\n{e}")

    def _on_editor_focusout(self, event=None):
        if not self._current_file:
            return
        try:
            content = self.editor.get("1.0", tk.END).rstrip() + "\n"
            try:
                with open(self._current_file, "r", encoding="utf-8") as f:
                    if f.read() == content:
                        return
            except Exception:
                pass
            with open(self._current_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

    def _load_csv_into_tree(self, path: str):
        import csv as csvmod

        self.csv_tree.delete(*self.csv_tree.get_children())
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                rows = list(csvmod.DictReader(f, delimiter=";",
                                              quoting=csvmod.QUOTE_ALL))
            if not rows:
                return

            rows.sort(key=lambda r: (0 if r.get("status", "").strip('"')
                                     == "FEHLER" else 1))
            for row in rows:
                status_raw = row.get("status", "").strip('"')
                desc = row.get("description", "").strip('"')
                error = row.get("error_detail", "").strip('"').replace("\n", " ").replace("\r", "")
                status = "Error" if status_raw == "FEHLER" else "OK"
                tag = "err" if status_raw == "FEHLER" else "ok"
                self.csv_tree.insert("", tk.END,
                                     values=(status, desc, error),
                                     tags=(tag,))
        except Exception as e:
            log.warning(f"CSV load failed: {e}")

    def _on_save_results(self):
        children = self.csv_tree.get_children()
        if not children:
            messagebox.showinfo("", "No data to save.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV-Datei", "*.csv")],
            initialfile=self.result_title.cget("text") + ".csv")
        if not path:
            return
        try:
            import csv as csvmod
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csvmod.writer(f, delimiter=";",
                                       quoting=csvmod.QUOTE_ALL)
                writer.writerow(["Status", "Description", "Error"])
                for iid in children:
                    writer.writerow(self.csv_tree.item(iid, "values"))
            log.info(f"CSV saved: {path}")
        except Exception as e:
            messagebox.showerror("", f"Failed to save:\n{e}")

    def _on_create(self):
        name = simpledialog.askstring(
            "New testcase", "Name:", parent=self.root)
        if not name:
            return
        name = name.strip().replace(" ", "_")
        path = os.path.join(_tc_dir(), name + ".yaml")
        if os.path.exists(path):
            messagebox.showwarning("", f"'{name}' already exists.")
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("")
            self._refresh_tc_list()
            self._load_into_editor(path)
        except Exception as e:
            messagebox.showerror("", f"Error: {e}")

    def _on_rename(self):
        sel = self.tc_listbox.curselection()
        if not sel:
            messagebox.showinfo("", "Please select a file.")
            return
        old_name = self.tc_listbox.get(sel[0])
        new_name = simpledialog.askstring(
            "Rename", f"New name for '{old_name}':",
            initialvalue=old_name, parent=self.root)
        if not new_name or new_name == old_name:
            return
        new_name = new_name.strip().replace(" ", "_")
        old_path = os.path.join(_tc_dir(), old_name + ".yaml")
        new_path = os.path.join(_tc_dir(), new_name + ".yaml")
        if os.path.exists(new_path):
            messagebox.showwarning("", f"'{new_name}' already exists.")
            return
        try:
            os.rename(old_path, new_path)
            if self._current_file == old_path:
                self._current_file = new_path
            self._refresh_tc_list()
            self.editor_title.configure(text=new_name, fg=FG)
        except Exception as e:
            messagebox.showerror("", f"Error: {e}")

    def _on_delete(self):
        sel = self.tc_listbox.curselection()
        if not sel:
            messagebox.showinfo("", "Please select a file.")
            return
        name = self.tc_listbox.get(sel[0])
        if not messagebox.askyesno("Delete", f"Delete '{name}'?"):
            return
        path = os.path.join(_tc_dir(), name + ".yaml")
        try:
            os.remove(path)
            if self._current_file == path:
                self.editor.delete("1.0", tk.END)
                self._current_file = ""
                self.editor_title.configure(
                    text="No testcase selected", fg=FG_SEC)
            self._refresh_tc_list()
        except Exception as e:
            messagebox.showerror("", f"Error: {e}")

    def _on_run_test(self, headless: bool = True):
        if self.running:
            return
        self._on_editor_focusout()
        sel = self.tc_listbox.curselection()
        if not sel:
            messagebox.showinfo("", "Please select testcases.\n"
                                   "(Multi-select with Ctrl+Click)")
            return

        names = [self.tc_listbox.get(i) for i in sel]
        paths = [os.path.join(_tc_dir(), n + ".yaml") for n in names]
        self._set_running(True)
        threading.Thread(target=run_test,
                         args=(self, paths, headless), daemon=True).start()

    def _on_stop(self):
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

    def run(self):
        self.root.mainloop()