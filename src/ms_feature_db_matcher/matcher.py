from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

from .column_rules import (
    DATASET_FEATURE_COLUMNS,
    FORMULA_COLUMNS,
    NAME_COLUMNS,
    RNA_EXTRA_MASS_COLUMNS,
    SOURCE_COLUMNS,
    TAGS_COLUMNS,
    UNIVERSAL_MASS_COLUMNS,
    find_column,
)


class MatchMode(str, Enum):
    DNA = "DNA"
    RNA = "RNA"
    BOTH = "Both"


class RnaSubtypeMode(str, Enum):
    R_ONLY = "R"
    MER_ONLY = "MeR"
    R_AND_MER = "R + MeR"


@dataclass(frozen=True)
class MatchCell:
    text: str
    formula_text: str
    source_text: str = ""
    dna_names: list[str] = field(default_factory=list)
    rna_names: list[str] = field(default_factory=list)
    mer_names: list[str] = field(default_factory=list)
    dna_formulas: list[str] = field(default_factory=list)
    rna_formulas: list[str] = field(default_factory=list)
    mer_formulas: list[str] = field(default_factory=list)
    dna_sources: list[str] = field(default_factory=list)


def parse_mz_value(value: object) -> float:
    text = str(value).strip()
    if not text:
        raise ValueError("Missing m/z value")
    value = text.split("/", 1)[0].strip()
    return float(value)


def parse_feature_mz(feature: object) -> float:
    return parse_mz_value(feature)


def ppm_difference(feature_mz: float, db_mz: float) -> float:
    return abs(feature_mz - db_mz) / db_mz * 1e6


def _clean_optional_text(value: object) -> str:
    text = str(value).strip()
    return text if text and text.lower() != "nan" else ""


def _collect_hits(
    table: pd.DataFrame,
    mass_candidates: set[str],
    feature_mz: float,
    *,
    collect_source: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    name_col = find_column(table.columns, NAME_COLUMNS)
    mass_col = find_column(table.columns, mass_candidates)
    if name_col is None or mass_col is None:
        return [], [], []
    formula_col = find_column(table.columns, FORMULA_COLUMNS)
    source_col = find_column(table.columns, SOURCE_COLUMNS) if collect_source else None
    names: list[str] = []
    formulas: list[str] = []
    sources: list[str] = []
    for _, row in table.iterrows():
        try:
            if ppm_difference(feature_mz, parse_mz_value(row[mass_col])) <= 20:
                names.append(str(row[name_col]))
                if formula_col is not None:
                    formulas.append(_clean_optional_text(row[formula_col]))
                else:
                    formulas.append("")
                if source_col is not None:
                    sources.append(_clean_optional_text(row[source_col]))
                elif collect_source:
                    sources.append("")
        except (TypeError, ValueError, ZeroDivisionError):
            continue
    return names, formulas, sources


def _parse_allowed_tags(raw_tag: object) -> set[str]:
    if raw_tag is None or (isinstance(raw_tag, float) and pd.isna(raw_tag)):
        return {"2", "3"}
    return {_normalize_tag_token(t) for t in str(raw_tag).split(";")}


def _normalize_tag_token(token: str) -> str:
    text = token.strip()
    try:
        value = float(text)
    except ValueError:
        return text
    return str(int(value)) if value.is_integer() else text


def build_match_column(
    dataset: pd.DataFrame,
    dna: pd.DataFrame,
    rna: pd.DataFrame,
    mode: MatchMode,
    rna_subtype_mode: RnaSubtypeMode = RnaSubtypeMode.R_AND_MER,
) -> list[MatchCell]:
    feature_col = find_column(dataset.columns, DATASET_FEATURE_COLUMNS)
    if feature_col is None:
        found_str = ", ".join(repr(c) for c in list(dataset.columns)[:10])
        raise ValueError(
            "Dataset 缺少可辨識的 m/z 欄位。\n"
            "  支援的欄位名稱：Feature, Mz, Mz/RT, m/z, Precursor Ion m/z, Charged monoisotopic mass 等\n"
            f"  Dataset 中實際找到的欄位：{found_str}\n"
            "  常見原因：欄位名稱使用逗號（如 'm/z,RT'）而非斜線（'Mz/RT'）、"
            "或第一列為說明列而非標題列。"
        )
    tags_col = find_column(dataset.columns, TAGS_COLUMNS)
    tag_values: list[object] = (
        list(dataset[tags_col]) if tags_col is not None else [None] * len(dataset)
    )
    results: list[MatchCell] = []
    for feature, raw_tag in zip(dataset[feature_col], tag_values):
        try:
            feature_mz = parse_feature_mz(feature)
        except (TypeError, ValueError):
            results.append(MatchCell(text="Invalid Feature", formula_text=""))
            continue

        dna_names: list[str] = []
        rna_names: list[str] = []
        mer_names: list[str] = []
        dna_formulas: list[str] = []
        rna_formulas: list[str] = []
        mer_formulas: list[str] = []
        dna_sources: list[str] = []
        if mode in (MatchMode.DNA, MatchMode.BOTH):
            dna_names, dna_formulas, dna_sources = _collect_hits(
                dna, UNIVERSAL_MASS_COLUMNS, feature_mz, collect_source=True
            )
        if mode in (MatchMode.RNA, MatchMode.BOTH):
            all_rna_names, all_rna_formulas, _ = _collect_hits(
                rna, UNIVERSAL_MASS_COLUMNS | RNA_EXTRA_MASS_COLUMNS, feature_mz
            )
            for name, formula in zip(all_rna_names, all_rna_formulas):
                if name.endswith("m"):
                    mer_names.append(name)
                    mer_formulas.append(formula)
                else:
                    rna_names.append(name)
                    rna_formulas.append(formula)

        allowed_tags = _parse_allowed_tags(raw_tag)
        if "2" not in allowed_tags:
            rna_names, rna_formulas = [], []
        if "3" not in allowed_tags:
            mer_names, mer_formulas = [], []
        if rna_subtype_mode == RnaSubtypeMode.R_ONLY:
            mer_names, mer_formulas = [], []
        elif rna_subtype_mode == RnaSubtypeMode.MER_ONLY:
            rna_names, rna_formulas = [], []

        all_names = dna_names + rna_names + mer_names
        all_formulas = dna_formulas + rna_formulas + mer_formulas
        text = "/".join(all_names) if all_names else "No match"
        non_empty = [f for f in all_formulas if f]
        formula_text = "/".join(non_empty) if non_empty else ""
        source_non_empty = [s for s in dna_sources if s]
        source_text = "/".join(source_non_empty) if source_non_empty else ""
        results.append(
            MatchCell(
                text=text,
                formula_text=formula_text,
                source_text=source_text,
                dna_names=dna_names,
                rna_names=rna_names,
                mer_names=mer_names,
                dna_formulas=dna_formulas,
                rna_formulas=rna_formulas,
                mer_formulas=mer_formulas,
                dna_sources=dna_sources,
            )
        )

    return results
