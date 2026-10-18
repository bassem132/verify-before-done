# Manual checks by change type

Automated tests come first. Use these lists for what tests usually miss. Check only the items that apply to your change, and report which ones you checked.

## Web UI

- [ ] Open the page in the running dev server, not just the component in isolation.
- [ ] Do the exact action the user asked for, start to finish.
- [ ] The browser console shows no new errors or warnings.
- [ ] Empty state, loading state and error state (stop the API or pass bad input).
- [ ] Narrow screen (~375px): nothing overflows, no horizontal scroll.
- [ ] Keyboard: Tab reaches the new controls, Enter/Space activates them, focus is visible.
- [ ] Long text and big numbers don't break the layout.
- [ ] Dark mode, if the app has one.

## RTL and Arabic

- [ ] Page with `dir="rtl"`: layout mirrors, icons that point (arrows, chevrons) flip, logos don't.
- [ ] Use logical CSS (`margin-inline-start`, `padding-inline-end`) instead of left/right.
- [ ] Arabic text renders in the right font, with no boxes (□) or broken letter joining.
- [ ] Mixed Arabic + numbers/English reads in the right order (phone numbers, prices, dates).
- [ ] Arabic-Indic digits (٠١٢) and Western digits (012) are both handled where users type numbers.
- [ ] Search, sorting and validation work with Arabic input.

## API / backend

- [ ] Call the endpoint for real (curl/httpie/test client) and read the response body.
- [ ] Happy path, plus invalid input (expect 400), missing auth (401) and another user's resource (403/404).
- [ ] The status code and response shape match what clients expect. Nothing renamed silently.
- [ ] Server logs show no new errors or stack traces.
- [ ] Any new query uses an index (look at it with EXPLAIN on realistic data).

## Database and data

- [ ] The migration runs on a fresh database and on a copy of real data.
- [ ] The rollback runs too, or it's documented as irreversible and approved.
- [ ] Row counts and totals match before and after a backfill.
- [ ] No long table locks on big tables.

## Mobile (iOS / Android / React Native / Flutter)

- [ ] Run it on a simulator or emulator, not just a build.
- [ ] Small and large screens, portrait and landscape if supported.
- [ ] Safe areas (notch, home indicator) don't cover content.
- [ ] Offline or slow network shows a sensible state.
- [ ] Back navigation and app relaunch keep the expected state.

## CLI / scripts

- [ ] Run the real command with real arguments and read its output.
- [ ] `--help` still works, and bad arguments give a clear error with a non-zero exit code.
- [ ] Run it from a different working directory, and with paths that contain spaces.

## Money and dates

- [ ] Amounts are stored and calculated in minor units (piasters, cents). Rounding is tested.
- [ ] Results are checked in the user's time zone (e.g. Africa/Cairo) and in UTC, including near midnight and DST changes.

## Before you say "done"

- [ ] The checks ran **after** your last edit.
- [ ] You read the full output, including warnings and skipped tests.
- [ ] Your report lists what you checked and what you couldn't check.
