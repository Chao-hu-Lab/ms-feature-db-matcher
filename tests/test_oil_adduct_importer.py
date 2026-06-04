from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill

from ms_feature_db_matcher.adduct_importer import build_oil_adduct_tables, export_oil_adduct_databases
from ms_feature_db_matcher.matcher import MatchMode, RnaSubtypeMode, build_match_column
from ms_feature_db_matcher.profiles import DatabaseMode, load_database_table


GREEN_FILL = PatternFill("solid", fgColor="FF92D050")
YELLOW_FILL = PatternFill("solid", fgColor="FFFFFF00")


def _write_oil_workbook(path: Path) -> None:
    workbook = Workbook()
    database = workbook.active
    database.title = "Database"
    database.append(
        [
            "Entry",
            "Name",
            "Short name",
            "Alternative name",
            "Formula",
            "Monoisotopic mass",
            "Charged monoisotopic mass",
            "Charged monoisotopic mass -dR",
            "Source",
        ]
    )
    database.append([1, "Deoxyinosine", "dI", "", "C10H12N4O4", 252.0858, 253.0932, "", "ROS"])
    database["I7"] = "ROS, LPO"
    database["I7"].fill = YELLOW_FILL
    database["R3"] = "LPO"
    database["R3"].fill = YELLOW_FILL
    database["R4"] = "Acetaldehyde"
    database["R4"].fill = GREEN_FILL

    dna = workbook.create_sheet("DNA 總表")
    dna.append([])
    dna.append([])
    dna.append(
        [
            "",
            "Category",
            "Adduct",
            "Structure",
            "Chemical Formula",
            "Extract mass",
            "[M+H]+ Chemical Formula",
            "[M+H]+ Extract mass",
            "Source",
        ]
    )
    dna.append(
        [
            "",
            "2'-dN",
            "N6-Ethyl-dA (N6-Et-dA)",
            "",
            "C12H17N5O3",
            279.1331,
            "C12H18N5O3+",
            280.1404,
            "Alkylation, Acetaldehyde",
        ]
    )
    dna["I4"].fill = GREEN_FILL
    dna.append(
        [
            "",
            "2'-dN",
            "N2-(1-Carboxyethyl)-dG  (N2-(1-Carboxy-Et)-dG)",
            "",
            "C13H17N5O6",
            343.1022,
            "",
            344.1095,
            "ROS, LPO",
        ]
    )
    dna["I5"].fill = YELLOW_FILL
    dna.append([])
    dna.append(["", "Category", "Chemical", "Chemical Formula", "Exact Mass", "m/z", "Structure", "", "FAH"])
    dna.append(["", "Monoadducts", "N2-hm-dG", "C11H15N5O5", 297.1073, 298.1146, "", "", ""])

    rna = workbook.create_sheet("RNA 總表")
    rna.append([])
    rna.append([])
    rna.append(
        [
            "",
            "Category",
            "Adduct",
            "Structure",
            "Chemical Formula",
            "Extract mass",
            "[M+H]+ Chemical Formula",
            "[M+H]+ Extract mass",
            "Source",
        ]
    )
    rna.append(
        [
            "",
            "2'-rN",
            "N6-Ethyl-rA (N6-Et-rA)",
            "",
            "C12H17N5O4",
            295.1281,
            "C12H18N5O4",
            296.1353,
            "Alkylation, Acetaldehyde",
        ]
    )
    rna["I4"].fill = GREEN_FILL
    rna.append([])
    rna.append(["Category", "Chemical", "Chemical Formula", "Exact Mass", "m/z", "Structure"])
    rna.append(["Monoadducts", "N2-hm-MerG", "C12H17N5O6", 327.1179, 328.1252, ""])
    rna.append(["", "rG-CH2-rG", "C21H26N10O10", 578.1833, 579.1906, ""])

    workbook.save(path)


