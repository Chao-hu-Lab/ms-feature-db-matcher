# RNA / MeR Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact RNA subtype selector so users can match `R`, `MeR`, or `R + MeR` while keeping the database scope selector simple.

**Architecture:** Keep `MatchMode` as the database scope (`DNA`, `RNA`, `Both`) for compatibility, but add a separate `RnaSubtypeMode` enum for RNA hit filtering. `build_match_column()` applies subtype filtering after existing R/MeR classification and `Tags matched` rules. The Tk GUI keeps three main mode tiles, displays `Both` as `DNA + RNA`, and adds a small second-row segmented control for RNA subtype.

**Tech Stack:** Python, pandas, openpyxl, Tkinter, pytest.

---

## Current Workspace Constraint

The branch currently contains uncommitted DNA Source output changes in `README.md`, `src/ms_feature_db_matcher/*.py`, and related tests. Do not revert those changes. Commit steps below should be run only after the implementer intentionally decides whether those existing changes are part of the same branch baseline; otherwise skip commit steps and report the dirty baseline.

## Preflight Baseline Gate

Before Task 1, run:

```powershell
git status --short --branch
pytest -v
```

Expected: the working tree may be dirty from the DNA Source output work, but the current suite should pass before adding RNA/MeR changes. If `pytest -v` fails before this plan is implemented, stop and fix or report the baseline failure first; do not mix baseline repair with RNA subtype work without naming it.

## File Structure

- Modify `src/ms_feature_db_matcher/matcher.py`: add `RnaSubtypeMode` and filter RNA/MeR hit lists.
- Modify `src/ms_feature_db_matcher/gui.py`: add display labels, `run_matching(..., rna_subtype_mode=...)`, and compact subtype segmented buttons.
- Modify `tests/test_matcher.py`: cover subtype filtering and tag intersection.
- Modify `tests/test_gui_smoke.py`: cover `run_matching()` subtype behavior and user-facing labels.
- Modify `README.md`: document `DNA only`, `RNA only`, `DNA + RNA`, and RNA subtype choices.

## Task 1: Matcher RNA Subtype Filtering

**Files:**
- Modify: `src/ms_feature_db_matcher/matcher.py`
- Test: `tests/test_matcher.py`

- [ ] **Step 1: Write failing matcher tests**

Update the import in `tests/test_matcher.py`:

```python
from ms_feature_db_matcher.matcher import (
    MatchMode,
    RnaSubtypeMode,
    build_match_column,
    parse_feature_mz,
)
```

Add these tests before `test_build_match_column_formula_empty_when_db_has_no_formula_col`:

```python
def test_build_match_column_rna_subtype_r_only_excludes_mer() -> None:
    dataset = pd.DataFrame({"Feature": ["268.1052/17.59"]})
    dna = pd.DataFrame({"Short name": [], "Charged monoisotopic mass": []})
    rna = pd.DataFrame(
        {
            "Short name": ["m1A", "m1Am"],
            "[M+H]+": [268.1052, 268.1052],
            "Formula": ["C11H16N5O3", "C11H18N5O4"],
        }
    )

    result = build_match_column(
        dataset,
        dna,
        rna,
        MatchMode.RNA,
        rna_subtype_mode=RnaSubtypeMode.R_ONLY,
    )

    assert result[0].text == "m1A"
    assert result[0].rna_names == ["m1A"]
    assert result[0].mer_names == []
    assert result[0].formula_text == "C11H16N5O3"
```

```python
def test_build_match_column_rna_subtype_mer_only_excludes_r() -> None:
    dataset = pd.DataFrame({"Feature": ["268.1052/17.59"]})
    dna = pd.DataFrame({"Short name": [], "Charged monoisotopic mass": []})
    rna = pd.DataFrame(
        {
            "Short name": ["m1A", "m1Am"],
            "[M+H]+": [268.1052, 268.1052],
            "Formula": ["C11H16N5O3", "C11H18N5O4"],
        }
    )

    result = build_match_column(
        dataset,
        dna,
        rna,
        MatchMode.RNA,
        rna_subtype_mode=RnaSubtypeMode.MER_ONLY,
    )

    assert result[0].text == "m1Am"
    assert result[0].rna_names == []
    assert result[0].mer_names == ["m1Am"]
    assert result[0].formula_text == "C11H18N5O4"
```

