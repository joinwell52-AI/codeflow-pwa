# 仓库协作与整洁约定

多人改同一仓库时，按下面约定可减少分叉、冲突和杂文件。

## 分支

| 分支 | 用途 |
|------|------|
| **`main`** | **唯一主分支**：日常开发、合并、推送均在此分支；与 GitHub 默认分支一致。 |

**不要再使用或新建 `master`**（历史遗留的双分支已废弃，避免与 `main` 重复、分叉）。

**推送习惯：**

```bash
git checkout main
git pull origin main
# …开发、提交…
git push origin main
```

## 不要提交的内容

- **`_pages_tmp/`**：本地静态快照，**勿提交**；以 `web/pwa/`、`docs/`、根目录同步副本为准。
- **桌面端调试图**：`*_crop.png`、`test_*.png`、`cursor_screenshot.png`、`cursor_vision_report.json`、`_test_layout.py` 等（已列入 `.gitignore`）。
- **凭据**：`.git-credentials`、Token、内网账号密码；勿写进仓库文件。
- **`dist/`、`build/`**：构建产物（已忽略）。

## 命名（历史兼容）

- **产品名**：**码流（CodeFlow）**。
- **目录名**：`codeflow-desktop/`、`CodeFlow.json` 等为历史遗留文件名；新配置优先 **`codeflow.json`**、**`codeflow-nudger.json`**（见配置参考）。

## 冲突多时以谁为准

- **约定**：以 **`main` 上已合并、已测试的最新提交**为准。

## 相关文档

- [github-repo-about.md](github-repo-about.md) — GitHub 网页 About / Topics
- 根目录 [README.md](../README.md)、[CHANGELOG.md](../CHANGELOG.md)
