# CodeFlow Desktop 发版规范

## 概述

CodeFlow Desktop 采用**一条龙发版流程**：一条命令完成从版本号校验到多平台发布的全部步骤。

```
release.cmd <版本号>
```

## 发版前准备（手动）

每次发版前需要手动完成以下三步：

### 1. 修改版本号

编辑 `codeflow-desktop/main.py`：

```python
VERSION = "2.10.0"  # ← 改成新版本号
```

### 2. 编写 CHANGELOG

在 `CHANGELOG.md` 顶部（`[Unreleased]` 下方）新增版本条目：

```markdown
## [2.10.0] - 2026-04-14

### 桌面端（`codeflow-desktop`）

#### 新增：功能标题

- 具体改动 1
- 具体改动 2
```

### 3. 提交代码

确保所有代码改动已保存。`release.cmd` 会自动 `git add -A` 并提交。

---

## 一条龙流程（release.cmd 自动执行）

```
cd codeflow-desktop
release.cmd 2.10.0
```

### 执行步骤

| 步骤 | 内容 | 失败处理 |
|------|------|----------|
| **[1/8] 前置检查** | 校验 `main.py` VERSION、`CHANGELOG.md` 条目、`gh` CLI、Gitee token | 缺少则中止 |
| **[2/8] 打包 EXE** | `pack.cmd` → PyInstaller → `dist/CodeFlow-Desktop.exe` | 打包失败则中止 |
| **[3/8] 提取版本说明** | 从 CHANGELOG 提取当前版本内容，生成 `_release_notes.md` | 失败则中止 |
| **[4/8] git commit + tag** | `git add -A` → commit → `git tag -a vX.Y.Z` | 无改动则跳过，tag 已存在则跳过 |
| **[5/8] push origin** | `git push origin main` + `git push origin vX.Y.Z` | 警告但继续 |
| **[6/8] GitHub Release** | `gh release create` + 上传 EXE 附件 | 警告但继续 |
| **[7/8] Gitee 同步** | `git push gitee main --tags` + `release.py` 创建 Release | 警告但继续 |
| **[8/8] backup 同步** | `git push backup main --tags` | 警告但继续 |

### 设计原则

- **步骤 1-3 是硬性前置**：任何一步失败直接 `exit /b 1`
- **步骤 4-8 尽量容错**：单步失败不阻塞后续步骤，给出警告
- **幂等安全**：tag 已存在、Release 已存在都会跳过而非报错，可重复执行

---

## 仓库结构

| Remote | 地址 | 用途 |
|--------|------|------|
| `origin` | `github.com/joinwell52-AI/codeflow-pwa` | **主仓库**，代码 + Release + GitHub Pages |
| `gitee` | `gitee.com/joinwell52/cursor-ai` | **国内镜像**，代码 + Release（供国内用户下载） |
| `backup` | `github.com/joinwell52-AI/codehouse` | **备份仓库**，纯代码备份 |

### 推送顺序

```
origin  ─── 最先推送，触发 GitHub Release
gitee   ─── 国内镜像同步
backup  ─── 最后推送，纯备份
```

---

## 版本号规范

遵循 [语义化版本](https://semver.org/lang/zh-CN/)：

| 类型 | 格式 | 示例 | 触发场景 |
|------|------|------|----------|
| 主版本 | `X.0.0` | `3.0.0` | 不兼容的架构级变更 |
| 次版本 | `x.Y.0` | `2.10.0` | 新功能（如 CDP 引擎） |
| 修订版 | `x.y.Z` | `2.10.1` | Bug 修复、小优化 |

版本号只存在于一个地方：`codeflow-desktop/main.py` 的 `VERSION` 常量。
`release.cmd` 在步骤 [1/8] 校验两者一致。

---

## 文件清单

| 文件 | 作用 |
|------|------|
| `codeflow-desktop/release.cmd` | 一条龙发版入口脚本 |
| `codeflow-desktop/pack.cmd` | 打包子脚本（PyInstaller） |
| `codeflow-desktop/build.spec` | PyInstaller 打包配置 |
| `codeflow-desktop/release.py` | GitHub + Gitee 双平台 Release API（被 release.cmd 调用） |
| `codeflow-desktop/main.py` | 版本号定义 (`VERSION`) |
| `CHANGELOG.md` | 版本历史（release.cmd 自动从中提取版本说明） |
| `codeflow-desktop/.gitee_token` | Gitee API token（不入 git） |

---

## 前置环境

### 必须

| 工具 | 路径 | 用途 |
|------|------|------|
| Python 3.12 | `py -3.12` | 打包 + 提取 CHANGELOG |
| PyInstaller | pip 安装 | 打包 EXE |
| Git | 系统 PATH | 代码推送 |
| GitHub CLI | `C:\Program Files\GitHub CLI\gh.exe` | GitHub Release 创建 + EXE 上传 |

### 可选

| 工具 | 说明 |
|------|------|
| Gitee Token | 存于 `.gitee_token` 文件或 `GITEE_TOKEN` 环境变量，无则跳过 Gitee Release |

### 首次配置

```powershell
# 1. 安装 GitHub CLI（https://cli.github.com/）后登录
& "C:\Program Files\GitHub CLI\gh.exe" auth login

# 2. 确认 git remote
git remote -v
# 应该看到 origin / gitee / backup 三个

# 3. Gitee token（放在 codeflow-desktop/ 下）
echo "你的gitee_token" > codeflow-desktop/.gitee_token
```

---

## 发版后验证

发版完成后建议快速验证：

| 检查项 | 方法 |
|--------|------|
| GitHub Release | 打开 `https://github.com/joinwell52-AI/codeflow-pwa/releases/tag/vX.Y.Z`，确认 EXE 附件存在 |
| Gitee Release | 打开 `https://gitee.com/joinwell52/cursor-ai/releases/tag/vX.Y.Z` |
| 自动更新 | 启动旧版 EXE，检查是否提示新版 |
| backup | `git log backup/main --oneline -1` 确认最新提交 |

---

## 故障排除

| 问题 | 原因 | 解决 |
|------|------|------|
| `gh` 未找到 | 安装路径不在 PATH | 脚本已硬编码 `C:\Program Files\GitHub CLI\gh.exe` |
| GitHub push 被拒绝 | 远端有新提交 | `git pull --rebase origin main` 后重新运行 |
| Gitee push tag 被拒绝 | 旧 tag 已存在 | `git push gitee :refs/tags/vX.Y.Z` 删除远端 tag 后重试 |
| EXE 太大（>50MB） | 打包配置有误 | 检查 `build.spec` 的 excludes |
| Gitee EXE 上传失败 | 文件超过 Gitee 免费限制 | Gitee 仅保留代码镜像，EXE 以 GitHub 为准 |
| Release 已存在 | 重复发版 | `gh release delete vX.Y.Z --repo xxx` 后重试 |

---

## 完整示例

```powershell
# 1. 修改版本号
#    main.py: VERSION = "2.11.0"

# 2. 写 CHANGELOG
#    CHANGELOG.md: ## [2.11.0] - 2026-04-15

# 3. 一条龙发版
cd D:\BridgeFlow\codeflow-desktop
release.cmd 2.11.0

# 4. 验证
start https://github.com/joinwell52-AI/codeflow-pwa/releases/tag/v2.11.0
```