```python
def test_build_match_column_both_with_r_only_keeps_dna_and_excludes_mer() -> None:
    dataset = pd.DataFrame({"Feature": ["268.1052/17.59"]})
    dna = pd.DataFrame(
        {
            "Short name": ["dX"],
            "Charged monoisotopic mass": [268.1052],
            "Formula": ["C10H13N4O4"],
            "Source": ["DNA DB"],
        }
    )
    rna = pd.DataFrame(
        {
            "Short name": ["m1A", "m1Am"],
            "[M+H]+": [268.1052, 268.1052],
            "Formula": ["C11H16N5O3", "C11H18N5O4"],
        }
    )

    result = build_match_column(
        dataset,
        dna,
        rna,
        MatchMode.BOTH,
        rna_subtype_mode=RnaSubtypeMode.R_ONLY,
    )

    assert result[0].text == "dX/m1A"
    assert result[0].dna_names == ["dX"]
    assert result[0].rna_names == ["m1A"]
    assert result[0].mer_names == []
    assert result[0].source_text == "DNA DB"
```

```python
def test_build_match_column_both_with_mer_only_keeps_dna_and_excludes_r() -> None:
    dataset = pd.DataFrame({"Feature": ["268.1052/17.59"]})
    dna = pd.DataFrame(
        {
            "Short name": ["dX"],
            "Charged monoisotopic mass": [268.1052],
            "Formula": ["C10H13N4O4"],
        }
    )
    rna = pd.DataFrame(
        {
            "Short name": ["m1A", "m1Am"],
            "[M+H]+": [268.1052, 268.1052],
        }
    )

    result = build_match_column(
        dataset,
        dna,
        rna,
        MatchMode.BOTH,
        rna_subtype_mode=RnaSubtypeMode.MER_ONLY,
    )

    assert result[0].text == "dX/m1Am"
    assert result[0].rna_names == []
    assert result[0].mer_names == ["m1Am"]
```

```python
def test_build_match_column_rna_subtype_intersects_with_tags() -> None:
    dataset = pd.DataFrame(
        {
            "Feature": ["268.1052/17.59"],
            "Tags matched": ["3"],
        }
    )
    dna = pd.DataFrame({"Short name": [], "Charged monoisotopic mass": []})
    rna = pd.DataFrame(
        {
            "Short name": ["m1A", "m1Am"],
            "[M+H]+": [268.1052, 268.1052],
        }
    )

    result = build_match_column(
        dataset,
        dna,
        rna,
        MatchMode.RNA,
        rna_subtype_mode=RnaSubtypeMode.R_ONLY,
    )

    assert result[0].text == "No match"
    assert result[0].rna_names == []
    assert result[0].mer_names == []
```

```python
def test_build_match_column_dna_mode_ignores_rna_subtype() -> None:
    dataset = pd.DataFrame({"Feature": ["268.1052/17.59"]})
    dna = pd.DataFrame({"Short name": ["dX"], "Charged monoisotopic mass": [268.1052]})
    rna = pd.DataFrame({"Short name": ["m1A", "m1Am"], "[M+H]+": [268.1052, 268.1052]})

    result = build_match_column(
        dataset,
        dna,
        rna,
        MatchMode.DNA,
        rna_subtype_mode=RnaSubtypeMode.MER_ONLY,
    )

    assert result[0].text == "dX"
    assert result[0].dna_names == ["dX"]
    assert result[0].rna_names == []
    assert result[0].mer_names == []
```

- [ ] **Step 2: Run matcher tests to verify RED**

