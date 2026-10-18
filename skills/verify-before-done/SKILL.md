---
name: verify-before-done
description: Require real evidence before saying work is done, fixed or passing. Use before claiming a task is complete, before committing or opening a PR, and whenever you are about to write "this should work", "fixed", or "all tests pass".
author: Bassem Mo'men
license: MIT
---

# Verify before done

"It should work now" is the most expensive sentence an agent writes. The user trusts it, ships it, and finds the bug later. This skill makes every completion claim come with proof.

## The rule

**No claim without evidence from this session.** If you say it passes, you ran it and saw it pass. If you didn't run it, say so.

## Procedure

Before saying a task is done:

1. **Name the claim.** What exactly are you saying is true? ("The login bug is fixed", "The build passes", "The page works on mobile".)
2. **Pick the check that would prove it wrong.** Prefer, in order:
   - the exact reproduction of the original bug or request,
   - the project's tests / typecheck / lint / build commands (look in AGENTS.md, package.json, Makefile, CI config),
   - running the app and exercising the change (dev server, CLI, browser, simulator),
   - reading the diff end to end as a last resort.
3. **Run it now** and read the full output — not just the last line. Exit code 0 with skipped tests or swallowed errors is not a pass.
4. **Report what you saw**, with the command and the relevant output. Include failures and anything you couldn't check.
5. **If it fails**, don't claim partial success as success. Fix it, or report it plainly.

## Report format

```markdown
Done: invoice PDF export.

Verified:
- `pnpm test src/invoices` — 14 passed, 0 failed.
- `pnpm typecheck` — no errors.
- Dev server: clicked "Download PDF" on invoice #1042, file opened correctly.

Not verified:
- Safari (no access here).
```

## Red flags — stop and verify

- You're about to write "should", "probably", "I believe", "looks good".
- You changed code after the last test run.
- The test you ran doesn't cover the code you changed.
- You fixed a symptom but never reproduced the original bug.
- A command printed warnings or errors you didn't read.

## Never

- Delete, skip or weaken a test to make it pass without telling the user.
- Mark a task done because the code compiles.
- Report "all tests pass" from a run before your latest edit.
