# /// script
# requires-python = ">=3.10"
# dependencies = ["gdtoolkit==4.5.0"]
# ///
"""Strict-project verification pipeline.

Run without arguments to execute every stage. Every stage runs even when an
earlier one fails, so a single invocation reports everything that is wrong.
Exits non-zero if any stage failed. Pass a command name to run one thing;
`--help` lists them.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_TOP_LEVEL = {"addons", ".godot", ".git"}

CHECKER_SCENE = "res://scripts/typecheck.tscn"
FAIL_MARKER = "SCRIPT-FAIL "


@dataclass
class StageResult:
    name: str
    ok: bool
    details: list[str] = field(default_factory=list)


def find_godot() -> str:
    candidate = os.environ.get("GODOT") or shutil.which("godot")
    if not candidate:
        sys.exit(
            "Godot binary not found. Set the GODOT environment variable to the "
            "Godot 4.7 executable, or put `godot` on PATH."
        )
    return candidate


def run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout + proc.stderr


def gdscript_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(REPO_ROOT.rglob("*.gd")):
        parts = path.relative_to(REPO_ROOT).parts
        if parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        files.append(path)
    return files


def staged_gdscript_files() -> list[Path]:
    """GDScript files staged for the next commit, minus addons/ and deletions."""
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=ACMR",
            "-z",
            "--",
            "*.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        sys.exit(f"git diff --cached failed: {proc.stderr.strip()}")
    files: list[Path] = []
    for name in proc.stdout.split("\0"):
        if not name or Path(name).parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        path = REPO_ROOT / name
        if path.is_file():
            files.append(path)
    return sorted(files)


def stage_import(godot: str) -> StageResult:
    code, output = run([godot, "--headless", "--path", str(REPO_ROOT), "--import"])
    if code == 0:
        return StageResult("import", True, [])
    details = [f"godot --import exited {code}"]
    details.extend(f"  {line.rstrip()}" for line in output.splitlines() if line.strip())
    return StageResult("import", False, details)


def stage_typecheck(godot: str, files: list[Path]) -> StageResult:
    """Compile every script inside a running project.

    Scripts are loaded by a checker scene that runs as the project, so
    autoloads, class_name globals and UID references all resolve the way
    they do at runtime. `GDScript.reload()` returns a per-file error code,
    which is what makes a failure name its own path.
    """
    if not files:
        return StageResult("typecheck", True, [])
    res_paths = ["res://" + p.relative_to(REPO_ROOT).as_posix() for p in files]
    code, output = run(
        [
            godot,
            "--headless",
            "--path",
            str(REPO_ROOT),
            CHECKER_SCENE,
            "--",
            *res_paths,
        ]
    )
    lines = output.splitlines()
    details = [
        line.strip()[len(FAIL_MARKER) :]
        for line in lines
        if line.strip().startswith(FAIL_MARKER)
    ]
    diagnostics = [
        f"  {line.strip()}"
        for line in lines
        if "Parse Error:" in line or "Compile Error:" in line
    ]
    if details:
        details.extend(diagnostics)
    elif code != 0:
        details.append(f"checker scene exited {code} without naming a script")
        details.extend(diagnostics)
    return StageResult("typecheck", not details, details)


def stage_format(files: list[Path], write: bool = False) -> StageResult:
    name = "format" if write else "format(check)"
    if not files:
        return StageResult(name, True, [])
    paths = [str(path) for path in files]
    cmd = ["gdformat", *paths] if write else ["gdformat", "--check", *paths]
    code, output = run(cmd)
    lines = [f"  {line.strip()}" for line in output.splitlines() if line.strip()]
    if code != 0:
        header = "gdformat failed:" if write else "gdformat --check reported unformatted files:"
        return StageResult(name, False, [header, *lines])
    if write:
        print("\n".join(line.strip() for line in output.splitlines() if line.strip()))
    return StageResult(name, True, [])


def stage_lint(files: list[Path]) -> StageResult:
    if not files:
        return StageResult("lint", True, [])
    code, output = run(["gdlint", *[str(path) for path in files]])
    if code == 0:
        return StageResult("lint", True, [])
    details = ["gdlint reported problems:"]
    details.extend(f"  {line.strip()}" for line in output.splitlines() if line.strip())
    return StageResult("lint", False, details)


def stage_tests(godot: str) -> StageResult:
    tests_dir = REPO_ROOT / "tests"
    if not tests_dir.is_dir():
        return StageResult("tests", True, ["no tests directory"])
    code, output = run(
        [
            godot,
            "--headless",
            "--path",
            str(REPO_ROOT),
            "-s",
            "res://addons/gdUnit4/bin/GdUnitCmdTool.gd",
            "-a",
            "res://tests",
            "--ignoreHeadlessMode",
        ]
    )
    details: list[str] = []
    if code != 0:
        details.append(f"gdUnit4 exited {code}")
        details.extend(
            f"  {line.rstrip()}" for line in output.splitlines() if line.strip()
        )
    return StageResult("tests", code == 0, details)


def stage_install_hooks() -> StageResult:
    hook = REPO_ROOT / ".githooks" / "pre-commit"
    if not hook.is_file():
        return StageResult("hooks", False, [f"{hook} is missing"])
    code, output = run(
        ["git", "-C", str(REPO_ROOT), "config", "core.hooksPath", ".githooks"]
    )
    if code != 0:
        details = [f"git config exited {code}"]
        details.extend(f"  {line.strip()}" for line in output.splitlines() if line.strip())
        return StageResult("hooks", False, details)
    print("git will now run .githooks/pre-commit (checks formatting before a commit)")
    return StageResult("hooks", True, [])


def report(results: list[StageResult]) -> int:
    print()
    failed = [r for r in results if not r.ok]
    for result in results:
        mark = "PASS" if result.ok else "FAIL"
        print(f"[{mark}] {result.name}")
        if not result.ok:
            for detail in result.details:
                print(f"       {detail}")
    print()
    if failed:
        names = ", ".join(r.name for r in failed)
        print(f"FAILED: {names}")
        return 1
    print("All checks passed.")
    return 0


COMMANDS: dict[str, str] = {
    "check": "run every stage (default)",
    "import": "rebuild .godot/ (assets, UIDs, class names)",
    "typecheck": "compile every script inside the running project",
    "lint": "run gdlint",
    "format": "reformat every script in place with gdformat",
    "format-check": "report unformatted scripts without changing them",
    "test": "run the gdUnit4 suites",
    "hooks": "point git at .githooks so the pre-commit hook runs",
}


FILE_COMMANDS = {"lint", "format", "format-check"}


def usage() -> str:
    width = max(len(name) for name in COMMANDS)
    lines = [f"usage: dev.py [{'|'.join(COMMANDS)}] [--staged]", "", "commands:"]
    lines.extend(f"  {name:<{width}}  {help_}" for name, help_ in COMMANDS.items())
    lines.append("")
    lines.append(
        "  --staged  restrict %s to files staged for commit"
        % ", ".join(sorted(FILE_COMMANDS))
    )
    return "\n".join(lines)


def dispatch(command: str, staged: bool = False) -> list[StageResult]:
    """Resolve Godot and the file list only for the stages that need them."""
    if command == "hooks":
        return [stage_install_hooks()]
    if command in FILE_COMMANDS:
        files = staged_gdscript_files() if staged else gdscript_files()
        if command == "lint":
            return [stage_lint(files)]
        return [stage_format(files, write=command == "format")]

    godot = find_godot()
    if command == "import":
        return [stage_import(godot)]
    if command == "test":
        return [stage_import(godot), stage_tests(godot)]
    if command == "typecheck":
        return [stage_import(godot), stage_typecheck(godot, gdscript_files())]

    files = gdscript_files()
    return [
        stage_import(godot),
        stage_typecheck(godot, files),
        stage_format(files),
        stage_lint(files),
        stage_tests(godot),
    ]


def main(argv: list[str]) -> int:
    staged = "--staged" in argv
    argv = [arg for arg in argv if arg != "--staged"]
    if len(argv) > 1:
        return report_usage_error(f"expected at most one command, got {len(argv)}")
    command = argv[0] if argv else "check"
    if command in {"-h", "--help", "help"}:
        print(usage())
        return 0
    if command not in COMMANDS:
        return report_usage_error(f"unknown command {command!r}")
    if staged and command not in FILE_COMMANDS:
        allowed = ", ".join(sorted(FILE_COMMANDS))
        return report_usage_error(f"--staged only applies to {allowed}")
    return report(dispatch(command, staged))


def report_usage_error(message: str) -> int:
    print(f"error: {message}\n", file=sys.stderr)
    print(usage(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
