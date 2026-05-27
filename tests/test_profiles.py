import pandas as pd

from ms_feature_db_matcher.config import DEFAULT_DNA_PATH, DEFAULT_RNA_PATH
from ms_feature_db_matcher.profiles import DatabaseMode, load_database_table


def test_load_default_dna_profile_reads_sheet1_header_row_2() -> None:
    table = load_database_table(DEFAULT_DNA_PATH, DatabaseMode.DNA, use_default_profile=True)

    assert "Short name" in table.columns
    assert "Charged monoisotopic mass" in table.columns


def test_load_default_rna_profile_reads_required_columns() -> None:
    table = load_database_table(DEFAULT_RNA_PATH, DatabaseMode.RNA, use_default_profile=True)

    assert "Short name" in table.columns


def test_detects_replacement_rna_sheet_by_required_columns(tmp_path) -> None:
    path = tmp_path / "rna.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"note": ["ignore"]}).to_excel(writer, sheet_name="Intro", index=False)
        pd.DataFrame(
            {
                "Short name": ["m1A"],
                "[M+H]+": [282.1202],
            }
        ).to_excel(writer, sheet_name="Usable", index=False)

    table = load_database_table(path, DatabaseMode.RNA, use_default_profile=False)

    assert list(table["Short name"]) == ["m1A"]


def test_load_database_table_accepts_mz_column_for_dna(tmp_path) -> None:
    path = tmp_path / "dna.xlsx"
    pd.DataFrame({"Short name": ["dX"], "Mz": [268.1052]}).to_excel(path, index=False)

    table = load_database_table(path, DatabaseMode.DNA, use_default_profile=False)

    assert "Mz" in table.columns
    assert list(table["Short name"]) == ["dX"]


def test_load_database_table_canonicalizes_source_column_for_dna(tmp_path) -> None:
    path = tmp_path / "dna.xlsx"
    pd.DataFrame(
        {
            "Short name": ["dX"],
            "Mz": [268.1052],
            "source": ["DNA DB"],
        }
    ).to_excel(path, index=False)

    table = load_database_table(path, DatabaseMode.DNA, use_default_profile=False)

    assert "Source" in table.columns
    assert list(table["Source"]) == ["DNA DB"]
