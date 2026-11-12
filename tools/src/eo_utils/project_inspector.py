import os
import ast
import sys
import pkg_resources
from pathlib import Path
from importlib.metadata import packages_distributions

# -------------------------
# Functions for imports
# -------------------------
def get_imports_from_file(file_path):
    """Return top-level module names imported in a Python file."""
    with open(file_path, "r", encoding="utf-8") as f:
        node = ast.parse(f.read(), filename=file_path.name)
    imports = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for alias in n.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                imports.add(n.module.split(".")[0])
    return imports


def scan_project_for_imports(root_path, exclude_dirs=None):
    """Scan all .py files recursively and collect imported packages."""
    if exclude_dirs is None:
        exclude_dirs = {'.venv', 'env', 'venv'}

    all_imports = set()
    root_path = Path(root_path)
    local_modules = set()

    def is_excluded(path):
        return any(part in exclude_dirs or part.startswith('.') for part in path.parts)

    for py_file in root_path.rglob("*.py"):
        if is_excluded(py_file.relative_to(root_path)):
            continue
        local_modules.add(py_file.stem)

    for entry in root_path.iterdir():
        if entry.is_dir() and not is_excluded(entry.relative_to(root_path)):
            local_modules.add(entry.name)

    for package_dir in root_path.rglob("*"):
        if not package_dir.is_dir():
            continue
        if is_excluded(package_dir.relative_to(root_path)):
            continue
        if (package_dir / "__init__.py").exists():
            local_modules.add(package_dir.name)

    stdlib_modules = set(getattr(sys, "stdlib_module_names", set()))
    stdlib_modules.update(sys.builtin_module_names)

    for py_file in root_path.rglob("*.py"):
        if is_excluded(py_file.relative_to(root_path)):
            continue  # skip virtualenv or other excluded dirs
        all_imports.update(get_imports_from_file(py_file))
    third_party_imports = {
        module for module in all_imports
        if module not in stdlib_modules and module not in local_modules
    }
    return sorted(third_party_imports)


def distribution_name_for_import(import_name):
    """Return the installed distribution name for an import, when available."""
    distributions = packages_distributions().get(import_name)
    if distributions:
        return distributions[0]
    return import_name


def get_package_version(pkg_name):
    """Return the installed version of a package if available."""
    distribution_name = distribution_name_for_import(pkg_name)
    try:
        dist = pkg_resources.get_distribution(distribution_name)
        return distribution_name, dist.version
    except (pkg_resources.DistributionNotFound, pkg_resources.RequirementParseError):
        return pkg_name, None


def update_requirements(imports, requirements_file):
    """Update requirements.txt with exact versions from the venv."""
    existing = {}
    req_file = Path(requirements_file)
    if req_file.exists():
        with open(req_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and "==" in line:
                    pkg, ver = line.split("==")
                    existing[pkg] = ver
                elif line:
                    existing[line] = None

    new_lines = []
    for pkg in imports:
        distribution_name, ver = get_package_version(pkg)
        if pkg in existing or distribution_name in existing:
            continue  # already listed
        if ver:
            new_lines.append(f"{distribution_name}=={ver}")
        else:
            new_lines.append(pkg)

    if new_lines:
        with open(req_file, "a", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")
        print(f"Added to {requirements_file}: {new_lines}")
    else:
        print("No new packages to add to requirements.txt.")

def update_readme(root_path, readme_file, project_name="EO Utils", description=None,
                  exclude_dirs=None, max_depth=2, max_entries=20):
    """Refresh a bounded directory map while preserving manually written guidance.

    Only the block between the generated markers is replaced. Files are omitted
    from the map; nested data filenames do not belong in the repository README.
    """
    if max_depth < 1 or max_entries < 1:
        raise ValueError("max_depth and max_entries must be positive")
    if exclude_dirs is None:
        exclude_dirs = {
            'env', 'venv', '__pycache__', 'data', 'runtime_downloads',
            'audit_results', 'deliveries', 'resources_usage_prod',
            'downloads', 'event_downloads', 'inputs', 'outputs', 'reports',
            'prod', 'uat', 'legacy_v0_code', 'Old', 'validation_samples',
            'V0_tiffs', 'V1_tiffs', 'local_satpy_venv',
        }
    root_path = Path(root_path)
    readme_file = Path(readme_file)
    start = "<!-- BEGIN GENERATED DIRECTORY MAP -->"
    end = "<!-- END GENERATED DIRECTORY MAP -->"
    existing = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""
    if existing.count(start) != existing.count(end) or existing.count(start) > 1:
        raise ValueError("README directory map markers must occur as one matching pair")
    if start in existing and existing.index(start) > existing.index(end):
        raise ValueError("README directory map markers are out of order")

    lines = [start, "## Directory map", "", "Directories only; data and hidden folders omitted.", "", "```text"]

    def build_tree(path, depth=1):
        entries = sorted(
            (p for p in path.iterdir()
             if not p.name.startswith('.') and p.name not in exclude_dirs
             and not p.is_symlink() and p.is_dir()),
            key=lambda p: p.name,
        )
        for entry in entries[:max_entries]:
            lines.append("  " * (depth - 1) + entry.name + "/")
            if depth < max_depth:
                build_tree(entry, depth + 1)
        if len(entries) > max_entries:
            lines.append("  " * (depth - 1) + f"... {len(entries) - max_entries} more directories")

    build_tree(root_path)
    lines.extend(["```", end])
    block = "\n".join(lines)
    if start in existing:
        before, rest = existing.split(start, 1)
        _, after = rest.split(end, 1)
        result = before + block + after
    else:
        if not existing:
            existing = f"# {project_name}\n\n{description or 'Earth Observation utilities and workflows.'}\n"
        result = existing.rstrip() + "\n\n" + block + "\n"
    readme_file.write_text(result, encoding="utf-8")
    print(f"Updated bounded directory map in {readme_file}")
