# external/ — 第三方 Skills / 工具资源（本地克隆）

本目录存放从 GitHub **浅克隆**（`git clone --depth 1`）的仓库，作为 **Agent Skills、配图、公众号/小红书工作流** 的**本地资源池**。  
**不修改**上游代码；升级时在各子目录内 `git pull`。

---

## 当前清单（以本机目录为准）

| 本地目录 | 上游仓库 | 用途摘要 |
|----------|----------|----------|
| `anthropics-skills` | [anthropics/skills](https://github.com/anthropics/skills) | Anthropic 官方 Agent Skills 示例与规范（含 docx/pdf 等参考实现） |
| `wechat_article_skills` | [BND-1/wechat_article_skills](https://github.com/BND-1/wechat_article_skills) | 微信公众号：写作 / 格式化 / 草稿发布等 |
| `Auto-Redbook-Skills` | [comeonzhj/Auto-Redbook-Skills](https://github.com/comeonzhj/Auto-Redbook-Skills) | 小红书：Markdown→卡片图、主题、可选发布 |
| `smart-illustrator` | [axtonliu/smart-illustrator](https://github.com/axtonliu/smart-illustrator) | 文章配图 / 多平台封面等插画流程 |
| `wewrite` | [oaker-io/wewrite](https://github.com/oaker-io/wewrite) | 公众号全流程（含封面与配图相关步骤） |

---

## 给 Cursor 用（拷贝而非改源码）

将**需要的子目录**（含 `SKILL.md` 的文件夹）复制到：

- **全局**：`%USERPROFILE%\.cursor\skills\`
- **仅当前项目**：`D:\BridgeFlow\.cursor\skills\`

各仓库的依赖、API Key、公众号/小红书合规要求以**各自 README** 为准。

---

## 统一更新命令（PowerShell）

```powershell
$base = "D:\BridgeFlow\external"
@(
  "anthropics-skills",
  "wechat_article_skills",
  "Auto-Redbook-Skills",
  "smart-illustrator",
  "wewrite"
) | ForEach-Object {
  $p = Join-Path $base $_
  if (Test-Path (Join-Path $p ".git")) {
    Write-Host ">>> $_"
    Push-Location $p; git pull --ff-only; Pop-Location
  }
}
```

---

## Git 说明

若不希望把整段 `external/` 提交进 BridgeFlow 主仓库，可在主项目 `.gitignore` 中加入一行：`external/`（按需）。  
若希望团队共享固定版本，可改为 **git submodule** 指向上述各仓库。
