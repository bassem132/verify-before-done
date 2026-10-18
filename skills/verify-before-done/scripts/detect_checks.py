#!/usr/bin/env python3
"""Find the commands that verify work in a repo: tests, lint, typecheck, build.

Reads package.json (and the lockfile to pick npm/pnpm/yarn/bun), Makefile,
pyproject.toml / pytest config, Cargo.toml, go.mod, composer.json, Gemfile,
pubspec.yaml, deno.json, and the `run:` steps of GitHub Actions workflows.

Usage:
    python3 detect_checks.py [repo-dir]          # default: current directory
    python3 detect_checks.py [repo-dir] --json

Exit code: 0 = found at least one check, 1 = found nothing.
Works on Python 3.8+ with no dependencies.
"""
import glob
import json
import os
import re
import sys

KINDS = ("test", "lint", "typecheck", "build")


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return ""


def node_checks(root, add):
    pkg_text = read(os.path.join(root, "package.json"))
    if not pkg_text:
        return
    try:
        scripts = json.loads(pkg_text).get("scripts", {}) or {}
    except ValueError:
        return
    if os.path.exists(os.path.join(root, "pnpm-lock.yaml")):
        pm = "pnpm"
    elif os.path.exists(os.path.join(root, "yarn.lock")):
        pm = "yarn"
    elif os.path.exists(os.path.join(root, "bun.lockb")) or os.path.exists(os.path.join(root, "bun.lock")):
        pm = "bun"
    else:
        pm = "npm"

    def run(name):
        if name == "test" and pm in ("npm", "pnpm", "yarn"):
            return "%s test" % pm
        return "%s run %s" % (pm, name)

    for name, body in scripts.items():
        low = name.lower()
        if re.search(r"(^|:)watch|dev|start|serve|preview", low):
            continue
        if low in ("test", "test:unit", "test:ci", "unit") or (low.startswith("test") and "e2e" not in low):
            kind = "test"
        elif "e2e" in low or "playwright" in low or "cypress" in low:
            kind = "test"
        elif low in ("lint", "eslint", "lint:ci", "biome", "format:check", "fmt:check") or low.startswith("lint"):
            kind = "lint"
        elif low in ("typecheck", "type-check", "types", "tsc", "check-types", "check:types"):
            kind = "typecheck"
        elif low in ("build", "compile"):
            kind = "build"
        elif low in ("check", "verify", "validate", "ci"):
            kind = "test"
        else:
            continue
        cmd = run(name)
        if kind == "test" and re.search(r"\b(vitest|jest)\b", body or "") and "--run" not in body and "vitest" in body:
            cmd += " -- --run"
        add(kind, cmd, "package.json script '%s': %s" % (name, body))
    if "typecheck" not in [k for k, _, _ in add.found] and os.path.exists(os.path.join(root, "tsconfig.json")):
        add("typecheck", "%s tsc --noEmit" % ("npx" if pm == "npm" else pm + " exec"), "tsconfig.json present")


def make_checks(root, add):
    text = read(os.path.join(root, "Makefile")) or read(os.path.join(root, "makefile"))
    for target in re.findall(r"^([A-Za-z][\w.-]*)\s*:(?!=)", text, re.M):
        low = target.lower()
        kind = {"test": "test", "tests": "test", "check": "test", "verify": "test", "ci": "test",
                "lint": "lint", "fmt-check": "lint", "typecheck": "typecheck", "build": "build"}.get(low)
        if kind:
            add(kind, "make %s" % target, "Makefile target")


def python_checks(root, add):
    pyproject = read(os.path.join(root, "pyproject.toml"))
    configs = pyproject + read(os.path.join(root, "setup.cfg")) + read(os.path.join(root, "tox.ini"))
    has_pytest = (os.path.exists(os.path.join(root, "pytest.ini")) or "[tool.pytest" in configs
                  or "[pytest]" in configs or "pytest" in configs
                  or (os.path.isdir(os.path.join(root, "tests")) and (pyproject or os.path.exists(os.path.join(root, "setup.py")))))
    if not (pyproject or has_pytest or os.path.exists(os.path.join(root, "requirements.txt"))):
        return
    if os.path.exists(os.path.join(root, "uv.lock")):
        prefix = "uv run "
    elif os.path.exists(os.path.join(root, "poetry.lock")):
        prefix = "poetry run "
    else:
        prefix = ""
    if has_pytest:
        add("test", prefix + "pytest", "pytest config or tests/ directory")
    if "[tool.ruff" in configs or os.path.exists(os.path.join(root, "ruff.toml")):
        add("lint", prefix + "ruff check .", "ruff config")
    if "[tool.mypy" in configs or os.path.exists(os.path.join(root, "mypy.ini")):
        add("typecheck", prefix + "mypy .", "mypy config")
    if "[tool.pyright" in configs or os.path.exists(os.path.join(root, "pyrightconfig.json")):
        add("typecheck", prefix + "pyright", "pyright config")


