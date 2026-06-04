# MS Feature DB Matcher

[![CI](https://github.com/Chao-hu-Lab/ms-feature-db-matcher/actions/workflows/ci.yml/badge.svg)](https://github.com/Chao-hu-Lab/ms-feature-db-matcher/actions/workflows/ci.yml)
[![Build Desktop Packages](https://github.com/Chao-hu-Lab/ms-feature-db-matcher/actions/workflows/build.yml/badge.svg)](https://github.com/Chao-hu-Lab/ms-feature-db-matcher/actions/workflows/build.yml)

Standalone Tkinter desktop app for matching LC-MS features against curated DNA, RNA, and oil-adduct databases. The app reads CSV/TSV/Excel feature tables, applies a fixed 20 ppm m/z tolerance rule, and writes the original data back with matched formula, source, and short-name annotations.

Current release target: `v0.3.0`.

## Highlights

- Desktop GUI for DNA-only, RNA-only, and DNA + RNA matching.
- RNA subtype control for `R`, `MeR`, or `R + MeR` without splitting the RNA database file.
- DNA `Matched Source` output when the selected DNA database provides a `Source` column.
- Built-in Standard DB and Oil Adduct DB presets.
- Oil adduct workbook importer for the curated `DNA 總表` / `RNA 總表` workbook format.
- Multi-sheet Excel input support: every sheet with a supported m/z column is matched and exported.

## Download

Pre-built Windows and macOS packages are published from tagged releases:

[GitHub Releases](https://github.com/Chao-hu-Lab/ms-feature-db-matcher/releases)

### macOS First Launch

The app is not code-signed. On first launch, right-click the app and choose **Open**, then confirm the dialog. You can also allow it from **System Settings > Privacy & Security**.

## Quick Start

1. Open **MS Feature DB Matcher**.
2. Choose a dataset file.
3. Pick the database preset:
   - **Standard DB** uses the bundled DNA and RNA default databases.
   - **Oil Adduct DB** uses the bundled oil adduct workbook for both DNA and RNA matching.
4. Choose the matching mode: **DNA only**, **RNA only**, or **DNA + RNA**.
5. If the mode includes RNA, choose `R`, `MeR`, or `R + MeR`.
6. Click **Run Matching**.
7. Open the generated workbook from the `Output/` folder.

## Matching Rule

Each feature m/z is matched against database m/z values with this tolerance:

```text
abs(feature_mz - db_mz) / db_mz * 1e6 <= 20
```

If a feature value contains `/`, only the text before the first `/` is parsed as m/z. For example, `268.1052/17.59(Mz/RT)` is parsed as `268.1052`.

## Dataset Input

Supported file formats:

- `.csv`
- `.tsv`
- `.xlsx`
- `.xls`

The dataset must contain at least one supported m/z column. Matching is case-insensitive.

| Column name | Example |
|---|---|
| `Feature` | `268.1052/17.59(Mz/RT)` |
| `Mz` | `268.1052` |
| `m/z` | `268.1052` |
| `Mz/RT` | `268.1052/17.59` |
| `Precursor Ion m/z` | `268.1052` |
| `Charged monoisotopic mass` | `268.1052` |

For Excel datasets, every worksheet containing a supported m/z column is processed. Worksheets without a supported m/z column are skipped.

## Database Input

The GUI ships with these database presets:

| Preset | DNA database | RNA database |
|---|---|---|
| Standard DB | `database/datatables.xlsx` | `database/natural_modifications.xlsx` |
| Oil Adduct DB | `database/oil_adduct_database.xlsx`, sheet `DNA 總表` | `database/oil_adduct_database.xlsx`, sheet `RNA 總表` |

You can replace either DNA or RNA database with **Browse**. When a custom oil adduct workbook is selected, the loader reads the mode-specific total sheet instead of the first workbook sheet.

### Required Database Columns

Each database must provide a short-name column and a mass column.

Short-name columns:

| Canonical field | Accepted names |
|---|---|
| `Short name` | `Short name`, `Compound` |

Mass columns:

| Accepted mass column | Mode |
|---|---|
| `Mz` | DNA / RNA |
| `m/z` | DNA / RNA |
| `Mz/RT` | DNA / RNA |
| `Precursor Ion m/z` | DNA / RNA |
| `Charged monoisotopic mass` | DNA / RNA |
| `[M+H]+ Protonated Mass` | DNA / RNA |
| `[M+H]+` | RNA |

Optional metadata columns:

| Column | Behavior |
|---|---|
| `Formula` / `Molecular Formula` | Appended as `Matched Formula` when present |
| `Source` | Used for DNA `Matched Source`; ignored for RNA-only output |
| `RNA Subtype` | Controls `R` / `MeR` filtering when present |

## Matching Modes

| Mode | Behavior |
|---|---|
| DNA only | Matches against the selected DNA database |
| RNA only | Matches against the selected RNA database |
| DNA + RNA | Matches DNA first, then RNA; combined output keeps DNA hits before RNA hits |

## RNA Subtype Control

`R` and `MeR` share the same RNA database. The GUI selector controls which subtype is eligible during RNA matching.

| RNA subtype | Behavior |
|---|---|
| `R` | Include RNA hits only |
| `MeR` | Include methylated RNA hits only |
| `R + MeR` | Include both; this is the default |

If the RNA database has an `RNA Subtype` column, values containing `MeR` are treated as MeR and `R` is treated as RNA. Without that column, MeR fallback detection uses matched RNA short names ending in `m`.

In DNA-only mode, the RNA subtype selector is disabled and ignored.

## Output Workbook

The output workbook preserves the original dataset columns and appends match columns at the end.

| Mode | Appended columns |
|---|---|
| DNA only | `Matched Formula`, `Matched Source`, `Matched Short name` |
| DNA + RNA | `Matched Formula`, `Matched Source`, `Matched Short name` |
| RNA only | `Matched Formula`, `Matched Short name` |

Output conventions:

- DNA matches are blue.
- RNA matches are red.
- MeR matches are yellow.
- Multiple hits are joined with `/`.
- `No match` means no database entry passed the tolerance rule.
- `Invalid Feature` means the feature m/z could not be parsed.
- Results are saved to `Output/` next to the app or project root.
- Existing output filenames receive a timestamp suffix.

`Matched Source` is intentionally DNA-only. RNA-only output does not append a source column even if a custom RNA database contains source metadata.

## Oil Adduct Workbook

`database/oil_adduct_database.xlsx` is the built-in Oil Adduct DB preset. It is based on the curated workbook layout with:

- `DNA 總表`
- `RNA 總表`
- source-color metadata that is normalized into `Source Group`

The importer can export reviewable canonical DNA/RNA database files:

```powershell
python -m ms_feature_db_matcher.adduct_importer "C:\Users\user\Downloads\oil DNA RNA adduct_詳細版_V3.0.xlsx" --output-dir database
```

or, after installation:

```powershell
ms-feature-db-import-oil-adducts "C:\Users\user\Downloads\oil DNA RNA adduct_詳細版_V3.0.xlsx" --output-dir database
```

Generated files:

| Output file | Mode |
|---|---|
| `oil_adduct_dna.xlsx` | DNA |
| `oil_adduct_rna.xlsx` | RNA |

The canonical exports normalize `Adduct` / `Chemical` into `Short name`, normalize mass values into `Charged monoisotopic mass`, preserve `Source`, and include oil-adduct metadata such as `Source Group`, `Adduct Category`, `Database Source Sheet`, and `Database Source Row`.

## Development

Create an editable install:

```powershell
python -m pip install -e .[dev]
```

Run the GUI from source:

```powershell
python app.py
```

Run tests:

```powershell
pytest -v
```

The CI-equivalent command is:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
uv run pytest tests/ -v --tb=short -x
```

## Build

Install build dependencies:

```powershell
python -m pip install -e .[build]
```

Build the desktop package:

```powershell
pyinstaller ms_feature_db_matcher.spec
```

The local binary is written to `dist/`.

## Release

Release builds are triggered by version tags matching `v*.*.*`.

```powershell
git tag v0.3.0
git push origin v0.3.0
```

The build workflow packages the desktop app and publishes release artifacts through GitHub Actions.
