from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "update_profile.py"
SPEC = importlib.util.spec_from_file_location("update_profile", SCRIPT)
assert SPEC and SPEC.loader
update_profile = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = update_profile
SPEC.loader.exec_module(update_profile)


class FakeClient:
    def __init__(self) -> None:
        self.repositories = {"known", "ignored", "new-repository"}
        self.modules = {("known", "packages"): {"packages/core", "packages/new"}}

    def latest_commit(self, owner, source):
        del owner, source
        return None

    def public_repositories(self, owner):
        del owner
        return self.repositories

    def module_directories(self, owner, repository, root):
        del owner
        return self.modules[(repository, root)]


def project(project_id: str, group: str) -> object:
    return update_profile.Project(
        id=project_id,
        name=project_id,
        group=group,
        summary=f"Summary for {project_id}",
        url=f"https://example.com/{project_id}",
        sources=(update_profile.Source(repository=project_id, paths=()),),
    )


class ProfileUpdaterTests(unittest.TestCase):
    def test_selection_limits_each_group(self):
        config = update_profile.Config(
            owner="owner",
            limit=3,
            max_per_group=1,
            active_within_days=90,
            projects=(),
            module_roots=(),
            ignored_repositories=frozenset(),
        )
        activity = (
            update_profile.Activity(project("a-new", "a"), date(2026, 9, 3)),
            update_profile.Activity(project("a-old", "a"), date(2026, 9, 2)),
            update_profile.Activity(project("b", "b"), date(2026, 9, 1)),
            update_profile.Activity(project("c", "c"), date(2026, 8, 30)),
        )

        selected = update_profile.select_lately(config, activity, date(2026, 9, 3))

        self.assertEqual([item.project.id for item in selected], ["a-new", "b", "c"])

    def test_generated_section_preserves_surrounding_content(self):
        readme = f"before\n{update_profile.START_MARKER}\nold\n{update_profile.END_MARKER}\nafter\n"

        result = update_profile.replace_generated_section(readme, "new")

        self.assertEqual(
            result,
            f"before\n{update_profile.START_MARKER}\nnew\n{update_profile.END_MARKER}\nafter\n",
        )

    def test_generated_section_requires_one_marker_pair(self):
        with self.assertRaisesRegex(RuntimeError, "exactly one"):
            update_profile.replace_generated_section("no markers", "new")

    def test_discovery_reports_new_repositories_and_modules(self):
        config = update_profile.Config(
            owner="owner",
            limit=1,
            max_per_group=1,
            active_within_days=90,
            projects=(
                update_profile.Project(
                    id="core",
                    name="Core",
                    group="known",
                    summary="Core",
                    url="https://example.com/core",
                    sources=(
                        update_profile.Source(
                            repository="known",
                            paths=("packages/core",),
                        ),
                    ),
                ),
            ),
            module_roots=(
                update_profile.ModuleRoot(
                    repository="known",
                    roots=("packages",),
                    ignored_paths=frozenset(),
                ),
            ),
            ignored_repositories=frozenset({"ignored"}),
        )

        report = update_profile.discover_unclassified(config, FakeClient())

        self.assertEqual(report.repositories, ("new-repository",))
        self.assertEqual(report.modules, (("known", "packages/new"),))

    def test_markdown_escapes_table_separators(self):
        item = update_profile.Activity(project("one|two", "group"), date(2026, 9, 3))

        result = update_profile.render_lately((item,))

        self.assertIn("one\\|two", result)


def date(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


if __name__ == "__main__":
    unittest.main()