Run:

```powershell
pytest tests/test_matcher.py -v
```

Expected: FAIL during collection or test execution because `RnaSubtypeMode` and `rna_subtype_mode` do not exist.

- [ ] **Step 3: Implement matcher subtype enum and filtering**

In `src/ms_feature_db_matcher/matcher.py`, add this enum after `MatchMode`:

```python
class RnaSubtypeMode(str, Enum):
    R_ONLY = "R"
    MER_ONLY = "MeR"
    R_AND_MER = "R + MeR"
```

Change the `build_match_column()` signature:

```python
def build_match_column(
    dataset: pd.DataFrame,
    dna: pd.DataFrame,
    rna: pd.DataFrame,
    mode: MatchMode,
    rna_subtype_mode: RnaSubtypeMode = RnaSubtypeMode.R_AND_MER,
) -> list[MatchCell]:
```

After the existing `Tags matched` filtering block:

```python
        if "2" not in allowed_tags:
            rna_names, rna_formulas = [], []
        if "3" not in allowed_tags:
            mer_names, mer_formulas = [], []
```

add:

```python
        if rna_subtype_mode == RnaSubtypeMode.R_ONLY:
            mer_names, mer_formulas = [], []
        elif rna_subtype_mode == RnaSubtypeMode.MER_ONLY:
            rna_names, rna_formulas = [], []
```

Do not change DNA matching, source collection, rich text grouping, or the default behavior for existing callers.

- [ ] **Step 4: Run matcher tests to verify GREEN**

Run:

```powershell
pytest tests/test_matcher.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit matcher task if baseline is clean**

If there are no unrelated or previous-task uncommitted changes, run:

```powershell
git add src/ms_feature_db_matcher/matcher.py tests/test_matcher.py
git commit -m "feat: filter rna and mer subtypes"
```

If the DNA Source output changes are still uncommitted, skip this commit and report that the feature was implemented on a dirty baseline.

## Task 2: Public Matching Entry Point and Labels

**Files:**
- Modify: `src/ms_feature_db_matcher/gui.py`
- Test: `tests/test_gui_smoke.py`

- [ ] **Step 1: Write failing GUI/run_matching tests**

Update the matcher import in `tests/test_gui_smoke.py`:

```python
from ms_feature_db_matcher.matcher import MatchMode, RnaSubtypeMode
```

Update `test_describe_mode_explains_both_ordering()`:

```python
def test_describe_mode_explains_dna_plus_rna_ordering() -> None:
    summary = describe_mode(MatchMode.BOTH)

    assert "DNA" in summary
    assert "RNA" in summary
    assert "DNA + RNA" in summary
```

Update the GUI import list to include new helpers:

```python
from ms_feature_db_matcher.gui import (
    AppState,
    DEFAULT_RNA_SUBTYPE_MODE,
    describe_mode,
    mode_label,
    path_badge_text,
    rna_subtype_enabled,
    run_matching,
    status_appearance,
)
```

Add these tests after `test_describe_mode_explains_dna_plus_rna_ordering()`:

```python
def test_mode_label_uses_dna_plus_rna_instead_of_both() -> None:
    assert mode_label(MatchMode.DNA) == "DNA only"
    assert mode_label(MatchMode.RNA) == "RNA only"
    assert mode_label(MatchMode.BOTH) == "DNA + RNA"
    assert "Both" not in mode_label(MatchMode.BOTH)
```

```python
def test_default_rna_subtype_preserves_current_behavior() -> None:
    assert DEFAULT_RNA_SUBTYPE_MODE == RnaSubtypeMode.R_AND_MER
```

```python
def test_rna_subtype_enabled_only_for_modes_that_use_rna() -> None:
    assert not rna_subtype_enabled(MatchMode.DNA)
    assert rna_subtype_enabled(MatchMode.RNA)
    assert rna_subtype_enabled(MatchMode.BOTH)
