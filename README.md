# Verify before done

"It should work now" is how bugs reach production. This skill makes the agent find the repo's real checks, run them after its last edit, read the full output, and report evidence. In Claude Code, a hook also blocks `git commit` and `gh pr create` until checks have run.

A portable agent skill (`SKILL.md` plus scripts and references) for **Claude Code**, **Codex** and **Cursor**. The scripts have no dependencies (Python 3.8+ / bash 3.2+).

## What's inside

| File | What it does |
| --- | --- |
| `skills/verify-before-done/SKILL.md` | When it triggers, the procedure, red flags and the report format |
| `skills/verify-before-done/scripts/detect_checks.py` | Finds test/lint/typecheck/build commands from package.json, lockfiles, Makefile, pyproject, Cargo, go.mod, composer, Gemfile, pubspec, deno and GitHub Actions |
| `skills/verify-before-done/reference/manual-checks.md` | Checklists for web UI, RTL and Arabic, APIs, data, mobile, CLIs, money and dates |
| `hooks/` | Claude Code gate: `hooks.json` + `verify_gate.py` |
| `adapters/cursor/verify-before-done.mdc` | Ready-made Cursor rule |
| `adapters/codex/AGENTS.snippet.md` | Short version to paste into any `AGENTS.md` |
| `evals/evals.json` | Test prompts: should it trigger, and what should the agent do |
| `tests/` | Unit tests for the scripts |

## Install

### Claude Code (plugin, recommended)

```
/plugin marketplace add bassem132/verify-before-done
/plugin install verify-before-done@verify-before-done
```

### Claude Code (manual)

```bash
git clone https://github.com/bassem132/verify-before-done.git
cp -r verify-before-done/skills/verify-before-done ~/.claude/skills/
```

### Codex

```bash
cp -r verify-before-done/skills/verify-before-done ~/.codex/skills/
```

Or paste `adapters/codex/AGENTS.snippet.md` into your `AGENTS.md`.

### Cursor

```bash
mkdir -p .cursor/rules .cursor/skills
cp verify-before-done/adapters/cursor/verify-before-done.mdc .cursor/rules/
cp -r verify-before-done/skills/verify-before-done .cursor/skills/      # so the agent can run the scripts
```

## Enforcement hook (Claude Code)

Installing as a plugin also installs `hooks/hooks.json`:

- After an Edit or Write to a code file, the session is marked unverified.
- Running a test, lint, typecheck or build command marks it verified.
- While it's unverified, `git commit` and `gh pr create` are blocked with a message telling the agent what to run.
- Docs-only edits (`.md`, `.txt`, images) never block. With your OK, `VERIFY_SKIP=1 git commit …` bypasses it.

Manual install: copy `hooks/verify_gate.py` somewhere stable and add the same three entries from `hooks/hooks.json` to `~/.claude/settings.json`, replacing `${CLAUDE_PLUGIN_ROOT}/hooks/verify_gate.py` with that path.

## Try the script

```bash
python3 skills/verify-before-done/scripts/detect_checks.py path/to/repo
```

## Develop

```bash
python3 -m unittest discover -s tests -v
claude plugin validate .
```

To check that the skill changes behaviour, run the prompts in `evals/evals.json` in a fresh session with the skill installed. Every `expect` item should hold, and prompts with `should_trigger: false` must not load the skill.

## Author

Bassem Mo’men · [@bassem132](https://github.com/bassem132)

## License

MIT, see [LICENSE](LICENSE).
