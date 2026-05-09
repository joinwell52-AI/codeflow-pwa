---
protocol: fcop
version: 1
sender: PM
recipient: ADMIN
thread_key: pypi_doc_patch_fcop_20260421
priority: P2
status: closed
---

# 总回执：`fcop 0.2.2` 文档补丁版已上架

## 结论

✅ 完成。任务 `TASK-20260421-004` 交付关闭。

## 发生了什么

你反馈 https://pypi.org/project/fcop/ 上没看到 Install 按钮。原因：PyPI 页面锁死在 0.2.1 上传那一刻的 README 快照，本地 README 改了不会回头刷新。

修复方案：发一个纯文档补丁版 `0.2.2`。

## 交付物

| 项 | 链接 / 位置 |
|---|---|
| 新版本页 | https://pypi.org/project/fcop/0.2.2/ |
| 主项目页 | https://pypi.org/project/fcop/ （CDN 刷新后显示 0.2.2 README + 按钮） |
| 安装方式 | 完全不变：`uvx fcop` / deeplink / `pip install fcop` |
| 运行时代码 | 0 改动 |

## 关键验证

- `curl -sI https://pypi.org/project/fcop/0.2.2/` → `HTTP/1.1 200 OK`
- `https://pypi.org/simple/fcop/` simple 索引已含 0.2.2 的 wheel + sdist

## 引用

- `TASK-20260421-004-ADMIN-to-PM.md` — 你的授权
- `TASK-20260421-004-PM-to-OPS.md` — 派发 OPS
- `TASK-20260421-004-OPS-to-PM.md` — OPS 发布回执
- 本文件 — 总回执

## 提醒

现在刷新 https://pypi.org/project/fcop/ ，如果看到的版本号还是 0.2.1，强刷一次（Ctrl+F5）或等 30 秒，CDN 同步完就会出按钮。

---
**签名**：PM-01  
**日期**：2026-04-21  
**任务状态**：`CLOSED`
