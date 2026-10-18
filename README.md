# Verify before done

Stops your AI agent from saying 'done' or 'fixed' without running the checks that prove it.

A portable agent skill (`SKILL.md`) that works in **Claude Code**, **Codex** and **Cursor**.

## Install

### Claude Code (plugin)

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

### Cursor

Copy the folder into your project's `.cursor/skills/`, or paste the body of `SKILL.md` into a rule in `.cursor/rules/verify-before-done.mdc`.

## What's inside

```
skills/verify-before-done/SKILL.md   the skill
```

See [skills/verify-before-done/SKILL.md](skills/verify-before-done/SKILL.md) for when it triggers and what it does.

## Author

Bassem Mo’men — [@bassem132](https://github.com/bassem132)

## License

MIT — see [LICENSE](LICENSE).
