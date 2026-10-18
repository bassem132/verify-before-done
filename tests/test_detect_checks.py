import json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "skills", "verify-before-done", "scripts", "detect_checks.py")


class DetectChecksTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def write(self, rel, text=""):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text)

    def detect(self):
        out = subprocess.run([sys.executable, SCRIPT, self.dir, "--json"], capture_output=True, text=True)
        return out.returncode, json.loads(out.stdout)

    def cmds(self, result, kind):
        return [c["command"] for c in result[kind]]

    def test_pnpm_project(self):
        self.write("package.json", json.dumps({"scripts": {"test": "vitest", "lint": "eslint .", "dev": "vite",
                                                           "typecheck": "tsc --noEmit", "build": "vite build"}}))
        self.write("pnpm-lock.yaml")
        code, r = self.detect()
        self.assertEqual(code, 0)
        self.assertEqual(self.cmds(r, "test"), ["pnpm test -- --run"])
        self.assertEqual(self.cmds(r, "lint"), ["pnpm run lint"])
        self.assertEqual(self.cmds(r, "typecheck"), ["pnpm run typecheck"])
        self.assertEqual(self.cmds(r, "build"), ["pnpm run build"])

    def test_npm_with_tsconfig_fallback(self):
        self.write("package.json", json.dumps({"scripts": {"test": "jest"}}))
        self.write("tsconfig.json", "{}")
        code, r = self.detect()
        self.assertEqual(self.cmds(r, "test"), ["npm test"])
        self.assertEqual(self.cmds(r, "typecheck"), ["npx tsc --noEmit"])

    def test_python_uv(self):
        self.write("pyproject.toml", "[tool.pytest.ini_options]\n[tool.ruff]\n[tool.mypy]\n")
        self.write("uv.lock")
        code, r = self.detect()
        self.assertEqual(self.cmds(r, "test"), ["uv run pytest"])
        self.assertEqual(self.cmds(r, "lint"), ["uv run ruff check ."])
        self.assertEqual(self.cmds(r, "typecheck"), ["uv run mypy ."])

    def test_go_and_make(self):
        self.write("go.mod", "module x\n")
        self.write("Makefile", "VAR := 1\ntest:\n\tgo test ./...\nlint:\n\tgolangci-lint run\n")
        code, r = self.detect()
        self.assertIn("go test ./...", self.cmds(r, "test"))
        self.assertIn("make test", self.cmds(r, "test"))
        self.assertIn("make lint", self.cmds(r, "lint"))

    def test_laravel(self):
        self.write("composer.json", json.dumps({"scripts": {}}))
        self.write("phpunit.xml")
        self.write("artisan")
        code, r = self.detect()
        self.assertEqual(self.cmds(r, "test"), ["vendor/bin/phpunit", "php artisan test"])

    def test_ci_steps(self):
        self.write(".github/workflows/ci.yml",
                   "jobs:\n  t:\n    steps:\n      - run: npm ci\n      - run: npm test\n"
                   "      - name: e2e\n        run: |\n          npx playwright install\n          npx playwright test\n")
        code, r = self.detect()
        self.assertEqual(self.cmds(r, "ci"), ["npm test", "npx playwright install", "npx playwright test"])

    def test_empty_repo(self):
        code, r = self.detect()
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