def test_build_oil_adduct_tables_normalizes_source_groups_and_totals(tmp_path) -> None:
    path = tmp_path / "oil.xlsx"
    _write_oil_workbook(path)

    tables = build_oil_adduct_tables(path)

    assert list(tables.dna.columns) == [
        "Short name",
        "Name",
        "Formula",
        "Monoisotopic mass",
        "Charged monoisotopic mass",
        "Source",
        "Source Group",
        "Adduct Category",
        "Database Source Sheet",
        "Database Source Row",
    ]
    dna_hit = tables.dna[tables.dna["Short name"] == "N6-Et-dA"].iloc[0]
    assert dna_hit["Formula"] == "C12H17N5O3"
    assert dna_hit["Charged monoisotopic mass"] == 280.1404
    assert dna_hit["Source"] == "Alkylation, Acetaldehyde"
    assert dna_hit["Source Group"] == "Acetaldehyde"

    nested_short_name = tables.dna[tables.dna["Short name"] == "N2-(1-Carboxy-Et)-dG"].iloc[0]
    assert nested_short_name["Source Group"] == "LPO"

    second_table_hit = tables.dna[tables.dna["Short name"] == "N2-hm-dG"].iloc[0]
    assert second_table_hit["Source"] == "FAH"
    assert second_table_hit["Source Group"] == "FAH"
    assert second_table_hit["Charged monoisotopic mass"] == 298.1146

    assert "RNA Subtype" in tables.rna.columns
    assert tables.rna.loc[tables.rna["Short name"] == "N6-Et-rA", "RNA Subtype"].item() == "R"
    assert tables.rna.loc[tables.rna["Short name"] == "N2-hm-MerG", "RNA Subtype"].item() == "MeR"
    assert tables.rna.loc[tables.rna["Short name"] == "rG-CH2-rG", "RNA Subtype"].item() == "R"


def test_load_database_table_uses_mode_specific_oil_workbook_sheets(tmp_path) -> None:
    path = tmp_path / "oil.xlsx"
    _write_oil_workbook(path)

    dna = load_database_table(path, DatabaseMode.DNA, use_default_profile=False)
    rna = load_database_table(path, DatabaseMode.RNA, use_default_profile=False)

    assert list(dna["Short name"]) == ["N6-Et-dA", "N2-(1-Carboxy-Et)-dG", "N2-hm-dG"]
    assert list(rna["Short name"]) == ["N6-Et-rA", "N2-hm-MerG", "rG-CH2-rG"]
    assert "dI" not in set(rna["Short name"])


def test_export_oil_adduct_databases_writes_canonical_workbooks(tmp_path) -> None:
    source = tmp_path / "oil.xlsx"
    output_dir = tmp_path / "out"
    _write_oil_workbook(source)

    dna_path, rna_path = export_oil_adduct_databases(source, output_dir)

    assert dna_path.name == "oil_adduct_dna.xlsx"
    assert rna_path.name == "oil_adduct_rna.xlsx"
    dna = pd.read_excel(dna_path)
    rna = pd.read_excel(rna_path)
    assert list(dna["Short name"]) == ["N6-Et-dA", "N2-(1-Carboxy-Et)-dG", "N2-hm-dG"]
    assert list(rna["RNA Subtype"]) == ["R", "MeR", "R"]


def test_matcher_uses_rna_subtype_column_when_names_do_not_end_with_m() -> None:
    dataset = pd.DataFrame({"Feature": [328.1252]})
    rna = pd.DataFrame(
        {
            "Short name": ["N2-hm-rG", "N2-hm-MerG"],
            "[M+H]+": [328.1252, 328.1252],
            "Formula": ["C11H15N5O6", "C12H17N5O6"],
            "RNA Subtype": ["R", "MeR"],
        }
    )
    dna = pd.DataFrame({"Short name": [], "Charged monoisotopic mass": []})

    r_only = build_match_column(dataset, dna, rna, MatchMode.RNA, RnaSubtypeMode.R_ONLY)
    mer_only = build_match_column(dataset, dna, rna, MatchMode.RNA, RnaSubtypeMode.MER_ONLY)

    assert r_only[0].text == "N2-hm-rG"
    assert r_only[0].rna_names == ["N2-hm-rG"]
    assert mer_only[0].text == "N2-hm-MerG"
    assert mer_only[0].mer_names == ["N2-hm-MerG"]
