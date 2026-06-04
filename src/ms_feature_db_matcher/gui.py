from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox

from .config import DEFAULT_DNA_PATH, DEFAULT_OIL_ADDUCT_PATH, DEFAULT_RNA_PATH, ensure_output_dir
from .exporter import export_workbook_results
from .io_utils import read_dataset_sheets
from .matcher import MatchMode, RnaSubtypeMode, build_match_column
from .adduct_importer import is_oil_adduct_workbook
from .profiles import DatabaseMode, load_database_table

OUTPUT_FORMULA_COLUMN_NAME = "Matched Formula"
OUTPUT_SOURCE_COLUMN_NAME = "Matched Source"
OUTPUT_NAME_COLUMN_NAME = "Matched Short name"
DEFAULT_RNA_SUBTYPE_MODE = RnaSubtypeMode.R_AND_MER

COLORS = {
    "app_bg": "#F3F6FA",
    "card_bg": "#FFFFFF",
    "card_border": "#D6E0EA",
    "title": "#18324A",
    "text": "#324C63",
    "muted": "#5E7288",
    "soft_bg": "#EDF2F7",
    "input_bg": "#F8FBFD",
    "primary": "#0F766E",
    "primary_active": "#0C5D57",
    "button_text": "#FFFFFF",
    "disabled_text": "#B0DDD9",
    "secondary_border": "#B8C8D8",
    "secondary_bg": "#F0F4F8",
    "secondary_hover": "#E2E9F0",
    "dna": "#2563EB",
    "rna": "#DC2626",
    "warning_bg": "#FFF7E8",
    "warning_fg": "#A16207",
    "ready_bg": "#E8F7F4",
    "ready_fg": "#0F766E",
    "success_bg": "#EAF7EF",
    "success_fg": "#166534",
    "error_bg": "#FDECEC",
    "error_fg": "#B42318",
}


def _system_font() -> str:
    if sys.platform == "darwin":
        return "Helvetica Neue"
    return "Segoe UI"


_FONT = _system_font()

FONTS = {
    "title": (_FONT, 16, "bold"),
    "subtitle": (_FONT, 10),
    "card_title": (_FONT, 11, "bold"),
    "label": (_FONT, 10, "bold"),
    "text": (_FONT, 10),
    "small": (_FONT, 9),
    "button": (_FONT, 10, "bold"),
    "badge": (_FONT, 9),
}


@dataclass
class AppState:
    dataset_path: Path | None
    dna_db_path: Path
    rna_db_path: Path
    output_dir: Path

    @classmethod
    def create(cls) -> "AppState":
        return cls(
            dataset_path=None,
            dna_db_path=DEFAULT_DNA_PATH,
            rna_db_path=DEFAULT_RNA_PATH,
            output_dir=ensure_output_dir(),
        )


def _same_path(left: Path, right: Path) -> bool:
    return left.expanduser().resolve(strict=False) == right.expanduser().resolve(strict=False)


def path_badge_text(current: Path, default: Path) -> str:
    return "Default" if _same_path(current, default) else "Custom"


def database_badge_text(current: Path, default: Path) -> str:
    if _same_path(current, default):
        return "Default"
    if current.exists() and current.suffix.lower() in {".xlsx", ".xlsm"}:
        try:
            if is_oil_adduct_workbook(current):
                return "Oil adduct"
        except Exception:
            pass
    return "Custom"


def mode_label(mode: MatchMode) -> str:
    if mode == MatchMode.DNA:
        return "DNA only"
    if mode == MatchMode.RNA:
        return "RNA only"
    return "DNA + RNA"


def rna_subtype_enabled(mode: MatchMode) -> bool:
    return mode in (MatchMode.RNA, MatchMode.BOTH)


def describe_mode(mode: MatchMode) -> str:
    if mode == MatchMode.DNA:
        return "DNA only."
    if mode == MatchMode.RNA:
        return "RNA only."
    return "DNA + RNA."


def status_appearance(message: str) -> dict[str, str]:
    if message.startswith("Failed:"):
        return {
            "tone": "error",
            "title": "Attention Needed",
            "background": COLORS["error_bg"],
            "foreground": COLORS["error_fg"],
        }
    if message.startswith("Saved result to:"):
        return {
            "tone": "success",
            "title": "Export Complete",
            "background": COLORS["success_bg"],
            "foreground": COLORS["success_fg"],
        }
    if message.startswith("Select a dataset"):
        return {
            "tone": "warning",
            "title": "Dataset Missing",
            "background": COLORS["warning_bg"],
            "foreground": COLORS["warning_fg"],
        }
    return {
        "tone": "ready",
        "title": "Ready to Run",
        "background": COLORS["ready_bg"],
        "foreground": COLORS["ready_fg"],
    }


