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

    def test_hooks_json_valid(self):
        with open(HOOKS_JSON) as fh:
            config = json.load(fh)
        self.assertIn("PreToolUse", config["hooks"])
        self.assertIn("PostToolUse", config["hooks"])


if __name__ == "__main__":
    unittest.main()
