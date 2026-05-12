#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "coverage>=7.0",
# ]
# ///

import contextlib as __stickytape_contextlib


@__stickytape_contextlib.contextmanager
def __stickytape_temporary_dir():
    import shutil
    import tempfile
    dir_path = tempfile.mkdtemp()
    try:
        yield dir_path
    finally:
        shutil.rmtree(dir_path)

with __stickytape_temporary_dir() as __stickytape_working_dir:
    def __stickytape_write_module(path, contents):
        import os
        import os.path

        def make_package(path):
            parts = path.split("/")
            partial_path = __stickytape_working_dir
            for part in parts:
                partial_path = os.path.join(partial_path, part)
                if not os.path.exists(partial_path):
                    os.mkdir(partial_path)
                    with open(os.path.join(partial_path, "__init__.py"), "wb") as f:
                        f.write(b"\n")

        make_package(os.path.dirname(path))

        full_path = os.path.join(__stickytape_working_dir, path)
        with open(full_path, "wb") as module_file:
            module_file.write(contents)

    import sys as __stickytape_sys
    __stickytape_sys.path.insert(0, __stickytape_working_dir)

    __stickytape_write_module('src/crap4python/__init__.py', b'"""crap4python - CRAP metric tool for Python projects."""\n')
    __stickytape_write_module('src/crap4python/crap_analyzer.py', b'"""CRAP analyzer - combines parsing, coverage, and scoring."""\n\nfrom pathlib import Path\n\nfrom .python_method_parser import parse as parse_methods\nfrom .crap_score import calculate as calculate_crap\nfrom .method_metrics import MethodMetrics\nfrom .coverage_parser import parse_coverage_xml\n\n\ndef analyze(\n    project_root: Path,\n    files: list[Path],\n    coverage_xml: Path | None = None,\n) -> list[MethodMetrics]:\n    """Analyze Python files and return method metrics."""\n    coverage_map = {}\n    if coverage_xml and coverage_xml.exists():\n        coverage_map = parse_coverage_xml(coverage_xml)\n\n    metrics = []\n    for file_path in files:\n        if not file_path.exists():\n            continue\n\n        source = file_path.read_text()\n        module_name = _module_name_from_path(file_path, project_root)\n        methods = parse_methods(source)\n\n        for method in methods:\n            coverage = _lookup_coverage(\n                coverage_map, module_name, method.start_line, method.end_line\n            )\n            crap = calculate_crap(method.complexity, coverage)\n            metrics.append(\n                MethodMetrics(\n                    method_name=method.name,\n                    class_name=module_name,\n                    complexity=method.complexity,\n                    coverage_percent=coverage,\n                    crap_score=crap,\n                )\n            )\n\n    return metrics\n\n\ndef _module_name_from_path(file_path: Path, project_root: Path) -> str:\n    """Derive a module name from a file path."""\n    try:\n        rel = file_path.resolve().relative_to(project_root.resolve())\n        name = str(rel).replace("/", ".").replace("\\\\", ".").removesuffix(".py")\n        # Strip leading \'src.\' to match coverage.py module names\n        if name.startswith("src."):\n            name = name[4:]\n        return name\n    except ValueError:\n        return file_path.stem\n\n\ndef _lookup_coverage(\n    coverage_map: dict[str, dict[int, bool]],\n    module_name: str,\n    start_line: int,\n    end_line: int,\n) -> float | None:\n    """Look up coverage for a method by checking line-level coverage in its range."""\n    candidate_names = [module_name]\n\n    # Some coverage.xml configurations use a source root (for example `app/`)\n    # and emit class filenames relative to that root, e.g. `config.py` instead\n    # of `app/config.py`. In that case our module name (`app.config`) should\n    # fall back to progressively shorter dotted names (`config`).\n    parts = module_name.split(".")\n    for i in range(1, len(parts)):\n        candidate_names.append(".".join(parts[i:]))\n\n    lines = None\n    for candidate in candidate_names:\n        if candidate in coverage_map:\n            lines = coverage_map[candidate]\n            break\n\n    if lines is None:\n        return None\n\n    # Count covered vs total lines in the method\'s range\n    total = 0\n    covered = 0\n    for line_num in range(start_line, end_line + 1):\n        if line_num in lines:\n            total += 1\n            if lines[line_num]:\n                covered += 1\n\n    if total == 0:\n        return None\n\n    return (covered / total) * 100.0\n')
    __stickytape_write_module('src/crap4python/python_method_parser.py', b'"""Python method parser using the ast module."""\n\nimport ast\nfrom dataclasses import dataclass\n\n\n@dataclass\nclass MethodDescriptor:\n    name: str\n    start_line: int\n    end_line: int\n    complexity: int\n\n\ndef parse(source: str) -> list[MethodDescriptor]:\n    """Parse Python source and extract function/method descriptors with complexity."""\n    tree = ast.parse(source)\n    methods = []\n    for node in ast.walk(tree):\n        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):\n            # Skip methods inside classes that are nested (anonymous-like)\n            complexity = _count_complexity(node)\n            methods.append(\n                MethodDescriptor(\n                    name=node.name,\n                    start_line=node.lineno,\n                    end_line=node.end_lineno or node.lineno,\n                    complexity=complexity,\n                )\n            )\n    return methods\n\n\ndef _count_complexity(func_node: ast.AST) -> int:\n    """Count cyclomatic complexity of a function node.\n\n    Base complexity is 1. Each decision point adds 1:\n    - if, elif\n    - for, while\n    - except\n    - ternary (IfExp)\n    - and, or (BoolOp)\n    - assert\n    """\n    complexity = 1\n    for node in ast.walk(func_node):\n        if isinstance(node, ast.If):\n            complexity += 1\n        elif isinstance(node, (ast.For, ast.AsyncFor)):\n            complexity += 1\n        elif isinstance(node, (ast.While,)):\n            complexity += 1\n        elif isinstance(node, ast.ExceptHandler):\n            complexity += 1\n        elif isinstance(node, ast.IfExp):\n            complexity += 1\n        elif isinstance(node, ast.BoolOp):\n            # Each \'and\'/\'or\' adds (number of values - 1)\n            complexity += len(node.values) - 1\n        elif isinstance(node, ast.Assert):\n            complexity += 1\n    return complexity\n')
    __stickytape_write_module('src/crap4python/crap_score.py', b'"""CRAP score calculation."""\n\n\ndef calculate(complexity: int, coverage_percent: float | None) -> float | None:\n    """Calculate CRAP score.\n\n    CRAP = CC^2 * (1 - coverage)^3 + CC\n\n    Where coverage is in range 0.0..1.0 (fraction, not percentage).\n    Returns None if coverage is None.\n    """\n    if coverage_percent is None:\n        return None\n\n    cc = float(complexity)\n    # coverage_percent is 0-100, convert to 0-1 fraction\n    coverage_fraction = coverage_percent / 100.0\n    uncovered = 1.0 - coverage_fraction\n    return (cc * cc * uncovered * uncovered * uncovered) + cc\n')
    __stickytape_write_module('src/crap4python/method_metrics.py', b'"""Data class for method metrics."""\n\nfrom dataclasses import dataclass\n\n\n@dataclass\nclass MethodMetrics:\n    method_name: str\n    class_name: str  # For Python, this is the module/file name\n    complexity: int\n    coverage_percent: float | None\n    crap_score: float | None\n')
    __stickytape_write_module('src/crap4python/coverage_parser.py', b'"""Coverage XML parser for coverage.py output."""\n\nimport xml.etree.ElementTree as ET\nfrom pathlib import Path\n\nfrom .coverage_data import CoverageData\n\n\ndef parse_coverage_xml(cobertura_xml_path: Path) -> dict[str, dict[int, bool]]:\n    """Parse coverage.py Cobertura-style XML into a line-level coverage map.\n\n    Returns a dict mapping "module_name" -> {line_number: is_covered}.\n    """\n    if not cobertura_xml_path.exists():\n        return {}\n\n    tree = ET.parse(cobertura_xml_path)\n    root = tree.getroot()\n\n    coverage = {}\n    for cls_elem in root.findall(".//class"):\n        filename = cls_elem.get("filename", "")\n        # Derive module name from filename\n        module_name = _module_from_filename(filename)\n\n        lines = {}\n        for line_elem in cls_elem.findall("lines/line"):\n            line_num = int(line_elem.get("number", "0"))\n            hits = int(line_elem.get("hits", "0"))\n            lines[line_num] = hits > 0\n\n        if lines:\n            coverage[module_name] = lines\n\n    return coverage\n\n\ndef _module_from_filename(filename: str) -> str:\n    """Convert a filename path to a module name."""\n    # Remove .py extension\n    name = filename\n    if name.endswith(".py"):\n        name = name[:-3]\n    # Convert path separators to dots\n    name = name.replace("/", ".").replace("\\\\", ".")\n    # Remove leading src. if present\n    if name.startswith("src."):\n        name = name[4:]\n    return name\n')
    __stickytape_write_module('src/crap4python/coverage_data.py', b'"""Coverage data representation."""\n\nfrom dataclasses import dataclass\n\n\n@dataclass\nclass CoverageData:\n    missed: int\n    covered: int\n\n    @property\n    def coverage_percent(self) -> float:\n        total = self.missed + self.covered\n        if total == 0:\n            return 0.0\n        return (self.covered * 100.0) / total\n')
    __stickytape_write_module('src/crap4python/coverage_runner.py', b'"""Coverage runner for Python projects using coverage.py."""\n\nimport os\nimport shlex\nimport subprocess\nimport shutil\nfrom pathlib import Path\n\n\ndef generate_coverage(project_root: Path, debug: bool = False, err=None) -> None:\n    """Run coverage.py tests and generate XML report.\n\n    Deletes stale coverage artifacts first.\n    """\n    def log(message: str) -> None:\n        if debug and err is not None:\n            err.write(f"[debug] {message}\\n")\n\n    # Delete stale artifacts\n    _delete_if_exists(project_root / "htmlcov")\n    _delete_if_exists(project_root / ".coverage")\n    _delete_if_exists(project_root / "coverage.xml")\n\n    coverage_prefix = _coverage_command_prefix()\n    log(f"Using coverage command prefix: {\' \'.join(coverage_prefix)}")\n\n    # Run tests with coverage.\n    # Prefer pytest, fall back to unittest discovery.\n    test_commands = [\n        [*coverage_prefix, "run", "-m", "pytest"],\n        [*coverage_prefix, "run", "-m", "unittest", "discover"],\n    ]\n\n    test_success = False\n    for command in test_commands:\n        log(f"Running test command for coverage: {\' \'.join(command)}")\n        result = subprocess.run(\n            command,\n            cwd=str(project_root),\n            capture_output=True,\n            text=True,\n        )\n        if result.returncode == 0:\n            test_success = True\n            log("Test command succeeded")\n            break\n        stderr_text = getattr(result, "stderr", "") or ""\n        log(\n            f"Test command failed (exit {result.returncode}): {stderr_text.strip()[:300]}"\n        )\n\n    if not test_success:\n        raise RuntimeError("All coverage test commands failed")\n\n    # If test tooling already produced coverage.xml (e.g., pytest-cov addopts), use it.\n    coverage_xml_path = project_root / "coverage.xml"\n    if coverage_xml_path.exists():\n        log("coverage.xml already exists after test run; using existing report")\n        return\n\n    # Generate XML report\n    xml_result = subprocess.run(\n        [*coverage_prefix, "xml", "-o", "coverage.xml"],\n        cwd=str(project_root),\n        capture_output=True,\n        text=True,\n    )\n    if xml_result.returncode != 0:\n        # Some runners/plugins may generate coverage.xml during test execution but\n        # still leave no data for a subsequent `coverage xml` invocation.\n        if coverage_xml_path.exists():\n            log(\n                "coverage xml command failed but coverage.xml exists; continuing with existing report"\n            )\n            return\n        raise RuntimeError(\n            f"coverage xml failed (exit {xml_result.returncode}): {xml_result.stderr.strip()[:300]}"\n        )\n    if not coverage_xml_path.exists():\n        raise RuntimeError("coverage xml command succeeded but coverage.xml not found")\n\n    log("Generated coverage.xml successfully")\n\n\ndef _delete_if_exists(path: Path) -> None:\n    """Delete a file or directory if it exists."""\n    if not path.exists():\n        return\n    if path.is_dir():\n        shutil.rmtree(path)\n    else:\n        path.unlink()\n\n\ndef _coverage_command_prefix() -> list[str]:\n    """Choose the command prefix used to invoke coverage.\n\n    Resolution order:\n    1) CRAP4PYTHON_COVERAGE_PREFIX env var (example: "uv run coverage")\n    2) uv-managed coverage ("uv run coverage")\n    3) system coverage executable ("coverage")\n    """\n    configured = os.getenv("CRAP4PYTHON_COVERAGE_PREFIX", "").strip()\n    if configured:\n        prefix = shlex.split(configured)\n        if not prefix:\n            raise RuntimeError("CRAP4PYTHON_COVERAGE_PREFIX is empty after parsing")\n        return prefix\n\n    if shutil.which("uv"):\n        return ["uv", "run", "coverage"]\n\n    if shutil.which("coverage"):\n        return ["coverage"]\n\n    raise RuntimeError(\n        "coverage.py is not available. Install coverage or use uv, "\n        "or set CRAP4PYTHON_COVERAGE_PREFIX."\n    )\n')
    if __name__ == '__main__' and __package__ is None:
        __package__ = 'src.crap4python'
    
    """crap4python CLI application."""
    
    import ast
    import os
    import sys
    from dataclasses import dataclass
    from enum import Enum
    from pathlib import Path
    
    
    VERSION = "0.1.0"
    DEFAULT_THRESHOLD = 8.0
    
    
    class CliMode(Enum):
        HELP = "help"
        ALL_SRC = "all_src"
        CHANGED_SRC = "changed_src"
        EXPLICIT_FILES = "explicit_files"
    
    
    @dataclass
    class CliArguments:
        mode: CliMode
        file_args: list[str]
    
    
    @dataclass
    class MethodMetrics:
        method_name: str
        class_name: str
        complexity: int
        coverage_percent: float | None
        crap_score: float | None
    
    
    def usage() -> str:
        return """Usage:
      crap4python            Analyze all Python files under the current directory recursively
      crap4python --changed Analyze changed Python files (excluding test files)
      crap4python <path...>  Analyze files, or for directory args analyze <dir> recursively
      crap4python --debug    Print debug diagnostics to stderr
      crap4python --help      Print this help message"""
    
    
    KNOWN_FLAGS = {"--help", "--changed", "--debug"}
    
    
    def parse_arguments(args: list[str]) -> CliArguments:
        if not args:
            return CliArguments(CliMode.ALL_SRC, [])
    
        if "--help" in args:
            return CliArguments(CliMode.HELP, [])
    
        # Reject unknown flags
        for arg in args:
            if arg.startswith("--") and arg not in KNOWN_FLAGS:
                raise ValueError(f"Unknown option: {arg}")
    
        changed = "--changed" in args
        file_args = [arg for arg in args if not arg.startswith("--")]
    
        if changed and file_args:
            raise ValueError("--changed cannot be combined with file arguments")
    
        if changed:
            return CliArguments(CliMode.CHANGED_SRC, [])
    
        if file_args:
            return CliArguments(CliMode.EXPLICIT_FILES, file_args)
    
        return CliArguments(CliMode.ALL_SRC, [])
    
    
    EXCLUDED_SCAN_DIRS = {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "dist",
        "build",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
    }
    
    
    def _is_test_python_file(path: Path) -> bool:
        """Return True when path looks like a Python test file."""
        name = path.name
        if not name.endswith(".py"):
            return False
    
        if name.startswith("test_") or name.endswith("_test.py"):
            return True
    
        for part in path.parts:
            lowered = part.lower()
            if lowered in {"test", "tests"}:
                return True
            if lowered.startswith("test_"):
                return True
            if lowered.endswith("_test") or lowered.endswith("_tests"):
                return True
    
        return False
    
    
    def find_python_files_recursively(root: Path) -> list[Path]:
        """Find all non-test .py files under root recursively."""
        if not root.exists() or not root.is_dir():
            return []
    
        files = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_SCAN_DIRS]
            current_dir = Path(dirpath)
    
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
    
                file_path = current_dir / filename
                relative = file_path.relative_to(root)
                if _is_test_python_file(relative):
                    continue
    
                files.append(file_path)
    
        files.sort()
        return files
    
    
    def find_changed_python_files(root: Path) -> list[Path]:
        """Find changed non-test .py files under root."""
        import subprocess
    
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )
        except Exception:
            return find_python_files_recursively(root)
    
        files = []
        for line in result.stdout.splitlines():
            if not line:
                continue
            # Format: XY filename (XY is status like M, A, ??, etc.)
            if len(line) < 3:
                continue
            filename = line[3:]  # Skip status characters
            file_path = root / filename
            if file_path.suffix == ".py" and file_path.exists():
                try:
                    relative = file_path.relative_to(root)
                except ValueError:
                    continue
    
                if _is_test_python_file(relative):
                    continue
    
                files.append(file_path)
    
        files.sort()
        return files
    
    
    def explicit_files(root: Path, args: list[str]) -> list[Path]:
        """Expand explicit file/directory arguments."""
        files = set()
        for arg in args:
            path = root / arg
            if path.is_dir():
                files.update(find_python_files_recursively(path))
            elif path.is_file() and path.suffix == ".py":
                files.add(path)
    
        sorted_files = sorted(files)
        return sorted_files
    
    
    def parse_python_methods(file_path: Path) -> list[MethodMetrics]:
        """Parse Python source file to extract method metrics."""
        if not file_path.exists():
            return []
    
        try:
            source = file_path.read_text()
        except Exception:
            return []
    
        try:
            tree = ast.parse(source)
        except Exception:
            return []
    
        metrics = []
    
        # Get module name from file
        module_name = file_path.stem
    
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private methods for now (can be configured)
                # Skip methods starting with underscore (private)
                if node.name.startswith("_"):
                    continue
    
                complexity = calculate_complexity(node)
                metrics.append(
                    MethodMetrics(
                        method_name=node.name,
                        class_name=module_name,
                        complexity=complexity,
                        coverage_percent=None,  # Will be filled by coverage
                        crap_score=None,
                    )
                )
            elif isinstance(node, ast.AsyncFunctionDef):
                if node.name.startswith("_"):
                    continue
    
                complexity = calculate_complexity(node)
                metrics.append(
                    MethodMetrics(
                        method_name=node.name,
                        class_name=module_name,
                        complexity=complexity,
                        coverage_percent=None,
                        crap_score=None,
                    )
                )
    
        return metrics
    
    
    def calculate_complexity(node: ast.AST) -> int:
        """
        Calculate cyclomatic complexity from AST.
        Base complexity = 1
        Each decision point adds 1.
        """
        complexity = 1
    
        for child in ast.walk(node):
            # Decision points that increase complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # and/or operators - each adds complexity
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                # list comprehensions with if
                if child.ifs:
                    complexity += len(child.ifs)
    
        return max(1, complexity)
    
    
    def run_coverage(root: Path) -> dict | None:
        """
        Run coverage on the given root and return coverage data.
        Uses coverage.py to generate coverage data.
        """
        import json
        import subprocess
    
        # Check if coverage is installed
        try:
            subprocess.run(["coverage", "--version"], capture_output=True, check=True)
        except Exception:
            return None
    
        # Run coverage with JSON report
        try:
            # First erase any old data
            subprocess.run(["coverage", "erase"], cwd=root, capture_output=True)
    
            # Run coverage on code under src/
            result = subprocess.run(
                ["coverage", "run", "-m", "pytest", "--collect-only", "-q"],
                cwd=root,
                capture_output=True,
                text=True,
            )
    
            # If no tests, run the module directly to get some coverage
            if result.returncode != 0:
                # Try to run python -c to at least load the modules
                src_dir = root / "src"
                if src_dir.exists():
                    for py_file in src_dir.rglob("*.py"):
                        if py_file.name.startswith("_"):
                            continue
                        subprocess.run(
                            ["coverage", "run", "-a", str(py_file)],
                            cwd=root,
                            capture_output=True,
                        )
    
            # Generate JSON report
            json_file = root / "coverage.json"
            try:
                subprocess.run(
                    ["coverage", "json", "-o", str(root), "--pretty-print"],
                    cwd=root,
                    capture_output=True,
                )
                if json_file.exists():
                    data = json.loads(json_file.read_text())
                    json_file.unlink()  # Clean up
                    return data
            except Exception:
                pass
    
        except Exception:
            pass
    
        return None
    
    
    def attribute_coverage(
        metrics: list[MethodMetrics], coverage_data: dict | None
    ) -> list[MethodMetrics]:
        """Attribute coverage data to method metrics."""
        if coverage_data is None:
            return metrics
    
        try:
            files = coverage_data.get("files", {})
        except Exception:
            return metrics
    
        result = []
        for metric in metrics:
            found = False
            for file_path, file_data in files.items():
                # Try to match method to coverage
                try:
                    percentages = file_data.get("percent_executed")
                except Exception:
                    percentages = None
    
                if percentages is not None:
                    result.append(
                        MethodMetrics(
                            method_name=metric.method_name,
                            class_name=metric.class_name,
                            complexity=metric.complexity,
                            coverage_percent=percentages,
                            crap_score=None,
                        )
                    )
                    found = True
                    break
    
            if not found:
                result.append(metric)
    
        return result
    
    
    def calculate_crap(
        complexity: int, coverage_percent: float | None
    ) -> float | None:
        """Calculate CRAP score: CC^2 * (1 - coverage)^3 + CC
    
        When coverage is unknown (None), treat as 0% for threshold purposes
        but still report as N/A in the output.
        """
        if coverage_percent is None:
            # Treat as 0% coverage for scoring
            cc = complexity
            return (cc * cc) + cc
    
        coverage = coverage_percent / 100.0
        cc = complexity
        crap = (cc * cc * ((1 - coverage) ** 3)) + cc
        return crap
    
    
    def format_report(metrics: list[MethodMetrics]) -> str:
        """Format metrics as a tabular report sorted by CRAP descending."""
        # Sort: N/A values at the end, then by CRAP descending
        sorted_metrics = sorted(
            metrics,
            key=lambda m: (
                m.crap_score is None,
                -float("inf") if m.crap_score is None else -m.crap_score,
            ),
        )
    
        lines = ["CRAP Report", "==========="]
        header = f"{'Method':<30} {'Class':<35} {'CC':>4} {'Cov%':>7} {'CRAP':>8}"
        lines.append(header)
        lines.append("-" * len(header))
    
        for metric in sorted_metrics:
            cov_str = (
                f"{metric.coverage_percent:5.1f}%"
                if metric.coverage_percent is not None
                else "  N/A "
            )
            crap_str = (
                f"{metric.crap_score:8.1f}" if metric.crap_score is not None else "     N/A"
            )
    
            lines.append(
                f"{metric.method_name:<30} {metric.class_name:<35} {metric.complexity:>4} {cov_str:>7} {crap_str:>8}"
            )
    
        return "\n".join(lines)
    
    
    def max_crap(metrics: list[MethodMetrics]) -> float:
        """Find maximum CRAP score in metrics."""
        max_val = 0.0
        for metric in metrics:
            if metric.crap_score is not None:
                max_val = max(max_val, metric.crap_score)
        return max_val
    
    
    def threshold_exceeded(max_crap: float) -> bool:
        return max_crap > DEFAULT_THRESHOLD
    
    
    def module_root_for(workspace_root: Path, file: Path) -> Path:
        """Find the module root for a given file by walking up for pyproject.toml or setup.py."""
        current = file.parent if file.is_file() else file
        current = current.resolve()
    
        workspace = workspace_root.resolve()
    
        while current != workspace and current.parent != current:
            for marker in ["pyproject.toml", "setup.py", "setup.cfg"]:
                if (current / marker).exists():
                    return current
            current = current.parent
    
        return workspace
    
    
    def analyze_files(files: list[Path], workspace_root: Path) -> list[MethodMetrics]:
        """Analyze the given files, grouped by module."""
        from collections import defaultdict
    
        # Group files by module root
        grouped = defaultdict(list)
        for file in files:
            module = module_root_for(workspace_root, file)
            grouped[module].append(file)
    
        all_metrics = []
    
        for module_root, module_files in grouped.items():
            # Run coverage for this module
            coverage_data = run_coverage(module_root)
    
            # Parse each file and compute metrics
            for file in module_files:
                metrics = parse_python_methods(file)
                metrics = attribute_coverage(metrics, coverage_data)
    
                # Calculate CRAP scores
                for metric in metrics:
                    crap = calculate_crap(metric.complexity, metric.coverage_percent)
                    all_metrics.append(
                        MethodMetrics(
                            method_name=metric.method_name,
                            class_name=metric.class_name,
                            complexity=metric.complexity,
                            coverage_percent=metric.coverage_percent,
                            crap_score=crap,
                        )
                    )
    
        return all_metrics
    
    
    def execute(args: list[str], project_root: Path, out=None, err=None) -> int:
        """Main execution function."""
        if out is None:
            out = sys.stdout
        if err is None:
            err = sys.stderr
    
        debug = "--debug" in args
    
        try:
            parsed = parse_arguments(args)
        except ValueError as e:
            err.write(str(e) + "\n")
            err.write(usage() + "\n")
            return 1
    
        if parsed.mode == CliMode.HELP:
            out.write(usage() + "\n")
            return 0
    
        # Find files to analyze
        if parsed.mode == CliMode.ALL_SRC:
            files = find_python_files_recursively(project_root)
        elif parsed.mode == CliMode.CHANGED_SRC:
            files = find_changed_python_files(project_root)
        elif parsed.mode == CliMode.EXPLICIT_FILES:
            files = explicit_files(project_root, parsed.file_args)
        else:
            files = []
    
        if debug:
            err.write(f"[debug] Selected {len(files)} Python files for analysis\n")
    
        if not files:
            out.write("No Python files to analyze.\n")
            return 0
    
        # Try to generate coverage, then analyze
        coverage_xml = project_root / "coverage.xml"
        if not coverage_xml.exists():
            try:
                from .coverage_runner import generate_coverage
    
                generate_coverage(project_root, debug=debug, err=err)
            except Exception:
                if debug:
                    err.write("[debug] Coverage generation failed; proceeding without coverage.xml\n")
        elif debug:
            err.write(f"[debug] Using existing coverage XML at {coverage_xml}\n")
    
        # Use the crap_analyzer module for proper coverage-aware analysis
        from .crap_analyzer import analyze as crap_analyze
    
        metrics = crap_analyze(
            project_root, files, coverage_xml if coverage_xml.exists() else None
        )
    
        if not metrics:
            out.write("No Python files to analyze.\n")
            return 0
    
        # Format and print report
        out.write(format_report(metrics) + "\n")
    
        # Check threshold
        max_crap_val = max_crap(metrics)
        if threshold_exceeded(max_crap_val):
            err.write(
                f"CRAP threshold exceeded: {max_crap_val:.1f} > {DEFAULT_THRESHOLD}\n"
            )
            return 2
    
        return 0
    
    
    def main() -> int:
        """Entry point."""
        project_root = Path.cwd()
        return execute(sys.argv[1:], project_root, sys.stdout, sys.stderr)
    
    
    if __name__ == "__main__":
        sys.exit(main())
    