def _truncate_path(path: Path, max_len: int = 50) -> str:
    text = str(path)
    if len(text) <= max_len:
        return text
    head = text[:15]
    tail = text[-(max_len - 18):]
    return f"{head}...{tail}"


def open_output_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    if os.name == "posix":
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen([opener, str(path)])
        return
    raise OSError(f"Unsupported platform for opening folders: {os.name}")


def run_matching(
    state: AppState,
    mode: MatchMode,
    rna_subtype_mode: RnaSubtypeMode = DEFAULT_RNA_SUBTYPE_MODE,
) -> Path:
    if state.dataset_path is None:
        raise ValueError("Please select a dataset file before running matching.")
    if not state.dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {state.dataset_path}")

    dataset_sheets = read_dataset_sheets(state.dataset_path)

    dna_table = None
    rna_table = None
    if mode in (MatchMode.DNA, MatchMode.BOTH):
        dna_table = load_database_table(
            state.dna_db_path,
            DatabaseMode.DNA,
            use_default_profile=_same_path(state.dna_db_path, DEFAULT_DNA_PATH),
        )
    if mode in (MatchMode.RNA, MatchMode.BOTH):
        rna_table = load_database_table(
            state.rna_db_path,
            DatabaseMode.RNA,
            use_default_profile=_same_path(state.rna_db_path, DEFAULT_RNA_PATH),
        )

    if dna_table is None:
        dna_table = build_empty_database_table("Charged monoisotopic mass")
    if rna_table is None:
        rna_table = build_empty_database_table("[M+H]+")

    match_cells_by_sheet = {
        sheet_name: build_match_column(
            dataset,
            dna_table,
            rna_table,
            mode,
            rna_subtype_mode=rna_subtype_mode,
        )
        for sheet_name, dataset in dataset_sheets.items()
    }
    return export_workbook_results(
        datasets=dataset_sheets,
        match_cells_by_sheet=match_cells_by_sheet,
        source_path=state.dataset_path,
        output_dir=state.output_dir,
        formula_column_name=OUTPUT_FORMULA_COLUMN_NAME,
        name_column_name=OUTPUT_NAME_COLUMN_NAME,
        source_column_name=(
            OUTPUT_SOURCE_COLUMN_NAME
            if mode in (MatchMode.DNA, MatchMode.BOTH)
            else None
        ),
    )


def build_empty_database_table(mass_column: str):
    from pandas import DataFrame

    return DataFrame(columns=["Short name", "Formula", mass_column])