```

Add this run-level test after `test_run_matching_in_rna_mode_omits_source_column()`:

```python
def test_run_matching_in_rna_mode_can_limit_to_mer_only(tmp_path) -> None:
    dataset_path = tmp_path / "dataset.csv"
    rna_path = tmp_path / "rna.xlsx"

    pd.DataFrame({"Feature": ["268.1052/17.59"]}).to_csv(dataset_path, index=False)
    pd.DataFrame(
        {
            "Short name": ["m1A", "m1Am"],
            "[M+H]+": [268.1052, 268.1052],
            "Formula": ["C11H16N5O3", "C11H18N5O4"],
        }
    ).to_excel(rna_path, index=False)

    state = AppState(
        dataset_path=dataset_path,
        dna_db_path=tmp_path / "missing-dna.xlsx",
        rna_db_path=rna_path,
        output_dir=tmp_path / "Output",
    )

    output_path = run_matching(
        state,
        MatchMode.RNA,
        rna_subtype_mode=RnaSubtypeMode.MER_ONLY,
    )
    result = pd.read_excel(output_path)

    assert list(result["Matched Short name"]) == ["m1Am"]
    assert list(result["Matched Formula"]) == ["C11H18N5O4"]
    assert "Matched Source" not in result.columns
```

```python
def test_run_matching_in_dna_mode_ignores_rna_subtype_and_missing_rna_db(tmp_path) -> None:
    dataset_path = tmp_path / "dataset.csv"
    dna_path = tmp_path / "dna.xlsx"

    pd.DataFrame({"Feature": ["268.1052/17.59"]}).to_csv(dataset_path, index=False)
    pd.DataFrame(
        {
            "Short name": ["dX"],
            "Charged monoisotopic mass": [268.1052],
        }
    ).to_excel(dna_path, index=False)

    state = AppState(
        dataset_path=dataset_path,
        dna_db_path=dna_path,
        rna_db_path=tmp_path / "missing-rna.xlsx",
        output_dir=tmp_path / "Output",
    )

    output_path = run_matching(
        state,
        MatchMode.DNA,
        rna_subtype_mode=RnaSubtypeMode.MER_ONLY,
    )
    result = pd.read_excel(output_path)

    assert list(result["Matched Short name"]) == ["dX"]
```

- [ ] **Step 2: Run GUI tests to verify RED**

Run:

```powershell
pytest tests/test_gui_smoke.py -v
```

Expected: FAIL because `DEFAULT_RNA_SUBTYPE_MODE`, `mode_label`, `rna_subtype_enabled`, and `run_matching(..., rna_subtype_mode=...)` are not wired into GUI yet.

- [ ] **Step 3: Implement GUI helpers and run_matching parameter**

In `src/ms_feature_db_matcher/gui.py`, update the matcher import:

```python
from .matcher import MatchMode, RnaSubtypeMode, build_match_column
```

Add this constant under output column constants:

```python
DEFAULT_RNA_SUBTYPE_MODE = RnaSubtypeMode.R_AND_MER
```

Add helper functions near `describe_mode()`:

```python
def mode_label(mode: MatchMode) -> str:
    if mode == MatchMode.DNA:
        return "DNA only"
    if mode == MatchMode.RNA:
        return "RNA only"
    return "DNA + RNA"
```

```python
def rna_subtype_enabled(mode: MatchMode) -> bool:
    return mode in (MatchMode.RNA, MatchMode.BOTH)
```

Replace `describe_mode()` with:

```python
def describe_mode(mode: MatchMode) -> str:
    if mode == MatchMode.DNA:
        return "DNA only."
    if mode == MatchMode.RNA:
        return "RNA only."
    return "DNA + RNA."
