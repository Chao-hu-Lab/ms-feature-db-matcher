UNIVERSAL_MASS_COLUMNS = {
    "mz",
    "mz/rt",
    "m/z",
    "charged monoisotopic mass",
    "[m+h]+ protonated mass",
    "precursor ion m/z",
}
RNA_EXTRA_MASS_COLUMNS = {"[m+h]+"}
DATASET_FEATURE_COLUMNS = {
    "feature",
    "m/z",
    "precursor ion m/z",
    "m/z,rt",
    "mz,rt",
} | UNIVERSAL_MASS_COLUMNS
NAME_COLUMNS = {"short name", "compound"}
FORMULA_COLUMNS = {"formula", "molecular formula"}
SOURCE_COLUMNS = {"source"}
TAGS_COLUMNS = {"tags matched", "tags"}


def normalize_label(label: object) -> str:
    return str(label).strip().lower()


def find_column(columns, candidates: set[str]) -> object | None:
    for column in columns:
        if normalize_label(column) in candidates:
            return column
    return None


def has_any_column(columns, candidates: set[str]) -> bool:
    return any(normalize_label(column) in candidates for column in columns)
