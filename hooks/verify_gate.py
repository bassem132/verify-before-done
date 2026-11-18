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
CHECK_ALT = (
    r"(npm|pnpm|yarn|bun)(\s+run)?\s+(test|lint|typecheck|type-check|check|build|verify|ci|e2e)\b"
    r"|(npx|pnpm exec|bunx)\s+(tsc|vitest|jest|eslint|playwright|biome)\b"
    r"|(vitest|jest|pytest|tsc|eslint|ruff|mypy|pyright|phpunit|rspec|rubocop|playwright)\b"
    r"|(uv|poetry) run (pytest|ruff|mypy|pyright)"
    r"|cargo (test|clippy|build|check)|go (test|vet|build)"
    r"|make (test|tests|check|verify|lint|build|ci)\b"
    r"|(flutter|dart) (test|analyze)|deno (test|lint|check)"
    r"|php artisan test|composer test|bundle exec (rspec|rake test|rubocop)"
    r"|python3? -m (pytest|unittest)|xcodebuild\b.*\btest\b|gradlew? (test|check|build)"
)
# A check only counts at the START of a command segment (after env vars / time / sudo), so
# `npm install jest`, `grep pytest .` or `echo vitest` never clear the gate.
CHECK_SEG = re.compile(r"^\s*(?:\w+=\S*\s+)*(?:(?:time|env|command|sudo|exec)\s+)*(?:" + CHECK_ALT + r")")
# Runs that do not actually exercise the code.
NOT_A_RUN = re.compile(r"--(version|help|collect-only|list-tests|listTests|dry-run|init)\b|\s-(h|v|V)(\s|$)")
SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\||\n")
# Shell commands that change files without going through the Edit/Write tools.
SHELL_EDIT = re.compile(r"\bsed\s+(?:-\w*\s+)*(?:-\w*i\w*|--in-place)\b|\bperl\s+-\w*i\w*\b|\btee\b|\bgit\s+apply\b|(?:^|\s)patch\s")
REDIRECT = re.compile(r"(?<![\d&>])>>?\s*([^\s&|;<>]+)")
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


def is_check(command):
    """True if any segment of the command is a real test/lint/typecheck/build run."""
    for seg in SEGMENT_SPLIT.split(command):
        if CHECK_SEG.search(seg) and not NOT_A_RUN.search(seg):
            return True
    return False


def shell_edited_paths(command):
    """Files a shell command appears to modify; ['(shell edit)'] when the target can't be parsed."""
    found = []
    for target in REDIRECT.findall(command):
        if target not in ("/dev/null", "/dev/stderr", "/dev/stdout") and not target.startswith("&"):
            found.append(target)
    if SHELL_EDIT.search(command) and not found:
        for seg in SEGMENT_SPLIT.split(command):
            if SHELL_EDIT.search(seg):
                args = [a for a in seg.split() if not a.startswith("-") and not a.startswith(("'", '"', "s/", "s|"))]
                found.append(args[-1] if args else "(shell edit)")
    return found


def run_failed(event):
    """Best-effort: did the Bash command fail or get interrupted? Unknown schema -> assume it passed."""
    resp = event.get("tool_response")
    if not isinstance(resp, dict):
        return False
    if resp.get("is_error") or resp.get("isError") or resp.get("interrupted"):
        return True
    for key in ("exitCode", "exit_code", "returncode", "code"):
        if isinstance(resp.get(key), int) and resp[key] != 0:
            return True
    return False


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
        if is_check(command) and not SHIP_CMD.search(command.split("&&")[0]):
            if not run_failed(event):
                state["dirty"] = []
                state["verified_by"] = command
                save(path, state)
            return 0
        code = [p for p in shell_edited_paths(command) if not DOC_EXT.search(p)]
        if code:
            state["dirty"] = sorted(set(state["dirty"]) | set(code))
            state["verified_by"] = None
            save(path, state)
        return 0

    if mode == "gate":
        if not SHIP_CMD.search(command) or not state["dirty"]:
            return 0
        if re.search(r"(^|\s)VERIFY_SKIP=1\b", command):
            return 0
        ship = SHIP_CMD.search(command)
        if is_check(command[:ship.start()]):
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
