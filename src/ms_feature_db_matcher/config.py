import sys
from pathlib import Path


def _base_path() -> Path:
    """Return the project root in dev, or the temp extraction dir under PyInstaller."""
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def _app_dir() -> Path:
    """Directory where the application lives (next to .exe or .app).

    - Windows: folder containing MS Feature DB Matcher.exe
    - macOS .app: folder containing MS Feature DB Matcher.app
    - Dev mode: project root
    """
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        # macOS .app bundle: exe is inside Foo.app/Contents/MacOS/
        if sys.platform == "darwin" and ".app/Contents/MacOS" in str(exe):
            return exe.parents[3]
        return exe.parent
    return Path(__file__).resolve().parents[2]


def database_dir() -> Path:
    return _base_path() / "database"


DEFAULT_DNA_PATH = database_dir() / "datatables.xlsx"
DEFAULT_RNA_PATH = database_dir() / "natural_modifications.xlsx"
DEFAULT_OIL_ADDUCT_PATH = database_dir() / "oil_adduct_database.xlsx"


def project_root() -> Path:
    return _app_dir()


def ensure_output_dir() -> Path:
    output = _app_dir() / "Output"
    output.mkdir(parents=True, exist_ok=True)
    return output
