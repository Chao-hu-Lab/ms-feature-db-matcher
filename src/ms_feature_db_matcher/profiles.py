from enum import Enum
from pathlib import Path

import pandas as pd

from .column_rules import FORMULA_COLUMNS, NAME_COLUMNS, RNA_EXTRA_MASS_COLUMNS, UNIVERSAL_MASS_COLUMNS, normalize_label


class DatabaseMode(str, Enum):
    DNA = "DNA"
    RNA = "RNA"


_DNA_REQUIRED: list[set[str]] = [NAME_COLUMNS, UNIVERSAL_MASS_COLUMNS]
_RNA_REQUIRED: list[set[str]] = [NAME_COLUMNS, UNIVERSAL_MASS_COLUMNS | RNA_EXTRA_MASS_COLUMNS]

_SHARED_CANONICAL: dict[str, str] = {
    "short name": "Short name",
    "compound": "Short name",
    "mz": "Mz",
    "mz/rt": "Mz/RT",
    "m/z": "m/z",
    "charged monoisotopic mass": "Charged monoisotopic mass",
    "[m+h]+ protonated mass": "[M+H]+ Protonated Mass",
    "precursor ion m/z": "Precursor Ion m/z",
    "formula": "Formula",
    "molecular formula": "Formula",
    "source": "Source",
}

_DNA_CANONICAL: dict[str, str] = {**_SHARED_CANONICAL}
_RNA_CANONICAL: dict[str, str] = {**_SHARED_CANONICAL, "[m+h]+": "[M+H]+"}


def _has_required_columns(columns, groups: list[set[str]]) -> bool:
    col_lower = {normalize_label(column) for column in columns}
    return all(bool(group & col_lower) for group in groups)


def _normalize_columns(table: pd.DataFrame, mode: DatabaseMode) -> pd.DataFrame:
    canonical = {DatabaseMode.DNA: _DNA_CANONICAL, DatabaseMode.RNA: _RNA_CANONICAL}[mode]
    rename = {
        column: canonical[normalize_label(column)]
        for column in table.columns
        if normalize_label(column) in canonical
    }
    return table.rename(columns=rename) if rename else table


def _find_matching_sheet(path: Path, mode: DatabaseMode, headers: tuple[int, ...]) -> pd.DataFrame | None:
    groups = {DatabaseMode.DNA: _DNA_REQUIRED, DatabaseMode.RNA: _RNA_REQUIRED}[mode]
    workbook = pd.ExcelFile(path)
    for header in headers:
        for sheet in workbook.sheet_names:
            table = pd.read_excel(path, sheet_name=sheet, header=header)
            if _has_required_columns(table.columns, groups):
                return _normalize_columns(table, mode)
    return None


def load_database_table(path: Path, mode: DatabaseMode, use_default_profile: bool) -> pd.DataFrame:
    if use_default_profile and mode == DatabaseMode.DNA:
        table = pd.read_excel(path, sheet_name="Sheet1", header=1)
        return _normalize_columns(table, mode)
    if use_default_profile and mode == DatabaseMode.RNA:
        table = _find_matching_sheet(path, mode, headers=(1,))
        if table is not None:
            return table

    table = _find_matching_sheet(path, mode, headers=(0, 1))
    if table is not None:
        return table

    groups = {DatabaseMode.DNA: _DNA_REQUIRED, DatabaseMode.RNA: _RNA_REQUIRED}[mode]
    raise ValueError(f"No worksheet contains required columns: {[sorted(g) for g in groups]}")
