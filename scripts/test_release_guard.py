"""Unit tests for the pure parts of scripts/release_guard.py (no git).

Run from the repository root: python3 -m unittest scripts/test_release_guard.py
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import release_guard as rg  # noqa: E402


def package_json(version: str) -> str:
    return json.dumps({"name": "frontend", "version": version, "private": True}, indent=2) + "\n"


def package_lock(version: str, dep_version: str = "1.2.3") -> str:
    data = {
        "name": "frontend",
        "version": version,
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "frontend", "version": version, "dependencies": {"left-pad": "^1.0.0"}},
            "node_modules/left-pad": {"version": dep_version},
        },
    }
    return json.dumps(data, indent=2) + "\n"


def pyproject(version: str, extra: str = "") -> str:
    return f'[project]\nname = "permitflow-backend"\nversion = "{version}"\n{extra}'


def uv_lock(version: str) -> str:
    return (
        'version = 1\n\n[[package]]\nname = "annotated-types"\nversion = "0.7.0"\n\n'
        f'[[package]]\nname = "permitflow-backend"\nversion = "{version}"\nsource = {{ editable = "." }}\n'
    )


def version_py(version: str) -> str:
    return f'"""doc"""\n\nimport os\n\nAPP_VERSION = "{version}"\nBUILD_COMMIT = "x"\n'


def release_files(semver: str) -> dict[str, str | None]:
    py = rg.pep440(semver)
    return {
        "frontend/package.json": package_json(semver),
        "frontend/package-lock.json": package_lock(semver),
        "backend/pyproject.toml": pyproject(py),
        "backend/uv.lock": uv_lock(py),
        "backend/app/core/version.py": version_py(semver),
    }


class ParseTagTests(unittest.TestCase):
    def test_release(self) -> None:
        tag = rg.parse_tag("v0.4.1")
        self.assertIsNotNone(tag)
        assert tag is not None
        self.assertEqual((tag.major, tag.minor, tag.patch, tag.rc), (0, 4, 1, None))
        self.assertEqual(tag.semver, "0.4.1")

    def test_candidate(self) -> None:
        tag = rg.parse_tag("v0.4.1-rc.12")
        assert tag is not None
        self.assertEqual(tag.rc, 12)
        self.assertEqual(tag.semver, "0.4.1-rc.12")
        self.assertEqual(tag.name, "v0.4.1-rc.12")
        self.assertEqual(tag.base, "0.4.1")

    def test_other_shapes_are_rejected(self) -> None:
        for bad in ["0.4.1", "v0.4", "v0.4.1.2", "v0.4.1-rc", "v0.4.1-rc.0", "v0.4.1-beta.1", "v01.4.1", "v0.4.1-rc.1-x", ""]:
            with self.subTest(tag=bad):
                self.assertIsNone(rg.parse_tag(bad))

    def test_pep440(self) -> None:
        self.assertEqual(rg.pep440("0.4.1-rc.2"), "0.4.1rc2")
        self.assertEqual(rg.pep440("0.4.1"), "0.4.1")


class ExtractVersionTests(unittest.TestCase):
    def test_package_json(self) -> None:
        self.assertEqual(rg.extract_versions("frontend/package.json", package_json("0.4.1-rc.1")), ["0.4.1-rc.1"])

    def test_package_lock_has_two_entries_and_ignores_dependencies(self) -> None:
        got = rg.extract_versions("frontend/package-lock.json", package_lock("0.4.1", dep_version="9.9.9"))
        self.assertEqual(got, ["0.4.1", "0.4.1"])

    def test_pyproject(self) -> None:
        self.assertEqual(rg.extract_versions("backend/pyproject.toml", pyproject("0.4.1rc1")), ["0.4.1rc1"])

    def test_uv_lock_reads_only_the_backend_package(self) -> None:
        self.assertEqual(rg.extract_versions("backend/uv.lock", uv_lock("0.4.1rc2")), ["0.4.1rc2"])

    def test_version_py(self) -> None:
        self.assertEqual(rg.extract_versions("backend/app/core/version.py", version_py("0.4.1-rc.1")), ["0.4.1-rc.1"])

    def test_unknown_file(self) -> None:
        with self.assertRaises(ValueError):
            rg.extract_versions("README.md", "x")


class VersionProblemTests(unittest.TestCase):
    def test_all_five_match(self) -> None:
        self.assertEqual(rg.version_problems(release_files("0.4.1-rc.2"), "0.4.1-rc.2", "v0.4.1-rc.2"), [])
        self.assertEqual(rg.version_problems(release_files("0.4.1"), "0.4.1", "v0.4.1"), [])

    def test_one_file_behind_fails(self) -> None:
        files = release_files("0.4.1-rc.2")
        files["backend/uv.lock"] = uv_lock("0.4.1rc1")
        problems = rg.version_problems(files, "0.4.1-rc.2", "v0.4.1-rc.2")
        self.assertEqual(len(problems), 1)
        self.assertIn("backend/uv.lock", problems[0])

    def test_pep440_form_is_required_for_python_files(self) -> None:
        files = release_files("0.4.1-rc.2")
        files["backend/pyproject.toml"] = pyproject("0.4.1-rc.2")
        self.assertEqual(len(rg.version_problems(files, "0.4.1-rc.2", "t")), 1)

    def test_missing_file_fails(self) -> None:
        files = release_files("0.4.1")
        files["frontend/package.json"] = None
        self.assertIn("missing", rg.version_problems(files, "0.4.1", "t")[0])

    def test_one_lock_entry_behind_fails(self) -> None:
        files = release_files("0.4.1")
        files["frontend/package-lock.json"] = package_lock("0.4.1").replace('"version": "0.4.1",\n      "dependencies"', '"version": "0.4.0",\n      "dependencies"')
        self.assertEqual(len(rg.version_problems(files, "0.4.1", "t")), 1)


class ShippedFilterTests(unittest.TestCase):
    def test_shipped_paths(self) -> None:
        for path in ["backend/app/main.py", "frontend/src/App.tsx", "docker/observability/alerts.yml", "docker-compose.yml"]:
            with self.subTest(path=path):
                self.assertTrue(rg.is_shipped(path))

    def test_not_shipped_paths(self) -> None:
        for path in ["docs/a.md", "README.md", "RELEASE_NOTES.md", "CHANGELOG.md", ".github/workflows/ci.yml", "scripts/release_guard.py", "backendx/a.py"]:
            with self.subTest(path=path):
                self.assertFalse(rg.is_shipped(path))

    def test_version_files_are_exempt(self) -> None:
        changed = list(rg.VERSION_FILES) + ["docs/x.md", "backend/app/api/x.py", "frontend/src/y.ts"]
        self.assertEqual(rg.shipped_changes(changed), ["backend/app/api/x.py", "frontend/src/y.ts"])


class LineDiffTests(unittest.TestCase):
    def test_only_version_lines_changed_passes(self) -> None:
        old, new = release_files("0.4.1-rc.2"), release_files("0.4.1")
        for path in rg.VERSION_FILES:
            with self.subTest(path=path):
                problems = rg.version_line_diff_problems(
                    path,
                    old[path] or "",
                    new[path] or "",
                    rg.expected_version(path, "0.4.1-rc.2"),
                    rg.expected_version(path, "0.4.1"),
                )
                self.assertEqual(problems, [])

    def test_extra_changed_line_fails(self) -> None:
        old = pyproject("0.4.1rc2", 'dependencies = ["a>=1"]\n')
        new = pyproject("0.4.1", 'dependencies = ["a>=2"]\n')
        problems = rg.version_line_diff_problems("backend/pyproject.toml", old, new, "0.4.1rc2", "0.4.1")
        self.assertTrue(problems)

    def test_extra_changed_dependency_in_lock_fails(self) -> None:
        old = package_lock("0.4.1-rc.2", dep_version="1.2.3")
        new = package_lock("0.4.1", dep_version="1.2.4")
        problems = rg.version_line_diff_problems("frontend/package-lock.json", old, new, "0.4.1-rc.2", "0.4.1")
        self.assertTrue(problems)

    def test_version_going_somewhere_else_fails(self) -> None:
        problems = rg.version_line_diff_problems(
            "backend/app/core/version.py", version_py("0.4.1-rc.2"), version_py("0.5.0"), "0.4.1-rc.2", "0.4.1"
        )
        self.assertTrue(problems)

    def test_changed_non_version_line_with_same_count_fails(self) -> None:
        old = version_py("0.4.1-rc.2")
        new = old.replace('APP_VERSION = "0.4.1-rc.2"', 'APP_VERSION = "0.4.1"').replace('BUILD_COMMIT = "x"', 'BUILD_COMMIT = "y"')
        problems = rg.version_line_diff_problems("backend/app/core/version.py", old, new, "0.4.1-rc.2", "0.4.1")
        self.assertTrue(problems)

    def test_unchanged_file_fails(self) -> None:
        text = version_py("0.4.1-rc.2")
        self.assertTrue(rg.version_line_diff_problems("backend/app/core/version.py", text, text, "0.4.1-rc.2", "0.4.1"))


class HighestCandidateTests(unittest.TestCase):
    def test_numeric_not_lexical(self) -> None:
        best = rg.highest_candidate(["v0.4.1-rc.2", "v0.4.1-rc.10", "v0.4.1-rc.1"], "0.4.1")
        assert best is not None
        self.assertEqual(best.name, "v0.4.1-rc.10")

    def test_other_versions_and_releases_ignored(self) -> None:
        self.assertIsNone(rg.highest_candidate(["v0.4.0-rc.3", "v0.4.1", "junk"], "0.4.1"))


if __name__ == "__main__":
    unittest.main()
