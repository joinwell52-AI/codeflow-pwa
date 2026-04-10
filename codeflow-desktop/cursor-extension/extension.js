/**
 * 在编辑器内打开本机 CodeFlow 面板（依赖内置 Simple Browser；失败则系统浏览器）。
 * 使用前请先运行 CodeFlow-Desktop.exe，使 http://127.0.0.1:18765 可访问。
 */
const vscode = require("vscode");

const PANEL_URL = "http://127.0.0.1:18765/";

async function openPanel() {
  const uri = vscode.Uri.parse(PANEL_URL);
  /** @type {(() => Promise<unknown>)[]} */
  const attempts = [
    () => vscode.commands.executeCommand("simpleBrowser.show", uri),
    () => vscode.commands.executeCommand("simpleBrowser.show", PANEL_URL),
    () => vscode.commands.executeCommand("workbench.action.simpleBrowser.show", uri),
    () => vscode.commands.executeCommand("vscode.simple-browser.open", uri),
  ];
  for (const run of attempts) {
    try {
      await run();
      return;
    } catch {
      /* try next */
    }
  }
  await vscode.env.openExternal(uri);
}

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand("codeflow.openPanel", openPanel),
  );

  const sb = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  sb.text = "$(radio-tower) CodeFlow";
  sb.tooltip = "打开码流控制面板（请先运行 CodeFlow-Desktop）";
  sb.command = "codeflow.openPanel";
  sb.show();
  context.subscriptions.push(sb);
}

function deactivate() {}

module.exports = { activate, deactivate };
