## 码流（CodeFlow）Desktop v2.9.24

> 下载 \CodeFlow-Desktop.exe\，双击运行，无需安装。
> 已安装旧版的用户程序会**自动检测并提示更新**，无需手动下载。

---

### 桌面端（`codeflow-desktop`）

#### 修复：引导完成后进程彻底退出

- 引导完成（填写完 Cursor 路径、团队、项目目录并保存）后，后端进程 1 秒内自动退出
- 前端引导页显示"配置已保存"后 3 秒自动关闭页面
- 不再打开任何额外浏览器标签、不再启动 Cursor、不再尝试嵌入面板
- 用户需要手动重新启动 CodeFlow 进入正常使用模式

#### 修复：引导阶段不再尝试嵌入 Cursor Simple Browser

- 引导期间只用系统浏览器打开引导页，完全移除对 `_schedule_embed_panel` 的调用
- 消除了引导期间可能触发 Cursor 自动启动的根源

---

---

### 系统要求
- Windows 10 / 11（64 位）
- 已安装 [Cursor IDE](https://www.cursor.com/)

### 快速开始
1. 双击 \CodeFlow-Desktop.exe\ 启动
2. 按引导选择项目目录和团队模板
3. 手机打开 [码流 PWA](https://joinwell52-ai.github.io/codeflow-pwa/) 扫码绑定

### 完整更新日志
见 [CHANGELOG.md](https://github.com/joinwell52-AI/codeflow-pwa/blob/main/CHANGELOG.md)