def other_checks(root, add):
    if os.path.exists(os.path.join(root, "Cargo.toml")):
        add("test", "cargo test", "Cargo.toml")
        add("lint", "cargo clippy -- -D warnings", "Cargo.toml")
        add("build", "cargo build", "Cargo.toml")
    if os.path.exists(os.path.join(root, "go.mod")):
        add("test", "go test ./...", "go.mod")
        add("lint", "go vet ./...", "go.mod")
        add("build", "go build ./...", "go.mod")
    composer = read(os.path.join(root, "composer.json"))
    if composer:
        try:
            scripts = json.loads(composer).get("scripts", {}) or {}
        except ValueError:
            scripts = {}
        if "test" in scripts:
            add("test", "composer test", "composer.json script")
        elif os.path.exists(os.path.join(root, "phpunit.xml")) or os.path.exists(os.path.join(root, "phpunit.xml.dist")):
            add("test", "vendor/bin/phpunit", "phpunit.xml")
        if os.path.exists(os.path.join(root, "artisan")):
            add("test", "php artisan test", "Laravel artisan")
    if os.path.exists(os.path.join(root, "Gemfile")):
        if os.path.isdir(os.path.join(root, "spec")):
            add("test", "bundle exec rspec", "Gemfile + spec/")
        elif os.path.isdir(os.path.join(root, "test")):
            add("test", "bundle exec rake test", "Gemfile + test/")
        if os.path.exists(os.path.join(root, ".rubocop.yml")):
            add("lint", "bundle exec rubocop", ".rubocop.yml")
    pubspec = read(os.path.join(root, "pubspec.yaml"))
    if pubspec:
        tool = "flutter" if "flutter:" in pubspec else "dart"
        add("test", "%s test" % tool, "pubspec.yaml")
        add("lint", "%s analyze" % tool, "pubspec.yaml")
    if os.path.exists(os.path.join(root, "deno.json")) or os.path.exists(os.path.join(root, "deno.jsonc")):
        add("test", "deno test", "deno.json")
        add("lint", "deno lint", "deno.json")
        add("typecheck", "deno check .", "deno.json")


def ci_steps(root):
    steps = []
    for path in sorted(glob.glob(os.path.join(root, ".github", "workflows", "*.y*ml"))):
        lines = read(path).splitlines()
        i = 0
        while i < len(lines):
            m = re.match(r"^(\s*)(?:-\s+)?run:\s*(.*)$", lines[i])
            if m:
                indent, value = len(m.group(1)), m.group(2).strip()
                if value in ("|", ">", "|-", ">-", ""):
                    i += 1
                    while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > indent):
                        if lines[i].strip() and not lines[i].strip().startswith("#"):
                            steps.append((os.path.relpath(path, root), lines[i].strip()))
                        i += 1
                    continue
                steps.append((os.path.relpath(path, root), value.strip("'\"")))
            i += 1
    noise = re.compile(r"^(echo|cd|export|mkdir|cp|mv|ls|cat|sudo apt|apt-get|brew|curl|wget|git config|"
                       r"npm (ci|install)|pnpm install|yarn install|yarn$|bun install|pip install|uv sync|"
                       r"poetry install|bundle install|composer install|go mod download)\b")
    return [(f, s) for f, s in steps if not noise.match(s)]


class Collector(object):
    def __init__(self):
        self.found = []

    def __call__(self, kind, cmd, source):
        if all(cmd != c for _, c, _ in self.found):
            self.found.append((kind, cmd, source))


def detect(root):
    add = Collector()
    node_checks(root, add)
    make_checks(root, add)
    python_checks(root, add)
    other_checks(root, add)
    result = {k: [{"command": c, "source": s} for kind, c, s in add.found if kind == k] for k in KINDS}
    result["ci"] = [{"command": s, "source": f} for f, s in ci_steps(root)]
    return result


def main(argv):
    as_json = "--json" in argv
    args = [a for a in argv if a != "--json"]
    root = os.path.abspath(args[0] if args else ".")
    result = detect(root)
    total = sum(len(v) for v in result.values())
    if as_json:
        print(json.dumps(result, indent=2))
        return 0 if total else 1
    if not total:
        print("No checks found in %s. Ask the user how they verify changes, then save it to AGENTS.md." % root)
        return 1
    print("Checks for %s\n" % root)
    for kind in KINDS + ("ci",):
        if result[kind]:
            print("%s:" % ("CI steps (run these locally if unsure)" if kind == "ci" else kind))
            for item in result[kind]:
                print("  %-40s  # %s" % (item["command"], item["source"]))
            print()
    print("Run the ones that cover your change. Read the full output, not just the exit code.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