```

Change `run_matching()` signature:

```python
def run_matching(
    state: AppState,
    mode: MatchMode,
    rna_subtype_mode: RnaSubtypeMode = DEFAULT_RNA_SUBTYPE_MODE,
) -> Path:
```

Change the `match_cells_by_sheet` construction:

```python
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
```

Do not change `source_column_name`; DNA-containing modes still get `Matched Source`, RNA-only mode does not.

- [ ] **Step 4: Run matcher and GUI tests to verify GREEN**

Run:

```powershell
pytest tests/test_matcher.py tests/test_gui_smoke.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit public entry point task if baseline is clean**

If there are no unrelated or previous-task uncommitted changes, run:

```powershell
git add src/ms_feature_db_matcher/gui.py tests/test_gui_smoke.py src/ms_feature_db_matcher/matcher.py tests/test_matcher.py
git commit -m "feat: expose rna subtype matching"
```

If the DNA Source output changes are still uncommitted, skip this commit and report that the feature was implemented on a dirty baseline.

## Task 3: Compact Tk RNA Subtype Selector

**Files:**
- Modify: `src/ms_feature_db_matcher/gui.py`

- [ ] **Step 1: Add GUI state and subtype buttons**

In `MatcherApp.__init__`, add the subtype variable after `self.mode_var`:

```python
self.rna_subtype_var = tk.StringVar(value=DEFAULT_RNA_SUBTYPE_MODE.value)
```

Update the trace loop:

```python
for var in (
    self.dataset_var,
    self.dna_var,
    self.rna_var,
    self.mode_var,
    self.rna_subtype_var,
):
    var.trace_add("write", self._on_ui_state_change)
```

Add a widget registry after `self.mode_tiles`:

```python
self.rna_subtype_buttons: dict[RnaSubtypeMode, tk.Button] = {}
```

In `_build()`, replace the mode card construction with this structure:

```python
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
        subtype_row.columnconfigure(1, weight=1)
        tk.Label(
            subtype_row,
            text="RNA subtype",
            bg=COLORS["card_bg"],
            fg=COLORS["muted"],
            font=FONTS["small"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        subtype_buttons = tk.Frame(subtype_row, bg=COLORS["card_bg"])
        subtype_buttons.grid(row=0, column=1, sticky="ew")
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
```

- [ ] **Step 2: Add subtype button helpers**

Add these methods near `_create_mode_tile()`:

```python
    def _create_rna_subtype_button(
        self,
        parent: tk.Frame,
        subtype: RnaSubtypeMode,
    ) -> tk.Button:
        button = tk.Button(
            parent,
            text=subtype.value,
            command=lambda value=subtype: self._select_rna_subtype(value),
            bg=COLORS["secondary_bg"],
            fg=COLORS["title"],
            activebackground=COLORS["secondary_hover"],
            activeforeground=COLORS["title"],
            disabledforeground=COLORS["muted"],
            highlightthickness=1,
            highlightbackground=COLORS["secondary_border"],
            bd=0,
            relief="flat",
            font=FONTS["small"],
            padx=8,
            pady=4,
            cursor="hand2",
        )
        self.rna_subtype_buttons[subtype] = button
        return button
```

```python
    def _select_rna_subtype(self, subtype: RnaSubtypeMode) -> None:
        self.rna_subtype_var.set(subtype.value)
```

Update `_create_mode_tile()` so the tile title uses `mode_label(mode)` instead of `mode.value`:

```python
        title = tk.Label(
            frame, text=mode_label(mode),
            bg=COLORS["secondary_bg"], fg=COLORS["title"],
            font=FONTS["label"], cursor="hand2",
        )
```

- [ ] **Step 3: Refresh subtype button state**

In `_refresh_ui()`, replace:

```python
self._refresh_mode_tiles(MatchMode(self.mode_var.get()))
```

with:

```python
selected_mode = MatchMode(self.mode_var.get())
selected_subtype = RnaSubtypeMode(self.rna_subtype_var.get())
self._refresh_mode_tiles(selected_mode)
self._refresh_rna_subtype_buttons(selected_mode, selected_subtype)
```

Add this method after `_refresh_mode_tiles()`:

