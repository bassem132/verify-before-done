#!/usr/bin/env python3
"""Claude Code hook: block `git commit` / `gh pr create` when code was edited
after the last verification command in this session.

Modes (passed as the first argument by hooks.json):
    edited   PostToolUse on Edit/Write/MultiEdit/NotebookEdit: mark the session as unverified
    ran      PostToolUse on Bash: if the command was a test/lint/typecheck/build, mark verified
    gate     PreToolUse on Bash: if the command commits or opens a PR while unverified, block it

Docs-only edits (.md, .txt, images, …) never block. To commit anyway with the
user's approval, prefix the command with VERIFY_SKIP=1.

Reads the hook JSON from stdin. Exit 2 + stderr = block (shown to the agent).
Works on Python 3.8+ with no dependencies.
"""
import json
import os
import re
import sys
import tempfile

DOC_EXT = re.compile(r"\.(md|mdx|markdown|txt|rst|adoc|png|jpe?g|gif|svg|webp|ico|pdf|csv)$", re.I)
CHECK_CMD = re.compile(
    r"(^|[\s;&|(])("
    r"(npm|pnpm|yarn|bun)(\s+run)?\s+(test|lint|typecheck|type-check|check|build|verify|ci|e2e)\b"
    r"|(npx|pnpm exec|bunx)\s+(tsc|vitest|jest|eslint|playwright|biome)\b"
    r"|\b(vitest|jest|pytest|tsc|eslint|ruff|mypy|pyright|phpunit|rspec|rubocop|playwright)\b"
    r"|(uv|poetry) run (pytest|ruff|mypy|pyright)"
    r"|cargo (test|clippy|build|check)|go (test|vet|build)"
    r"|make (test|tests|check|verify|lint|build|ci)\b"
    r"|(flutter|dart) (test|analyze)|deno (test|lint|check)"
    r"|php artisan test|composer test|bundle exec (rspec|rake test|rubocop)"
    r"|python3? -m (pytest|unittest)|xcodebuild\b.*\btest\b|gradlew? (test|check|build)"
    r")"
)
# git options before the subcommand, including ones that take a value: git -C dir / -c key=val commit
SHIP_CMD = re.compile(
    r"(^|[\s;&|(])(git\s+(?:(?:-C|-c|--git-dir|--work-tree)\s+\S+\s+|--?[\w-]+(?:=\S+)?\s+)*commit\b"
    r"|gh\s+pr\s+create\b)"
)


def state_path(session_id):
    folder = os.path.join(tempfile.gettempdir(), "verify-before-done")
    if not os.path.isdir(folder):
        os.makedirs(folder)
    safe = re.sub(r"[^\w.-]", "_", session_id or "default")
    return os.path.join(folder, safe + ".json")


def load(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"dirty": [], "verified_by": None}


def save(path, state):
    with open(path, "w") as fh:
        json.dump(state, fh)


def edited_paths(tool_input):
    paths = []
    for key in ("file_path", "notebook_path", "path"):
        if tool_input.get(key):
            paths.append(tool_input[key])
    for edit in tool_input.get("edits", []) or []:
        if isinstance(edit, dict) and edit.get("file_path"):
            paths.append(edit["file_path"])
    return paths


def main(argv):
    mode = argv[0] if argv else ""
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    path = state_path(event.get("session_id"))
    state = load(path)
    tool_input = event.get("tool_input") or {}
    command = tool_input.get("command") or ""

    if mode == "edited":
        code = [p for p in edited_paths(tool_input) if not DOC_EXT.search(p)]
        if code:
            state["dirty"] = sorted(set(state["dirty"]) | set(code))
            state["verified_by"] = None
            save(path, state)
        return 0

    if mode == "ran":
        if CHECK_CMD.search(command) and not SHIP_CMD.search(command.split("&&")[0]):
            state["dirty"] = []
            state["verified_by"] = command
            save(path, state)
        return 0

    if mode == "gate":
        if not SHIP_CMD.search(command) or not state["dirty"]:
            return 0
        if re.search(r"(^|\s)VERIFY_SKIP=1\b", command):
            return 0
        ship = SHIP_CMD.search(command)
        if CHECK_CMD.search(command[:ship.start()]):
            return 0  # e.g. `pnpm test && git commit …`
        files = state["dirty"]
        shown = ", ".join(os.path.basename(f) for f in files[:5]) + (" …" if len(files) > 5 else "")
        sys.stderr.write(
            "verify-before-done: code changed since the last test/lint/build run (%s).\n"
            "Run the checks that cover this change and read their output before committing. "
            "Find them with: python3 <skill-dir>/scripts/detect_checks.py\n"
            "If the user explicitly says to commit without checks, prefix the command with VERIFY_SKIP=1.\n" % shown
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
