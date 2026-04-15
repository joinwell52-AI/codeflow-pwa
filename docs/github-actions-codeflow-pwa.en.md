# codeflow-pwa repo · GitHub Actions failure notes

## Symptoms (aligned with notifications)

- **“Deploy PWA to GitHub Pages”** fails on **`main`**
- **“Publish to PyPI”** fails on **`v1.9.6`** and similar **tags**

## Root cause (high probability)

`joinwell52-ai/codeflow-pwa` is a **PWA static-site repo** (root usually has `index.html`, `config.js`, `sw.js`, `manifest.json`, etc.). It **does not** have a `web/pwa/` directory and **does not** have a publishable Python package (no root `pyproject.toml`).

If you **copy workflows verbatim** from the **main `CodeFlow` repo** into `codeflow-pwa`, you get:

| Workflow | Role in main CodeFlow repo | Problem when placed in codeflow-pwa |
|----------|------------------------------|-------------------------------------|
| `deploy-pwa.yml` | Pushes `web/pwa/` **to the external repo** `codeflow-pwa` | Inside codeflow-pwa, **`publish_dir: ./web/pwa` does not exist** → deploy fails |
| `publish.yml` | `python -m build` **publishes to PyPI** | No `pyproject.toml` → **build/upload fails** |

Also: if **`PAGES_DEPLOY_TOKEN`** is not set or lacks access to `codeflow-pwa`, “Deploy PWA” from the main repo will fail too (configure in **CodeFlow** repo **Secrets**).

## Recommended fix (manual steps on GitHub)

### A. Repo `joinwell52-ai/codeflow-pwa` (PWA-only)

1. Open **Actions** and open the failed workflow run.
2. **Delete or disable** workflow files that do not fit this repo (edit inside the **`codeflow-pwa`** repo):
   - Prefer **deleting** “Publish to PyPI” (`publish.yml` or equivalent) unless you actually maintain a Python package in that repo.
   - Prefer **deleting** “sync to external repo” style deploys (same logic as main repo `deploy-pwa.yml`, with `external_repository` / `web/pwa`) unless you explicitly need to run that again in this repo.
3. **GitHub Pages**: under **Settings → Pages**, typically choose **Source: Deploy from a branch**, **Branch: `main`**, **Folder: `/ (root)`** (consistent with static files pushed by peaceiris). **You do not necessarily need** Actions for outbound hosting.

> For a static PWA, **Pages alone is enough**; you do not need to run “deploy from web/pwa to external repo” again inside codeflow-pwa.

### B. Repo `CodeFlow` (main repo, if you push from main to codeflow-pwa)

1. **Settings → Secrets and variables → Actions**
2. Configure **`PAGES_DEPLOY_TOKEN`**: the PAT must have **push** to **`joinwell52-ai/codeflow-pwa`**.
3. Confirm workflow **`.github/workflows/deploy-pwa.yml`** has **`external_repository: joinwell52-ai/codeflow-pwa`**, **`publish_branch: main`**, matching your target.

### C. Tag `v1.9.6` triggering PyPI

If you create a **`v*`** tag on **codeflow-pwa**, it triggers **publish.yml**. If you do not need PyPI from that repo, **do not tag for PyPI on codeflow-pwa**, or **remove the publish workflow** from that repo.

---

## Summary

| Repo | Recommendation |
|------|----------------|
| **codeflow-pwa** | Remove **PyPI** and the incorrect **“web/pwa deploy”** workflows; **publish via Pages branch** is enough. |
| **CodeFlow** | Keep the deploy that **pushes to codeflow-pwa** (if still used); configure **`PAGES_DEPLOY_TOKEN`**. |

When triaging, check failed job logs for **`No such file or directory: web/pwa`** or missing **`python -m build` / `pyproject.toml`** — if it matches above, handle per the table.
