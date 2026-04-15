# CodeFlow Desktop Release Process

## Overview

CodeFlow Desktop uses an **end-to-end release pipeline**: one command runs every step from version checks to multi-platform publishing.

```
release.cmd <version>
```

## Pre-release preparation (manual)

Before each release, complete these three steps manually:

### 1. Update the version number

Edit `codeflow-desktop/main.py`:

```python
VERSION = "2.10.0"  # ← Change to the new version number
```

### 2. Write the CHANGELOG

At the top of `CHANGELOG.md` (below `[Unreleased]`), add a version entry:

```markdown
## [2.10.0] - 2026-04-14

### Desktop (`codeflow-desktop`)

#### Added: feature title

- Change detail 1
- Change detail 2
```

### 3. Save your work

Ensure all code changes are saved. `release.cmd` will run `git add -A` and commit automatically.

---

## End-to-end flow (automated by release.cmd)

```
cd codeflow-desktop
release.cmd 2.10.0
```

### Steps

| Step | What it does | On failure |
|------|--------------|------------|
| **[1/8] Pre-checks** | Validate `main.py` VERSION, `CHANGELOG.md` entry, `gh` CLI, Gitee token | Abort if missing |
| **[2/8] Build EXE** | `pack.cmd` → PyInstaller → `dist/CodeFlow-Desktop.exe` | Abort on pack failure |
| **[3/8] Extract release notes** | Pull current version text from CHANGELOG, write `_release_notes.md` | Abort on failure |
| **[4/8] git commit + tag** | `git add -A` → commit → `git tag -a vX.Y.Z` | Skip if no changes; skip if tag exists |
| **[5/8] push origin** | `git push origin main` + `git push origin vX.Y.Z` | Warn and continue |
| **[6/8] GitHub Release** | `gh release create` + upload EXE asset | Warn and continue |
| **[7/8] Gitee sync** | `git push gitee main --tags` + `release.py` creates Release | Warn and continue |
| **[8/8] backup sync** | `git push backup main --tags` | Warn and continue |

### Design principles

- **Steps 1–3 are hard prerequisites**: any failure exits with `exit /b 1`
- **Steps 4–8 are fault-tolerant**: a single step failing does not block later steps; warnings are shown
- **Idempotent**: existing tags or Releases are skipped instead of erroring; safe to re-run

---

## Repository layout

| Remote | URL | Purpose |
|--------|-----|---------|
| `origin` | `github.com/joinwell52-AI/codeflow-pwa` | **Primary** — code + Release + GitHub Pages |
| `gitee` | `gitee.com/joinwell52/cursor-ai` | **China mirror** — code + Release (downloads for users in China) |
| `backup` | `github.com/joinwell52-AI/codehouse` | **Backup** — code-only mirror |

### Push order

```
origin  ─── Push first; triggers GitHub Release
gitee   ─── China mirror sync
backup  ─── Push last; backup only
```

---

## Version numbering

Follow [Semantic Versioning](https://semver.org/lang/zh-CN/):

| Type | Format | Example | When to use |
|------|--------|---------|-------------|
| Major | `X.0.0` | `3.0.0` | Breaking, architecture-level changes |
| Minor | `x.Y.0` | `2.10.0` | New features (e.g. CDP engine) |
| Patch | `x.y.Z` | `2.10.1` | Bug fixes, small improvements |

The version string lives in a single place: the `VERSION` constant in `codeflow-desktop/main.py`.
`release.cmd` checks consistency in step [1/8].

---

## File reference

| File | Role |
|------|------|
| `codeflow-desktop/release.cmd` | End-to-end release entry script |
| `codeflow-desktop/pack.cmd` | Pack sub-script (PyInstaller) |
| `codeflow-desktop/build.spec` | PyInstaller spec |
| `codeflow-desktop/release.py` | GitHub + Gitee Release APIs (invoked by release.cmd) |
| `codeflow-desktop/main.py` | Version definition (`VERSION`) |
| `CHANGELOG.md` | Version history (release.cmd extracts notes from here) |
| `codeflow-desktop/.gitee_token` | Gitee API token (not committed to git) |

---

## Prerequisites

### Required

| Tool | Path | Purpose |
|------|------|---------|
| Python 3.12 | `py -3.12` | Packaging + CHANGELOG extraction |
| PyInstaller | pip install | Build EXE |
| Git | System PATH | Push code |
| GitHub CLI | `C:\Program Files\GitHub CLI\gh.exe` | Create GitHub Release + upload EXE |

### Optional

| Tool | Notes |
|------|-------|
| Gitee Token | In `.gitee_token` or `GITEE_TOKEN`; if missing, Gitee Release is skipped |

### First-time setup

```powershell
# 1. After installing GitHub CLI (https://cli.github.com/), log in
& "C:\Program Files\GitHub CLI\gh.exe" auth login

# 2. Verify git remotes
git remote -v
# You should see origin, gitee, and backup

# 3. Gitee token (place under codeflow-desktop/)
echo "your_gitee_token" > codeflow-desktop/.gitee_token
```

---

## Post-release verification

After a release, a quick smoke check is recommended:

| Check | How |
|-------|-----|
| GitHub Release | Open `https://github.com/joinwell52-AI/codeflow-pwa/releases/tag/vX.Y.Z` and confirm the EXE asset |
| Gitee Release | Open `https://gitee.com/joinwell52/cursor-ai/releases/tag/vX.Y.Z` |
| Auto-update | Launch an older EXE and confirm it prompts for the new version |
| backup | `git log backup/main --oneline -1` to confirm the latest commit |

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `gh` not found | Install path not on PATH | Script hard-codes `C:\Program Files\GitHub CLI\gh.exe` |
| GitHub push rejected | Remote has new commits | `git pull --rebase origin main`, then re-run |
| Gitee push tag rejected | Old tag already exists | `git push gitee :refs/tags/vX.Y.Z` to delete remote tag, then retry |
| EXE too large (>50MB) | Bad pack config | Check `excludes` in `build.spec` |
| Gitee EXE upload fails | File exceeds Gitee free tier | Keep code on Gitee; treat GitHub as source of truth for EXE |
| Release already exists | Duplicate release | `gh release delete vX.Y.Z --repo xxx`, then retry |

---

## Full example

```powershell
# 1. Update version number
#    main.py: VERSION = "2.11.0"

# 2. Write CHANGELOG
#    CHANGELOG.md: ## [2.11.0] - 2026-04-15

# 3. End-to-end release
cd D:\BridgeFlow\codeflow-desktop
release.cmd 2.11.0

# 4. Verify
start https://github.com/joinwell52-AI/codeflow-pwa/releases/tag/v2.11.0
```