```python
    def _refresh_rna_subtype_buttons(
        self,
        selected_mode: MatchMode,
        selected_subtype: RnaSubtypeMode,
    ) -> None:
        enabled = rna_subtype_enabled(selected_mode)
        for subtype, button in self.rna_subtype_buttons.items():
            selected = subtype == selected_subtype
            if not enabled:
                button.configure(
                    state="disabled",
                    bg=COLORS["soft_bg"],
                    fg=COLORS["muted"],
                    activebackground=COLORS["soft_bg"],
                    highlightbackground=COLORS["card_border"],
                    cursor="arrow",
                )
                continue

            frame_bg = COLORS["primary"] if selected else COLORS["secondary_bg"]
            title_fg = COLORS["button_text"] if selected else COLORS["title"]
            border = COLORS["primary"] if selected else COLORS["secondary_border"]
            button.configure(
                state="normal",
                bg=frame_bg,
                fg=title_fg,
                activebackground=COLORS["primary_active"] if selected else COLORS["secondary_hover"],
                activeforeground=title_fg,
                highlightbackground=border,
                cursor="hand2",
            )
```

- [ ] **Step 4: Pass selected subtype when running**

In `_run()`, replace:

```python
result_path = run_matching(self.state, MatchMode(self.mode_var.get()))
```

with:

```python
result_path = run_matching(
    self.state,
    MatchMode(self.mode_var.get()),
    rna_subtype_mode=RnaSubtypeMode(self.rna_subtype_var.get()),
)
```

- [ ] **Step 5: Add a Tk widget smoke test for the actual selector**

Add this import to `tests/test_gui_smoke.py`:

```python
import tkinter as tk
```

Update the GUI import list to include `MatcherApp`:

```python
from ms_feature_db_matcher.gui import (
    AppState,
    DEFAULT_RNA_SUBTYPE_MODE,
    MatcherApp,
    describe_mode,
    mode_label,
    path_badge_text,
    rna_subtype_enabled,
    run_matching,
    status_appearance,
)
```

Add this test after `test_rna_subtype_enabled_only_for_modes_that_use_rna()`:

```python
def test_matcher_app_rna_subtype_selector_is_compact_and_mode_sensitive() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        app = MatcherApp(root, AppState.create())

        assert app.mode_tiles[MatchMode.BOTH]["title"].cget("text") == "DNA + RNA"
        assert [button.cget("text") for button in app.rna_subtype_buttons.values()] == [
            "R",
            "MeR",
            "R + MeR",
        ]
        assert app.rna_subtype_var.get() == "R + MeR"

        app._select_mode(MatchMode.DNA)
        app._refresh_ui()
        assert {
            button.cget("state")
            for button in app.rna_subtype_buttons.values()
        } == {"disabled"}

        app._select_mode(MatchMode.RNA)
        app._refresh_ui()
        assert {
            button.cget("state")
            for button in app.rna_subtype_buttons.values()
        } == {"normal"}
    finally:
        root.destroy()
```

If this test cannot initialize Tk on the execution host, do not delete it silently. Mark the GUI widget smoke as blocked by environment and perform the manual GUI validation step below on a machine with a display.

- [ ] **Step 6: Smoke check GUI code through automated and manual validation**

Run:

```powershell
pytest tests/test_gui_smoke.py -v
```

Expected: PASS. These tests cover the helpers, `run_matching()` behavior, and actual Tk widget state.

Then launch the app manually:

```powershell
$env:PYTHONPATH='src'
python app.py
```

Manual acceptance:

- The main mode row shows `DNA only`, `RNA only`, and `DNA + RNA`.
- The small second row shows `RNA subtype` with `R`, `MeR`, and `R + MeR`.
- Selecting `DNA only` visibly disables the subtype row.
- Selecting `RNA only` or `DNA + RNA` enables the subtype row.
- No visible label says `Both`.

- [ ] **Step 7: Commit GUI task if baseline is clean**

