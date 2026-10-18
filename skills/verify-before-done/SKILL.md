---
name: verify-before-done
description: Require fresh evidence before claiming work is done, fixed, working or passing. Use before saying a task is complete, before committing, pushing or opening a PR, when the user asks "is it done?", "does it work?", "did the tests pass?", and whenever you are about to write "should work", "fixed", "done" or "all tests pass". Also use when picking which test, lint or build commands a repo uses.
author: Bassem Mo'men
license: MIT
---

# Verify before done

"It should work now" is the most expensive sentence an agent writes. The user trusts it, ships it, and finds the bug later. This skill makes every claim that work is done come with proof.

## The rule

**No claim without evidence from this session, gathered after your last edit.** If you say it passes, you ran it and saw it pass. If you didn't run it, say so.

## Procedure

1. **State the claim.** What exactly are you saying is true? ("The login bug is fixed", "The build passes", "The page works on mobile".)
2. **Find the repo's checks.** Read AGENTS.md / CLAUDE.md first. If they don't list the commands, run:
   ```bash
   python3 <skill-dir>/scripts/detect_checks.py
   ```
   It reads package.json and the lockfile, Makefile, pyproject, Cargo, go.mod, composer, Gemfile, pubspec, deno and GitHub Actions, then prints the test, lint, typecheck and build commands.
3. **Pick the check that would prove the claim wrong.** In order of preference:
   - the exact reproduction of the original bug or request,
   - the tests that cover the code you changed, then the full suite,
   - typecheck, lint and build,
   - running the app and doing the action yourself. [reference/manual-checks.md](reference/manual-checks.md) lists what to check for UI, RTL/Arabic, APIs, data, mobile, CLIs, money and dates,
   - reading the whole diff, but only as a last resort.
4. **Run it now** and read the full output, not just the last line. An exit code of 0 with skipped tests, swallowed errors or "0 tests ran" is not a pass.
5. **Report what you saw**: the command, the key output, and what you couldn't check.
6. **If it fails**, don't present partial success as success. Fix it, or report the failure plainly.

## Report format

```markdown
Done: invoice PDF export.

Verified:
- `pnpm test src/invoices`: 14 passed, 0 failed.
- `pnpm typecheck`: no errors.
- Dev server: clicked "Download PDF" on invoice #1042; the file opened and the totals match.

Not verified:
- Safari (no access here).
```

## Red flags: stop and verify

- You're about to write "should", "probably", "I believe" or "looks good".
- You changed code after the last test run.
- The test you ran doesn't cover the code you changed.
- You fixed a symptom but never reproduced the original bug.
- A command printed warnings or errors you didn't read.
- The suite ran "0 tests", or the file you changed was skipped.

## Never

- Delete, skip, loosen or `.only` a test to make it pass without telling the user.
- Mark a task done because the code compiles.
- Report "all tests pass" from a run before your latest edit.
- Commit or open a PR with checks you know are failing, unless the user says to and you've reported the failure.

## Enforcement hook (Claude Code)

When this repo is installed as a Claude Code plugin, `hooks/hooks.json` turns the rule into a gate. If code files were edited after the last test, lint, typecheck or build command, `git commit` and `gh pr create` are blocked until the checks run. Docs-only edits never block. If the user explicitly approves committing without checks, prefix the command with `VERIFY_SKIP=1`.

## Files in this skill

- [scripts/detect_checks.py](scripts/detect_checks.py): finds the repo's verification commands (Python 3.8+, no dependencies).
- [reference/manual-checks.md](reference/manual-checks.md): manual checklists by type of change.
- `../../hooks/`: the Claude Code gate (`hooks.json` + `verify_gate.py`).