class MatcherApp:
    def __init__(self, root: tk.Tk, state: AppState) -> None:
        self.root = root
        self.state = state
        self.root.title("MS Feature DB Matcher")
        self.root.configure(bg=COLORS["app_bg"])
        self.root.geometry("640x690")
        self.root.minsize(580, 690)

        self.dataset_var = tk.StringVar(value="")
        self.dna_var = tk.StringVar(value=str(state.dna_db_path))
        self.rna_var = tk.StringVar(value=str(state.rna_db_path))
        self.mode_var = tk.StringVar(value=MatchMode.BOTH.value)
        self.rna_subtype_var = tk.StringVar(value=DEFAULT_RNA_SUBTYPE_MODE.value)
        self.status_var = tk.StringVar(value="Select a dataset file to start matching.")
        self.status_title_var = tk.StringVar()
        self.dataset_badge_var = tk.StringVar()
        self.dna_badge_var = tk.StringVar()
        self.rna_badge_var = tk.StringVar()

        self.mode_tiles: dict[MatchMode, dict[str, tk.Widget]] = {}
        self.rna_subtype_buttons: dict[RnaSubtypeMode, tk.Button] = {}
        self.standard_database_button: tk.Button | None = None
        self.oil_adduct_database_button: tk.Button | None = None
        self.run_button: tk.Button | None = None
        self.status_frame: tk.Frame | None = None
        self.status_title_label: tk.Label | None = None
        self.status_detail_label: tk.Label | None = None

        for var in (
            self.dataset_var,
            self.dna_var,
            self.rna_var,
            self.mode_var,
            self.rna_subtype_var,
        ):
            var.trace_add("write", self._on_ui_state_change)

        self._build()
        self._refresh_ui()

    def _build(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        shell = tk.Frame(self.root, bg=COLORS["app_bg"], padx=20, pady=14)
        shell.grid(sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        # ── Header ──
        header = tk.Frame(shell, bg=COLORS["app_bg"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tk.Label(
            header, text="MS Feature DB Matcher",
            bg=COLORS["app_bg"], fg=COLORS["title"], font=FONTS["title"],
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text="Match features against DNA / RNA databases  |  20 ppm",
            bg=COLORS["app_bg"], fg=COLORS["muted"], font=FONTS["subtitle"],
        ).grid(row=1, column=0, sticky="w", pady=(1, 0))

        # ── Input Files card ──
        input_card = self._create_card(shell, "Input Files")
        self.input_card = input_card
        input_card.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        input_card.columnconfigure(0, weight=1)

        self._add_file_picker(
            input_card, row=0, label="Dataset",
            variable=self.dataset_var, badge_var=self.dataset_badge_var,
            command=self._choose_dataset,
            filetypes=[("Supported files", "*.csv *.tsv *.xlsx *.xls"), ("All files", "*.*")],
        )
        self._add_file_picker(
            input_card, row=1, label="DNA Database",
            variable=self.dna_var, badge_var=self.dna_badge_var,
            command=self._choose_dna_db,
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
        )
        self.rna_database_group = self._add_file_picker(
            input_card, row=2, label="RNA Database",
            variable=self.rna_var, badge_var=self.rna_badge_var,
            command=self._choose_rna_db,
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
        )
        database_preset_row = tk.Frame(self.rna_database_group, bg=COLORS["card_bg"])
        database_preset_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        for col in range(2):
            database_preset_row.columnconfigure(col, weight=1, uniform="database_preset")
        self.standard_database_button = self._make_button(
            database_preset_row,
            text="Standard DB",
            command=self._apply_standard_default_database,
            primary=False,
            width=15,
        )
        self.standard_database_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.oil_adduct_database_button = self._make_button(
            database_preset_row,
            text="Oil Adduct DB",
            command=self._apply_oil_default_database,
            primary=False,
            width=15,
        )
        self.oil_adduct_database_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        # ── Matching Mode card ──
        mode_card = self._create_card(shell, "Matching Mode")
        mode_card.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        mode_card.columnconfigure(0, weight=1)
        tile_row = tk.Frame(mode_card, bg=COLORS["card_bg"])
        tile_row.grid(row=1, column=0, sticky="ew")
        for col in range(3):
            tile_row.columnconfigure(col, weight=1, uniform="mode")
        for idx, mode in enumerate((MatchMode.DNA, MatchMode.RNA, MatchMode.BOTH)):
            tile = self._create_mode_tile(tile_row, mode)
            px = (0 if idx == 0 else 3, 0 if idx == 2 else 3)
            tile["frame"].grid(row=0, column=idx, sticky="nsew", padx=px)

        subtype_row = tk.Frame(mode_card, bg=COLORS["card_bg"])
        subtype_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        subtype_row.columnconfigure(0, weight=1)
        tk.Label(
            subtype_row,
            text="RNA subtype",
            bg=COLORS["card_bg"],
            fg=COLORS["muted"],
            font=FONTS["small"],
        ).grid(row=0, column=0, sticky="w")

        subtype_buttons = tk.Frame(subtype_row, bg=COLORS["card_bg"])
        subtype_buttons.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        for col in range(3):
            subtype_buttons.columnconfigure(col, weight=1, uniform="rna_subtype")
        for idx, subtype in enumerate(
            (
                RnaSubtypeMode.R_ONLY,
                RnaSubtypeMode.MER_ONLY,
                RnaSubtypeMode.R_AND_MER,
            )
        ):
            button = self._create_rna_subtype_button(subtype_buttons, subtype)
            px = (0 if idx == 0 else 3, 0 if idx == 2 else 3)
            button.grid(row=0, column=idx, sticky="ew", padx=px)

        # ── Status bar ──
        self.status_frame = tk.Frame(
            shell, bg=COLORS["warning_bg"],
            highlightthickness=1, highlightbackground=COLORS["card_border"],
            padx=12, pady=6,
        )
        self.status_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.status_frame.columnconfigure(0, weight=1)
        self.status_title_label = tk.Label(
            self.status_frame, textvariable=self.status_title_var,
            bg=COLORS["warning_bg"], fg=COLORS["warning_fg"],
            font=FONTS["label"], anchor="w",
        )
        self.status_title_label.grid(row=0, column=0, sticky="w")
        self.status_detail_label = tk.Label(
            self.status_frame, textvariable=self.status_var,
            bg=COLORS["warning_bg"], fg=COLORS["text"],
            font=FONTS["small"], anchor="w", justify="left",
        )
        self.status_detail_label.grid(row=1, column=0, sticky="w", pady=(1, 0))

        # ── Action buttons (right-aligned) ──
        button_bar = tk.Frame(shell, bg=COLORS["app_bg"])
        button_bar.grid(row=4, column=0, sticky="ew")
        for col in range(2):
            button_bar.columnconfigure(col, weight=1, uniform="actions")

        open_btn = self._make_button(
            button_bar, text="Open Output Folder",
            command=self._open_output, primary=False, width=16,
        )
        open_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.run_button = self._make_button(
            button_bar, text="Run Matching",
            command=self._run, primary=True, width=16,
        )
        self.run_button.grid(row=0, column=1, sticky="ew")

    def _create_card(self, parent: tk.Widget, title: str) -> tk.Frame:
        outer = tk.Frame(
            parent, bg=COLORS["card_bg"],
            highlightthickness=1, highlightbackground=COLORS["card_border"],
            padx=14, pady=10,
        )
        tk.Label(
            outer, text=title,
            bg=COLORS["card_bg"], fg=COLORS["title"],
            font=FONTS["card_title"], anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        return outer

    def _add_file_picker(
        self, frame: tk.Frame, row: int, label: str,
        variable: tk.StringVar, badge_var: tk.StringVar,
        command, filetypes,
    ) -> tk.Frame:
        group = tk.Frame(frame, bg=COLORS["card_bg"])
        group.grid(row=row + 1, column=0, sticky="ew", pady=(0, 8 if row < 2 else 0))
        group.columnconfigure(0, weight=1)

        # Label + inline badge
        label_row = tk.Frame(group, bg=COLORS["card_bg"])
        label_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 2))
        tk.Label(
            label_row, text=label,
            bg=COLORS["card_bg"], fg=COLORS["title"], font=FONTS["label"],
        ).pack(side="left")
        tk.Label(
            label_row, textvariable=badge_var,
            bg=COLORS["soft_bg"], fg=COLORS["muted"],
            font=FONTS["badge"], padx=6, pady=1,
        ).pack(side="left", padx=(6, 0))

        # Entry + Browse on same line
        entry = tk.Entry(
            group, textvariable=variable,
            relief="flat", bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["card_border"],
            highlightcolor=COLORS["primary"],
            bg=COLORS["input_bg"], fg=COLORS["text"],
            font=FONTS["text"],
            insertbackground=COLORS["title"],
        )
        entry.grid(row=1, column=0, sticky="ew", ipadx=6, ipady=5, padx=(0, 6))

        browse = self._make_button(group, text="Browse", command=command, primary=False, width=7)
        browse.grid(row=1, column=1, sticky="e")
        browse.configure(command=lambda: command(filetypes))
        return group

    def _create_mode_tile(self, parent: tk.Frame, mode: MatchMode) -> dict[str, tk.Widget]:
        frame = tk.Frame(
            parent, bg=COLORS["secondary_bg"],
            highlightthickness=1, highlightbackground=COLORS["secondary_border"],
            cursor="hand2", padx=8, pady=8,
        )
        frame.columnconfigure(0, weight=1)
        title = tk.Label(
            frame, text=mode_label(mode),
            bg=COLORS["secondary_bg"], fg=COLORS["title"],
            font=FONTS["label"], cursor="hand2",
        )
        title.grid(row=0, column=0)

        for widget in (frame, title):
            widget.bind("<Button-1>", lambda _e, m=mode: self._select_mode(m))

        self.mode_tiles[mode] = {"frame": frame, "title": title}
        return self.mode_tiles[mode]

    def _create_rna_subtype_button(
        self,
        parent: tk.Frame,
        subtype: RnaSubtypeMode,
    ) -> tk.Button:
        button = tk.Button(
            parent,
            text=subtype.value,
            command=lambda s=subtype: self._select_rna_subtype(s),
            bg=COLORS["secondary_bg"],
            fg=COLORS["title"],
            activebackground=COLORS["secondary_hover"],
            activeforeground=COLORS["title"],
            disabledforeground=COLORS["muted"],
            highlightthickness=1,
            highlightbackground=COLORS["secondary_border"],
            bd=0,
            relief="flat",
            font=FONTS["button"],
            padx=6,
            pady=5,
            cursor="hand2",
        )
        self.rna_subtype_buttons[subtype] = button
        return button

    def _make_button(
        self, parent: tk.Widget, text: str,
        command, primary: bool, width: int,
    ) -> tk.Button:
        bg = COLORS["primary"] if primary else COLORS["secondary_bg"]
        fg = COLORS["button_text"] if primary else COLORS["title"]
        active_bg = COLORS["primary_active"] if primary else COLORS["secondary_hover"]
        border = COLORS["primary"] if primary else COLORS["secondary_border"]
        dis_fg = COLORS["disabled_text"] if primary else COLORS["muted"]
        return tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg,
            activebackground=active_bg, activeforeground=fg,
            disabledforeground=dis_fg,
            highlightthickness=1, highlightbackground=border,
            bd=0, relief="flat",
            font=FONTS["button"],
            padx=14, pady=8,
            cursor="hand2", width=width,
        )

    def _choose_dataset(self, filetypes) -> None:
        path = filedialog.askopenfilename(title="Select dataset", filetypes=filetypes)
        if path:
            self.state.dataset_path = Path(path)
            self.dataset_var.set(path)

    def _choose_dna_db(self, filetypes) -> None:
        path = filedialog.askopenfilename(title="Select DNA database", filetypes=filetypes)
        if path:
            self.state.dna_db_path = Path(path)
            self.dna_var.set(path)

    def _choose_rna_db(self, filetypes) -> None:
        path = filedialog.askopenfilename(title="Select RNA database", filetypes=filetypes)
        if path:
            self.state.rna_db_path = Path(path)
            self.rna_var.set(path)

    def _apply_standard_default_database(self) -> None:
        self.state.dna_db_path = DEFAULT_DNA_PATH
        self.state.rna_db_path = DEFAULT_RNA_PATH
        self.dna_var.set(str(DEFAULT_DNA_PATH))
        self.rna_var.set(str(DEFAULT_RNA_PATH))
        self.status_var.set("Standard default databases selected.")

    def _apply_oil_default_database(self) -> None:
        self._apply_oil_adduct_database(DEFAULT_OIL_ADDUCT_PATH)

    def _apply_oil_adduct_database(self, path: Path) -> None:
        self.state.dna_db_path = path
        self.state.rna_db_path = path
        self.dna_var.set(str(path))
        self.rna_var.set(str(path))
        self.status_var.set(f"Oil adduct database: {_truncate_path(path)}")

    def _select_mode(self, mode: MatchMode) -> None:
        self.mode_var.set(mode.value)

    def _select_rna_subtype(self, subtype: RnaSubtypeMode) -> None:
        self.rna_subtype_var.set(subtype.value)

    def _on_ui_state_change(self, *_args) -> None:
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        dataset_text = self.dataset_var.get().strip()
        dna_path = Path(self.dna_var.get()) if self.dna_var.get().strip() else DEFAULT_DNA_PATH
        rna_path = Path(self.rna_var.get()) if self.rna_var.get().strip() else DEFAULT_RNA_PATH

        self.dataset_badge_var.set("Required" if not dataset_text else "Ready")
        self.dna_badge_var.set(database_badge_text(dna_path, DEFAULT_DNA_PATH))
        self.rna_badge_var.set(database_badge_text(rna_path, DEFAULT_RNA_PATH))

        # Update status: dataset-missing warning, or ready state
        if not dataset_text:
            if not self.status_var.get().startswith("Failed:"):
                self.status_var.set("Select a dataset file to start matching.")
        elif self.status_var.get().startswith("Select a dataset"):
            self.status_var.set(f"Output: {_truncate_path(self.state.output_dir)}")

        selected_mode = MatchMode(self.mode_var.get())
        selected_subtype = RnaSubtypeMode(self.rna_subtype_var.get())
        self._refresh_mode_tiles(selected_mode)
        self._refresh_database_preset_buttons(dna_path, rna_path)
        self._refresh_rna_subtype_buttons(selected_mode, selected_subtype)
        self._refresh_status()

        if self.run_button is not None:
            self.run_button.configure(state="normal" if dataset_text else "disabled")

    def _refresh_mode_tiles(self, selected_mode: MatchMode) -> None:
        for mode, widgets in self.mode_tiles.items():
            selected = mode == selected_mode
            frame_bg = COLORS["primary"] if selected else COLORS["secondary_bg"]
            title_fg = COLORS["button_text"] if selected else COLORS["title"]
            border = COLORS["primary"] if selected else COLORS["secondary_border"]
            widgets["frame"].configure(bg=frame_bg, highlightbackground=border)
            widgets["title"].configure(bg=frame_bg, fg=title_fg)

    def _refresh_database_preset_buttons(self, dna_path: Path, rna_path: Path) -> None:
        if self.standard_database_button is None or self.oil_adduct_database_button is None:
            return

        standard_selected = _same_path(dna_path, DEFAULT_DNA_PATH) and _same_path(
            rna_path, DEFAULT_RNA_PATH
        )
        oil_selected = _same_path(dna_path, DEFAULT_OIL_ADDUCT_PATH) and _same_path(
            rna_path, DEFAULT_OIL_ADDUCT_PATH
        )
        for button, selected in (
            (self.standard_database_button, standard_selected),
            (self.oil_adduct_database_button, oil_selected),
        ):
            button.configure(
                bg=COLORS["primary"] if selected else COLORS["secondary_bg"],
                fg=COLORS["button_text"] if selected else COLORS["title"],
                activebackground=(
                    COLORS["primary_active"] if selected else COLORS["secondary_hover"]
                ),
                activeforeground=COLORS["button_text"] if selected else COLORS["title"],
                highlightbackground=COLORS["primary"] if selected else COLORS["secondary_border"],
            )

    def _refresh_rna_subtype_buttons(
        self,
        selected_mode: MatchMode,
        selected_subtype: RnaSubtypeMode,
    ) -> None:
        enabled = rna_subtype_enabled(selected_mode)
        for subtype, button in self.rna_subtype_buttons.items():
            selected = subtype == selected_subtype and enabled
            button.configure(
                state="normal" if enabled else "disabled",
                bg=COLORS["primary"] if selected else COLORS["secondary_bg"],
                fg=COLORS["button_text"] if selected else COLORS["title"],
                activebackground=(
                    COLORS["primary_active"] if selected else COLORS["secondary_hover"]
                ),
                activeforeground=COLORS["button_text"] if selected else COLORS["title"],
                highlightbackground=(
                    COLORS["primary"] if selected else COLORS["secondary_border"]
                ),
                cursor="hand2" if enabled else "arrow",
            )

    def _refresh_status(self) -> None:
        appearance = status_appearance(self.status_var.get())
        self.status_title_var.set(appearance["title"])
        if self.status_frame is not None:
            self.status_frame.configure(bg=appearance["background"])
        if self.status_title_label is not None:
            self.status_title_label.configure(bg=appearance["background"], fg=appearance["foreground"])
        if self.status_detail_label is not None:
            self.status_detail_label.configure(bg=appearance["background"], fg=COLORS["text"])

    def _run(self) -> None:
        self.state.dna_db_path = Path(self.dna_var.get())
        self.state.rna_db_path = Path(self.rna_var.get())
        dataset_text = self.dataset_var.get().strip()
        self.state.dataset_path = Path(dataset_text) if dataset_text else None

        try:
            result_path = run_matching(
                self.state,
                MatchMode(self.mode_var.get()),
                rna_subtype_mode=RnaSubtypeMode(self.rna_subtype_var.get()),
            )
        except Exception as exc:
            messagebox.showerror("Matching Failed", str(exc))
            self.status_var.set(f"Failed: {exc}")
            self._refresh_status()
            return

        messagebox.showinfo("Matching Complete", f"Output saved to:\n{result_path}")
        self.status_var.set(f"Saved result to: {result_path}")
        self._refresh_status()

    def _open_output(self) -> None:
        try:
            open_output_folder(self.state.output_dir)
            self.status_var.set(f"Output: {_truncate_path(self.state.output_dir)}")
            self._refresh_status()
        except Exception as exc:
            messagebox.showerror("Open Output Folder Failed", str(exc))
            self.status_var.set(f"Failed: {exc}")
            self._refresh_status()


def launch_app() -> None:
    root = tk.Tk()
    MatcherApp(root, AppState.create())
    root.mainloop()