If there are no unrelated or previous-task uncommitted changes, run:

```powershell
git add src/ms_feature_db_matcher/gui.py tests/test_gui_smoke.py
git commit -m "feat: add compact rna subtype selector"
```

If the DNA Source output changes are still uncommitted, skip this commit and report that the feature was implemented on a dirty baseline.

## Task 4: README and Full Verification

**Files:**
- Modify: `README.md`
- Test: full pytest suite

- [ ] **Step 1: Update README matching mode copy**

In `README.md`, replace the Matching Modes table with:

```markdown
| Mode | Behavior |
|---|---|
| DNA only | Compare dataset m/z against DNA database masses |
| RNA only | Compare dataset m/z against RNA database masses using the selected RNA subtype |
| DNA + RNA | Run DNA first, then RNA using the selected RNA subtype; results are merged with DNA before RNA |
```

Add this section after the Matching Modes table:

```markdown
## RNA Subtype

When a mode includes RNA matching, choose one RNA subtype scope:

| RNA Subtype | Behavior |
|---|---|
| R | Include RNA database hits whose short name does not end with `m` |
| MeR | Include RNA database hits whose short name ends with `m` |
| R + MeR | Include both R and MeR hits |

The default is **R + MeR**, which preserves the previous RNA and DNA + RNA behavior. Dataset `Tags matched` rules still apply; the final RNA result is the intersection of the selected subtype and allowed tags.
```

In the Output section, replace `DNA and Both modes` with `DNA only and DNA + RNA modes`.

- [ ] **Step 2: Run targeted suite**

Run:

```powershell
pytest tests/test_matcher.py tests/test_gui_smoke.py tests/test_end_to_end.py tests/test_exporter.py -v
```

Expected: PASS.

- [ ] **Step 3: Run full suite**

Run:

```powershell
pytest -v
```

Expected: PASS.

- [ ] **Step 4: Commit docs and final verification if baseline is clean**

If there are no unrelated or previous-task uncommitted changes, run:

```powershell
git add README.md
git commit -m "docs: document rna subtype matching"
```

If the DNA Source output changes are still uncommitted, skip this commit and report that the feature was implemented on a dirty baseline.

## Final Acceptance Checklist

- [ ] GUI displays `DNA only`, `RNA only`, and `DNA + RNA`; it does not display `Both`.
- [ ] GUI displays compact RNA subtype buttons: `R`, `MeR`, `R + MeR`.
- [ ] RNA subtype buttons are disabled for `DNA only`.
- [ ] Tk widget smoke test or documented manual GUI validation confirms visible labels and disabled/enabled subtype states.
- [ ] Default subtype is `R + MeR`.
- [ ] `RNA only + R` excludes MeR hits.
- [ ] `RNA only + MeR` excludes R hits.
- [ ] `DNA + RNA + R` keeps DNA and R, excludes MeR.
- [ ] `DNA + RNA + MeR` keeps DNA and MeR, excludes R.
- [ ] `Tags matched` and subtype filtering combine by intersection.
- [ ] RNA-only output still omits `Matched Source`.
- [ ] DNA-containing output still includes `Matched Source`.
- [ ] `pytest -v` passes.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `plan-ceo-review` | Scope & product clarity | 1 | CLEAR | Kept scope focused on two-level selection; no expansion added because user explicitly wants simple UX. |
| Eng Review | `plan-eng-review` | Architecture & tests | 1 | FIXED | Added baseline gate, DNA-only subtype-ignore tests, and real Tk widget smoke/manual validation. |
| DX Review | `plan-devex-review` | Execution clarity | 1 | FIXED | Added preflight failure stop rule and made GUI validation observable instead of relying only on helper tests. |

- **UNRESOLVED:** 0.
- **VERDICT:** CEO + ENG + DX reviewed; blocking plan gaps have been repaired. Ready for implementation once the executor confirms the dirty DNA Source baseline is intentional.
