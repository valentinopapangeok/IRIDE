from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from eo_utils.project_inspector import scan_project_for_imports, update_requirements, update_readme

REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
README_FILE = PROJECT_ROOT / "README.md"

if __name__ == "__main__":
    imports = scan_project_for_imports(PROJECT_ROOT)
    update_requirements(imports, REQUIREMENTS_FILE)
    update_readme(PROJECT_ROOT, README_FILE)
