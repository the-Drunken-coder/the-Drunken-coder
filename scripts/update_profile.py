#!/usr/bin/env python3
"""Render the profile's current-project list from explicit portfolio metadata."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

START_MARKER = "<!-- profile:lately:start -->"
END_MARKER = "<!-- profile:lately:end -->"
ISSUE_TITLE = "Classify newly discovered portfolio projects"


class ConfigError(ValueError):
    """Raised when portfolio.json does not satisfy its interface."""


@dataclass(frozen=True)
class Source:
    repository: str
    paths: tuple[str, ...]


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    group: str
    summary: str
    url: str
    sources: tuple[Source, ...]


@dataclass(frozen=True)
class ModuleRoot:
    repository: str
    roots: tuple[str, ...]
    ignored_paths: frozenset[str]


@dataclass(frozen=True)
class Config:
    owner: str
    limit: int
    max_per_group: int
    active_within_days: int
    projects: tuple[Project, ...]
    module_roots: tuple[ModuleRoot, ...]
    ignored_repositories: frozenset[str]

    @property
    def source_repositories(self) -> frozenset[str]:
        return frozenset(
            source.repository
            for project in self.projects
            for source in project.sources
        )


@dataclass(frozen=True)
class Activity:
    project: Project
    occurred_at: datetime


@dataclass(frozen=True)
class DiscoveryReport:
    repositories: tuple[str, ...]
    modules: tuple[tuple[str, str], ...]

    @property
    def is_empty(self) -> bool:
        return not self.repositories and not self.modules


class PortfolioClient(Protocol):
    def latest_commit(self, owner: str, source: Source) -> datetime | None: ...

    def public_repositories(self, owner: str) -> set[str]: ...

    def module_directories(self, owner: str, repository: str, root: str) -> set[str]: ...


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self._token = token

    def _get(self, path: str, parameters: dict[str, str | int] | None = None) -> Any:
        query = urllib.parse.urlencode(parameters or {})
        url = f"https://api.github.com{path}"
        if query:
            url = f"{url}?{query}"

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "the-Drunken-coder-profile-updater",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub returned {error.code} for {path}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Could not reach GitHub for {path}: {error.reason}") from error

    def latest_commit(self, owner: str, source: Source) -> datetime | None:
        paths: tuple[str | None, ...] = source.paths or (None,)
        dates: list[datetime] = []
        for path in paths:
            parameters: dict[str, str | int] = {"per_page": 1}
            if path is not None:
                parameters["path"] = path
            commits = self._get(
                f"/repos/{owner}/{source.repository}/commits",
                parameters,
            )
            if not commits:
                continue
            commit = commits[0]["commit"]
            date = commit.get("committer", {}).get("date") or commit["author"]["date"]
            dates.append(parse_github_date(date))
        return max(dates) if dates else None

    def public_repositories(self, owner: str) -> set[str]:
        repositories: set[str] = set()
        page = 1
        while True:
            result = self._get(
                f"/users/{owner}/repos",
                {"type": "owner", "per_page": 100, "page": page},
            )
            repositories.update(repository["name"] for repository in result)
            if len(result) < 100:
                return repositories
            page += 1

    def module_directories(self, owner: str, repository: str, root: str) -> set[str]:
        entries = self._get(f"/repos/{owner}/{repository}/contents/{root}")
        return {entry["path"] for entry in entries if entry["type"] == "dir"}


def parse_github_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{field} must be a non-empty string")
    return value


def _require_relative_path(value: Any, field: str) -> str:
    path = _require_string(value, field)
    if path.startswith("/") or ".." in Path(path).parts:
        raise ConfigError(f"{field} must be a repository-relative path")
    return path.rstrip("/")


def load_config(path: Path) -> Config:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schemaVersion") != 1:
        raise ConfigError("schemaVersion must be 1")

    owner = _require_string(raw.get("owner"), "owner")
    lately = raw.get("lately")
    if not isinstance(lately, dict):
        raise ConfigError("lately must be an object")
    limit = lately.get("limit")
    max_per_group = lately.get("maxPerGroup")
    active_within_days = lately.get("activeWithinDays")
    if not isinstance(limit, int) or limit < 1:
        raise ConfigError("lately.limit must be a positive integer")
    if not isinstance(max_per_group, int) or max_per_group < 1:
        raise ConfigError("lately.maxPerGroup must be a positive integer")
    if not isinstance(active_within_days, int) or active_within_days < 1:
        raise ConfigError("lately.activeWithinDays must be a positive integer")

    projects: list[Project] = []
    project_ids: set[str] = set()
    for index, item in enumerate(raw.get("projects", [])):
        if not isinstance(item, dict):
            raise ConfigError(f"projects[{index}] must be an object")
        project_id = _require_string(item.get("id"), f"projects[{index}].id")
        if project_id in project_ids:
            raise ConfigError(f"duplicate project id: {project_id}")
        project_ids.add(project_id)

        sources: list[Source] = []
        for source_index, source in enumerate(item.get("sources", [])):
            if not isinstance(source, dict):
                raise ConfigError(
                    f"projects[{index}].sources[{source_index}] must be an object"
                )
            repository = _require_string(
                source.get("repository"),
                f"projects[{index}].sources[{source_index}].repository",
            )
            raw_paths = source.get("paths", [])
            if not isinstance(raw_paths, list):
                raise ConfigError(
                    f"projects[{index}].sources[{source_index}].paths must be an array"
                )
            paths = tuple(
                _require_relative_path(
                    value,
                    f"projects[{index}].sources[{source_index}].paths[{path_index}]",
                )
                for path_index, value in enumerate(raw_paths)
            )
            sources.append(Source(repository=repository, paths=paths))
        if not sources:
            raise ConfigError(f"projects[{index}].sources must not be empty")

        projects.append(
            Project(
                id=project_id,
                name=_require_string(item.get("name"), f"projects[{index}].name"),
                group=_require_string(item.get("group"), f"projects[{index}].group"),
                summary=_require_string(
                    item.get("summary"), f"projects[{index}].summary"
                ),
                url=_require_string(item.get("url"), f"projects[{index}].url"),
                sources=tuple(sources),
            )
        )

    if not projects:
        raise ConfigError("projects must not be empty")

    module_roots: list[ModuleRoot] = []
    for index, item in enumerate(raw.get("moduleRoots", [])):
        if not isinstance(item, dict):
            raise ConfigError(f"moduleRoots[{index}] must be an object")
        roots = item.get("roots", [])
        ignored_paths = item.get("ignoredPaths", [])
        if not isinstance(roots, list) or not roots:
            raise ConfigError(f"moduleRoots[{index}].roots must be a non-empty array")
        if not isinstance(ignored_paths, list):
            raise ConfigError(f"moduleRoots[{index}].ignoredPaths must be an array")
        module_roots.append(
            ModuleRoot(
                repository=_require_string(
                    item.get("repository"), f"moduleRoots[{index}].repository"
                ),
                roots=tuple(
                    _require_relative_path(root, f"moduleRoots[{index}].roots")
                    for root in roots
                ),
                ignored_paths=frozenset(
                    _require_relative_path(
                        ignored, f"moduleRoots[{index}].ignoredPaths"
                    )
                    for ignored in ignored_paths
                ),
            )
        )

    ignored_raw = raw.get("ignoredRepositories", [])
    if not isinstance(ignored_raw, list):
        raise ConfigError("ignoredRepositories must be an array")
    ignored_repositories = frozenset(
        _require_string(value, "ignoredRepositories") for value in ignored_raw
    )

    config = Config(
        owner=owner,
        limit=limit,
        max_per_group=max_per_group,
        active_within_days=active_within_days,
        projects=tuple(projects),
        module_roots=tuple(module_roots),
        ignored_repositories=ignored_repositories,
    )
    overlap = config.source_repositories & config.ignored_repositories
    if overlap:
        raise ConfigError(
            "repositories cannot be both project sources and ignored: "
            + ", ".join(sorted(overlap, key=str.casefold))
        )
    return config


def collect_activity(config: Config, client: PortfolioClient) -> tuple[Activity, ...]:
    activity: list[Activity] = []
    for project in config.projects:
        dates = [
            date
            for source in project.sources
            if (date := client.latest_commit(config.owner, source)) is not None
        ]
        if dates:
            activity.append(Activity(project=project, occurred_at=max(dates)))
    return tuple(activity)


def select_lately(
    config: Config,
    activity: tuple[Activity, ...],
    now: datetime,
) -> tuple[Activity, ...]:
    cutoff = now.astimezone(timezone.utc) - timedelta(days=config.active_within_days)
    ranked = sorted(
        (item for item in activity if item.occurred_at >= cutoff),
        key=lambda item: (-item.occurred_at.timestamp(), item.project.id),
    )
    selected: list[Activity] = []
    group_counts: dict[str, int] = {}
    for item in ranked:
        count = group_counts.get(item.project.group, 0)
        if count >= config.max_per_group:
            continue
        selected.append(item)
        group_counts[item.project.group] = count + 1
        if len(selected) == config.limit:
            break
    return tuple(selected)


def markdown_text(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def render_lately(selected: tuple[Activity, ...]) -> str:
    lines = ["| Project | Notes |", "|:--|:--|"]
    for item in selected:
        project = item.project
        lines.append(
            f"| [**{markdown_text(project.name)}**]({project.url}) "
            f"| {markdown_text(project.summary)} |"
        )
    return "\n".join(lines)


def replace_generated_section(readme: str, rendered: str) -> str:
    if readme.count(START_MARKER) != 1 or readme.count(END_MARKER) != 1:
        raise RuntimeError("README must contain exactly one Lately marker pair")
    before, remainder = readme.split(START_MARKER, 1)
    _, after = remainder.split(END_MARKER, 1)
    return f"{before}{START_MARKER}\n{rendered}\n{END_MARKER}{after}"


def discover_unclassified(
    config: Config,
    client: PortfolioClient,
) -> DiscoveryReport:
    known_repositories = config.source_repositories | config.ignored_repositories
    repositories = tuple(
        sorted(
            client.public_repositories(config.owner) - known_repositories,
            key=str.casefold,
        )
    )

    registered_paths = {
        (source.repository, path)
        for project in config.projects
        for source in project.sources
        for path in source.paths
    }
    modules: list[tuple[str, str]] = []
    for module_root in config.module_roots:
        ignored = module_root.ignored_paths
        for root in module_root.roots:
            directories = client.module_directories(
                config.owner,
                module_root.repository,
                root,
            )
            for path in directories:
                if path in ignored:
                    continue
                if (module_root.repository, path) not in registered_paths:
                    modules.append((module_root.repository, path))

    return DiscoveryReport(
        repositories=repositories,
        modules=tuple(sorted(set(modules), key=lambda item: (item[0].casefold(), item[1]))),
    )


def render_discovery_report(config: Config, report: DiscoveryReport) -> str:
    if report.is_empty:
        return ""

    lines = [
        "The profile updater found public work that has no portfolio decision.",
        "",
        "Add each item to `projects` or the appropriate ignore list in "
        "`portfolio.json`. The next successful run will update or close this issue.",
    ]
    if report.repositories:
        lines.extend(["", "## Repositories", ""])
        lines.extend(
            f"- [{repository}](https://github.com/{config.owner}/{repository})"
            for repository in report.repositories
        )
    if report.modules:
        lines.extend(["", "## Monorepo modules", ""])
        lines.extend(
            f"- [{repository} / {path}]"
            f"(https://github.com/{config.owner}/{repository}/tree/main/{path})"
            for repository, path in report.modules
        )
    lines.extend(["", "<!-- Generated by scripts/update_profile.py. -->", ""])
    return "\n".join(lines)


def update_footer(readme: str, selected: tuple[Activity, ...]) -> str:
    if not selected:
        return readme
    latest = max(item.occurred_at for item in selected)
    value = f"<sub>Updated {latest.day} {latest.strftime('%b %Y')}</sub>"
    lines = readme.splitlines()
    matches = [index for index, line in enumerate(lines) if line.startswith("<sub>Updated ")]
    if len(matches) != 1:
        raise RuntimeError("README must contain exactly one Updated footer")
    lines[matches[0]] = value
    return "\n".join(lines) + ("\n" if readme.endswith("\n") else "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("portfolio.json"))
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--write", action="store_true", help="write the generated README")
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if README does not match current project activity",
    )
    parser.add_argument(
        "--unclassified-output",
        type=Path,
        help="write the maintenance issue body, or an empty file when all work is classified",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.write and args.check:
        raise SystemExit("--write and --check are mutually exclusive")

    config = load_config(args.config)
    client = GitHubClient(os.environ.get("GITHUB_TOKEN"))
    activity = collect_activity(config, client)
    selected = select_lately(config, activity, datetime.now(timezone.utc))

    current = args.readme.read_text(encoding="utf-8")
    generated = replace_generated_section(current, render_lately(selected))
    generated = update_footer(generated, selected)

    if args.write:
        args.readme.write_text(generated, encoding="utf-8")
    elif args.check and generated != current:
        print("README.md is out of date; run scripts/update_profile.py --write", file=sys.stderr)
        return 1
    else:
        print(render_lately(selected))

    report = discover_unclassified(config, client)
    if args.unclassified_output:
        args.unclassified_output.write_text(
            render_discovery_report(config, report),
            encoding="utf-8",
        )
    if not report.is_empty:
        print(
            f"Found {len(report.repositories)} unclassified repositories and "
            f"{len(report.modules)} unclassified modules.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
