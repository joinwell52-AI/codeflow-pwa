# Repository Collaboration and Hygiene

When several people work on the same repo, the conventions below reduce unnecessary forks, merge conflicts, and stray files.

## Branches

| Branch | Purpose |
|--------|---------|
| **`main`** | **The only default branch**: day-to-day development, merges, and pushes are done here; aligned with GitHub’s default branch. |

**Do not use or create `master` anymore** (the legacy dual-branch setup is deprecated; avoid duplicating or diverging from `main`).

**Push habit:**

```bash
git checkout main
git pull origin main
# …开发、提交…
git push origin main
```

## Do Not Commit

- **`_pages_tmp/`**: local static snapshots — **do not commit**; treat `web/pwa/`, `docs/`, and root-level synced copies as source of truth.
- **Desktop debug artifacts**: `*_crop.png`, `test_*.png`, `cursor_screenshot.png`, `cursor_vision_report.json`, `_test_layout.py`, etc. (already in `.gitignore`).
- **Credentials**: `.git-credentials`, tokens, internal account passwords — do not put them in repo files.
- **`dist/`, `build/`**: build outputs (ignored).

## Naming (historical compatibility)

- **Product name**: **码流（CodeFlow）**.
- **Directory names**: `codeflow-desktop/`, `CodeFlow.json`, etc. are legacy; prefer new configs **`codeflow.json`**, **`codeflow-nudger.json`** (see configuration references).

## When There Are Many Conflicts

- **Convention**: the **latest merged, tested commit on `main`** wins.

## Related Docs

- [github-repo-about.md](github-repo-about.md) — GitHub web About / Topics
- Root [README.md](../README.md), [CHANGELOG.md](../CHANGELOG.md)
