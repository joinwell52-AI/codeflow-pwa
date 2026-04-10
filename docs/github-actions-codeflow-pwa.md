# codeflow-pwa 仓库 · GitHub Actions 失败说明

## 现象（与通知一致）

- **「部署 PWA 到 GitHub Pages」** 在 **`main`** 上失败  
- **「发布到 PyPI」** 在 **`v1.9.6` 等 tag** 上失败  

## 根因（高概率）

`joinwell52-ai/codeflow-pwa` 是 **PWA 静态站仓库**（根目录一般为 `index.html`、`config.js`、`sw.js`、`manifest.json` 等），**没有** `web/pwa/` 目录，也**没有** 可发布的 Python 包（无根目录 `pyproject.toml`）。

若把 **主仓库 `CodeFlow`** 里的工作流 **原样复制** 到 `codeflow-pwa`，会出现：

| 工作流 | 在主仓库 CodeFlow 里的作用 | 放到 codeflow-pwa 后的问题 |
|--------|-------------------------------|----------------------------|
| `deploy-pwa.yml` | 把 `web/pwa/` **推送到外仓** `codeflow-pwa` | 在 codeflow-pwa 内 **`publish_dir: ./web/pwa` 不存在** → 部署失败 |
| `publish.yml` | `python -m build` **发布 PyPI** | 无 `pyproject.toml` → **构建/上传失败** |

另外：若 **`PAGES_DEPLOY_TOKEN`** 未配置或无权访问 `codeflow-pwa`，主仓库侧的「部署 PWA」也会失败（需在 **CodeFlow** 仓库 Secrets 里配置）。

## 推荐修复（在 GitHub 上手动操作）

### A. 仓库 `joinwell52-ai/codeflow-pwa`（PWA 专仓）

1. 打开 **Actions**，进入失败的工作流。  
2. **删除或禁用** 不适合本仓库的工作流文件（在 **`codeflow-pwa`** 仓库内编辑）：  
   - 建议 **删除** `发布到 PyPI`（`publish.yml` 或同名），除非你真的在该仓库里维护 Python 包。  
   - 建议 **删除**「同步到外仓」类部署（与主仓 `deploy-pwa.yml` 同逻辑、且带 `external_repository` / `web/pwa` 的那份），除非你明确需要在本仓再跑一遍。  
3. **GitHub Pages**：在 **Settings → Pages** 中，一般选 **Source: Deploy from a branch**，**Branch: `main`**，**Folder: `/ (root)`**（与 peaceiris 推上来的静态文件一致即可）。**不一定需要** Actions 才能出站。

> 静态 PWA **只开 Pages 即可**；不必在 codeflow-pwa 里再跑一遍「从 web/pwa 部署到外仓」的流程。

### B. 仓库 `CodeFlow`（主仓库，若你要从主仓推送到 codeflow-pwa）

1. **Settings → Secrets and variables → Actions**  
2. 配置 **`PAGES_DEPLOY_TOKEN`**：PAT 需对 **`joinwell52-ai/codeflow-pwa`** 有 **push** 权限。  
3. 确认工作流 **`.github/workflows/deploy-pwa.yml`** 里 **`external_repository: joinwell52-ai/codeflow-pwa`**、**`publish_branch: main`** 与目标一致。  

### C. 关于 tag `v1.9.6` 触发 PyPI

若在 **codeflow-pwa** 上打了 **`v*`** tag，会触发 **publish.yml**。若不需要在该仓发 PyPI，请 **勿在 codeflow-pwa 打用于 PyPI 的 tag**，或 **删除该仓库的 publish 工作流**。

---

## 小结

| 仓库 | 建议 |
|------|------|
| **codeflow-pwa** | 删掉 **PyPI** 与 **错误的「web/pwa 部署」** 工作流；用 **Pages 分支发布** 即可。 |
| **CodeFlow** | 保留「推送到 codeflow-pwa」的 deploy（若仍用）；配好 **PAGES_DEPLOY_TOKEN**。 |

排查时请看失败 job 日志里是否出现 **`No such file or directory: web/pwa`** 或 **`python -m build` / `pyproject.toml` 缺失** —— 与上文一致则可按上表处理。
