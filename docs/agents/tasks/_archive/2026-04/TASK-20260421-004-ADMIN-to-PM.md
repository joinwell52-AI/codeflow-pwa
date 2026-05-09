---
protocol: fcop
version: 1
sender: ADMIN
recipient: PM
thread_key: pypi_doc_patch_fcop_20260421
priority: P2
---

# 授权：发一个 `fcop 0.2.2` 文档补丁版

## 背景

PyPI 页面 https://pypi.org/project/fcop/ 显示的是 `0.2.1` 上传时的旧 README（本地路径安装），没有三路安装章节、没有 Cursor Install 按钮。

现在本地 `codeflow-plugin/README.md` 已经改好，但 PyPI 不会回头刷新，只有发新版才会显示。

## 授权

允许补发 `fcop 0.2.2`，改动范围只有文档刷新：

- 新增三路安装章节（`uvx` / Cursor Deeplink 按钮 / `pip`）
- 本地开发 shim 说明
- 不改任何运行时代码

## 验证标准

上传后 1 分钟刷 https://pypi.org/project/fcop/ ，页面能看到 **Install in Cursor** 胶囊按钮即为通过。

---
**签名**：ADMIN-01  
**日期**：2026-04-21
