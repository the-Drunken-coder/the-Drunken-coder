# Profile automation

The profile treats repositories and portfolio projects as separate things.
`portfolio.json` is the small interface between project organization and the
generated `Lately` table.

Each project has one or more activity sources. A source may be an entire
repository or a list of paths inside a repository. This lets the profile track
Atlas Core and the Atlas command interface independently without copying either
one into another repository. It also lets the three CVBench repositories appear
as related projects and folds EasyMANET's generated release repositories back
into their source modules.

The daily workflow ranks recent activity, limits each project group to two
entries, updates the marked section of `README.md`, and dates the footer from
the newest selected activity.

## When a new project is created

No setup in the new repository is required. The daily workflow compares every
public repository with `portfolio.json`. It opens or updates one maintenance
issue when it finds either:

- a public repository that is neither a project source nor ignored;
- a new module under one of the watched monorepo roots.

Resolve the issue by adding the work to `projects`, adding the repository to
`ignoredRepositories`, or adding an internal module to `ignoredPaths`. The next
successful run closes the issue when nothing remains unclassified.

Private repositories are intentionally outside this workflow. A public profile
should link to public source, public documentation, or a public demonstration.

## Run it locally

```sh
python3 -m unittest discover -s tests
python3 scripts/update_profile.py --write
```

Set `GITHUB_TOKEN` when authenticated API limits are needed. The script has no
third-party Python dependencies.
