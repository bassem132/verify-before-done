import json, os, subprocess, sys, unittest, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "..", "hooks", "verify_gate.py")
HOOKS_JSON = os.path.join(HERE, "..", "hooks", "hooks.json")


class GateTests(unittest.TestCase):
    def setUp(self):
        self.session = "test-" + uuid.uuid4().hex

    def call(self, mode, tool_name, tool_input):
        event = {"session_id": self.session, "tool_name": tool_name, "tool_input": tool_input}
        return subprocess.run([sys.executable, HOOK, mode], input=json.dumps(event), capture_output=True, text=True)

    def edit(self, path):
        return self.call("edited", "Edit", {"file_path": path, "old_string": "a", "new_string": "b"})

    def bash(self, mode, command):
        return self.call(mode, "Bash", {"command": command})

    def test_commit_without_edits_allowed(self):
        self.assertEqual(self.bash("gate", "git commit -m x").returncode, 0)

    def test_commit_after_edit_blocked(self):
        self.edit("/repo/src/app.ts")
        r = self.bash("gate", "git commit -m 'fix'")
        self.assertEqual(r.returncode, 2)
        self.assertIn("app.ts", r.stderr)

    def test_pr_after_edit_blocked(self):
        self.edit("/repo/src/app.py")
        self.assertEqual(self.bash("gate", "gh pr create --fill").returncode, 2)

    def test_commit_after_tests_allowed(self):
        self.edit("/repo/src/app.ts")
        self.bash("ran", "pnpm test -- --run")
        self.assertEqual(self.bash("gate", "git commit -m x").returncode, 0)

    def test_edit_after_tests_blocks_again(self):
        self.edit("/repo/src/app.ts")
        self.bash("ran", "pytest -q")
        self.edit("/repo/src/other.ts")
        self.assertEqual(self.bash("gate", "git commit -m x").returncode, 2)

    def test_docs_only_edit_allowed(self):
        self.edit("/repo/README.md")
        self.assertEqual(self.bash("gate", "git commit -m docs").returncode, 0)

    def test_chained_check_then_commit_allowed(self):
        self.edit("/repo/main.go")
        self.assertEqual(self.bash("gate", "go test ./... && git commit -am x").returncode, 0)

    def test_skip_prefix_allowed(self):
        self.edit("/repo/main.go")
        self.assertEqual(self.bash("gate", "VERIFY_SKIP=1 git commit -am x").returncode, 0)

    def test_non_check_command_does_not_clear(self):
        self.edit("/repo/src/app.ts")
        self.bash("ran", "ls -la")
        self.assertEqual(self.bash("gate", "git -C /repo commit -m x").returncode, 2)

    def test_git_status_not_gated(self):
        self.edit("/repo/src/app.ts")
        self.assertEqual(self.bash("gate", "git status").returncode, 0)

    def test_git_options_with_values_still_gated(self):
        self.edit("/repo/src/app.ts")
        for cmd in ("git -c user.name=x commit -m y", "git --no-pager commit -m y", "cd /repo && git commit -m y"):
            self.assertEqual(self.bash("gate", cmd).returncode, 2, cmd)

    def test_non_runs_do_not_clear_the_gate(self):
        for cmd in ("npm install jest", "pip install pytest", "grep -rn pytest .", "echo run vitest",
                    "eslint --version", "pytest --collect-only", "cat package.json | grep test"):
            self.edit("/repo/src/app.ts")
            self.bash("ran", cmd)
            self.assertEqual(self.bash("gate", "git commit -m x").returncode, 2, cmd)

    def test_real_checks_still_clear_the_gate(self):
        for cmd in ("pnpm test", "npx tsc --noEmit", "cd /repo && pytest -q", "CI=1 npm run build",
                    "go vet ./... && go test ./...", "time cargo test"):
            self.edit("/repo/src/app.ts")
            self.bash("ran", cmd)
            self.assertEqual(self.bash("gate", "git commit -m x").returncode, 0, cmd)

    def test_failed_check_does_not_clear_the_gate(self):
        self.edit("/repo/src/app.ts")
        event = {"session_id": self.session, "tool_name": "Bash", "tool_input": {"command": "pnpm test"},
                 "tool_response": {"exitCode": 1}}
        subprocess.run([sys.executable, HOOK, "ran"], input=json.dumps(event), capture_output=True, text=True)
        self.assertEqual(self.bash("gate", "git commit -m x").returncode, 2)

    def test_shell_edits_mark_dirty(self):
        for cmd in ("sed -i '' 's/a/b/' src/app.ts", "echo 'x' > src/app.js", "cat <<EOF >> main.py\nx\nEOF",
                    "git apply fix.patch", "perl -pi -e 's/a/b/' lib/util.rb"):
            self.session = "test-" + uuid.uuid4().hex
            self.bash("ran", cmd)
            self.assertEqual(self.bash("gate", "git commit -m x").returncode, 2, cmd)

    def test_shell_doc_or_devnull_redirects_ignored(self):
        for cmd in ("echo hi > notes.md", "npm run lint 2>/dev/null", "ls > /dev/null", "echo x >> CHANGELOG.md"):
            self.session = "test-" + uuid.uuid4().hex
            self.bash("ran", cmd)
            self.assertEqual(self.bash("gate", "git commit -m x").returncode, 0, cmd)

    def test_hooks_json_valid(self):
        with open(HOOKS_JSON) as fh:
            config = json.load(fh)
        self.assertIn("PreToolUse", config["hooks"])
        self.assertIn("PostToolUse", config["hooks"])


if __name__ == "__main__":
    unittest.main()
