import tkinter as tk

from models.models import NavigationResult
from adapters.browser.driver import setup_logging
from interfaces.style import BG, NAV_BG, NAV_FG, NAV_ACTIVE_BG, NAV_ACTIVE_FG, BORDER, SUB_BG, FONT
from interfaces.style import apply_theme, color_titlebar
from interfaces.view_testing   import ViewTesting
from interfaces.view_recording import ViewRecording
from interfaces.view_results   import ViewResults
from interfaces.view_settings  import ViewSettings


class BugulaApp(ViewTesting, ViewRecording, ViewResults, ViewSettings):

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bugula")
        self.root.geometry("960x640")
        self.root.minsize(760, 480)
        self.root.resizable(True, True)
        self.root.configure(bg=BG)

        self.running  = False
        self.driver   = None
        self.recorder = None
        self.results: list[NavigationResult] = []

        self._current_section = "testing"
        self._current_tc_name = ""
        self._nav_buttons: dict[str, tk.Label] = {}

        apply_theme()
        setup_logging()
        color_titlebar(self.root)
        self._build_ui()
        self._show_section("testing")

    def _build_ui(self):
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Navigation sidebar
        self.nav_frame = tk.Frame(self.root, bg=NAV_BG, width=130)
        self.nav_frame.grid(row=0, column=0, sticky="ns")
        self.nav_frame.grid_propagate(False)
        tk.Frame(self.nav_frame, bg=NAV_BG, height=12).pack()

        for key, label in [("testing",  "Testing"),
                            ("record",   "Recording"),
                            ("results",  "Results"),
                            ("settings", "Settings")]:
            btn = tk.Label(
                self.nav_frame, text=label, bg=NAV_BG, fg=NAV_FG,
                font=(FONT, 11), anchor="w", padx=16, pady=10,
                cursor="hand2")
            btn.pack(fill=tk.X)
            btn.bind("<Button-1>", lambda _, k=key: self._show_section(k))
            self._nav_buttons[key] = btn

        # Paned layout
        self.paned = tk.PanedWindow(
            self.root, orient=tk.HORIZONTAL, bg=BORDER,
            sashwidth=4, sashrelief="flat", borderwidth=0,
            sashcursor="sb_h_double_arrow")
        self.paned.grid(row=0, column=1, sticky="nsew")

        self.sub_frame     = tk.Frame(self.paned, bg=SUB_BG)
        self.sub_container = tk.Frame(self.sub_frame, bg=SUB_BG)
        self.sub_container.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.paned.add(self.sub_frame, minsize=140, width=210)

        self.content_frame = tk.Frame(self.paned, bg=BG)
        self.paned.add(self.content_frame, minsize=300)

        # Build all views
        self.build_sub(self.sub_container)
        ViewResults.build_sub(self, self.sub_container)
        ViewSettings.build_sub(self, self.sub_container)
        self.build_content(self.content_frame)
        ViewRecording.build_content(self, self.content_frame)
        ViewResults.build_content(self, self.content_frame)
        ViewSettings.build_content(self, self.content_frame)

    def _show_section(self, section: str):
        if self._current_section == "testing":
            self._on_editor_focusout()

        self._current_section = section

        for key, btn in self._nav_buttons.items():
            btn.configure(bg=NAV_ACTIVE_BG if key == section else NAV_BG,
                          fg=NAV_ACTIVE_FG if key == section else NAV_FG)

        for w in self.sub_container.winfo_children():
            w.pack_forget()
        for w in self.content_frame.winfo_children():
            w.pack_forget()

        if section == "testing":
            self.sub_testing.pack(fill=tk.BOTH, expand=True)
            self.content_testing.pack(fill=tk.BOTH, expand=True)
            self._refresh_tc_list()
        elif section == "record":
            self.content_record.pack(fill=tk.BOTH, expand=True)
        elif section == "results":
            self.sub_results.pack(fill=tk.BOTH, expand=True)
            self.content_results.pack(fill=tk.BOTH, expand=True)
            self._refresh_results_list()
        elif section == "settings":
            self.sub_settings.pack(fill=tk.BOTH, expand=True)
            self.content_settings.pack(fill=tk.BOTH, expand=True)
            self._settings_show_first()

    def run(self):
        self.root.mainloop()
