# BridgeFlow PyPI 发布说明

## 发布范围

- `PyPI` 只发布 Python 包 `bridgeflow`
- `PWA` 静态页面不发布到 `PyPI`
- `PWA` 目录单独位于 `web/pwa/`

## 执行目录

所有打包和上传命令都在项目根目录执行：

```powershell
cd BridgeFlow
```

不要在以下目录执行上传：

- `web/pwa/`
- `src/bridgeflow/`
- `server/relay/`

## 关键路径

- 包配置文件：`pyproject.toml`
- 源码目录：`src/bridgeflow/`
- 构建产物目录：`dist/`
- `PWA` 目录：`web/pwa/`

## 本地已验证结果

- 已从 `BridgeFlow/` 根目录成功构建 `wheel`
- 已生成构建产物：`dist/bridgeflow-0.1.0-py3-none-any.whl`
- 已用临时虚拟环境安装该 `wheel`
- 已验证 `bridgeflow --help` 可正常输出

## 发布前准备

如需标准发布流程，建议先安装：

```powershell
py -3.10 -m pip install --upgrade build twine
```

## 构建命令

推荐同时构建源码包和轮子包：

```powershell
py -3.10 -m build
```

构建完成后，产物位于：

- `dist/*.whl`
- `dist/*.tar.gz`

## 上传命令

先检查包内容：

```powershell
py -3.10 -m twine check dist/*
```

再上传到 `PyPI`：

```powershell
py -3.10 -m twine upload dist/*
```

## 注意事项

- 公开发布前，示例配置和文档中的真实默认值应保持为示例值
- `room_key` 不要使用演示值，发布前自行替换
- `relayUrl` 应在真实部署时覆盖，不建议把生产地址写成公开默认值
- 如果只想内部试装，可先分发 `dist/` 下的 `wheel`
