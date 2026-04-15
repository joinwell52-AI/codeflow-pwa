"""
cursor_cdp.py — 通过 Chrome DevTools Protocol (CDP) 读取 Cursor 状态并执行操作。

优先于 cursor_vision.py（OCR）使用：
  - 不需要截屏、OCR、图像处理
  - 精度 100%，延迟 <100ms
  - 需要 Cursor 以 --remote-debugging-port=9222 启动

对外暴露与 cursor_vision.py 兼容的 CursorState，供 nudger.py 无缝切换。

依赖：websockets（已在 requirements.txt）, json, urllib（标准库）
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

from config import _T

logger = logging.getLogger("codeflow.cdp")

# ═══════════════════════════════════════════════════════════
#  配置
# ═══════════════════════════════════════════════════════════

CDP_HOST = "127.0.0.1"
CDP_PORT = 9222
CDP_TIMEOUT = 5.0

# ═══════════════════════════════════════════════════════════
#  数据结构 — 兼容 cursor_vision.CursorState
# ═══════════════════════════════════════════════════════════

@dataclass
class CdpCursorState:
    """与 cursor_vision.CursorState 字段兼容，供 nudger 无缝使用。"""
    found: bool = False
    window: Any = None
    active_tab: str = ""
    chat_panel_open: bool = False
    agent_mode: bool = False
    current_mode: str = ""
    agent_role: str = ""
    pinned_active_role: str = ""
    all_roles: list[str] = field(default_factory=list)
    role_states: dict = field(default_factory=dict)
    input_box: Any = None
    sidebar_visible: bool = False
    bottom_bar_tabs: list[str] = field(default_factory=list)
    lines: list = field(default_factory=list)
    raw_text: str = ""
    scan_ms: float = 0
    error: str = ""
    is_busy: bool = False
    busy_hint: str = ""
    role_positions: dict = field(default_factory=dict)
    screenshot: object = None

    # CDP 专有字段
    cdp_mode: bool = True
    messages: list[dict] = field(default_factory=list)
    pending_approvals: list[dict] = field(default_factory=list)
    agent_status: str = ""
    model_name: str = ""
    window_title: str = ""
    chat_tabs: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "found": self.found,
            "error": self.error,
            "scan_ms": round(self.scan_ms, 1),
            "cdp_mode": True,
        }
        if self.window_title:
            d["window"] = {"title": self.window_title}
        d["active_tab"] = self.active_tab
        d["current_mode"] = self.current_mode
        d["agent_mode"] = self.agent_mode
        d["agent_role"] = self.agent_role
        d["all_roles"] = self.all_roles
        if self.role_states:
            d["role_states"] = self.role_states
        d["chat_panel_open"] = self.chat_panel_open
        d["sidebar_visible"] = self.sidebar_visible
        d["is_busy"] = self.is_busy
        if self.busy_hint:
            d["busy_hint"] = self.busy_hint
        d["agent_status"] = self.agent_status
        d["model_name"] = self.model_name
        d["message_count"] = len(self.messages)
        d["pending_approvals"] = len(self.pending_approvals)
        if self.messages:
            d["recent_messages"] = self.messages[:20]
        return d


# ═══════════════════════════════════════════════════════════
#  CDP 低层通信
# ═══════════════════════════════════════════════════════════

def _get_targets(host: str = CDP_HOST, port: int = CDP_PORT) -> list[dict]:
    """从 CDP 端点获取所有调试目标（tab/window）。"""
    url = f"http://{host}:{port}/json"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=CDP_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.debug("CDP targets 获取失败: %s", e)
        return []


def _find_cursor_targets(targets: list[dict]) -> list[dict]:
    """筛选出 Cursor 编辑器的页面目标。"""
    result = []
    for t in targets:
        if t.get("type") != "page":
            continue
        title = t.get("title", "")
        ws_url = t.get("webSocketDebuggerUrl", "")
        if not ws_url:
            continue
        result.append(t)
    return result


def is_cdp_available(host: str = CDP_HOST, port: int = CDP_PORT) -> bool:
    """检测 CDP 端口是否可用（Cursor 是否以 --remote-debugging-port 启动）。"""
    targets = _get_targets(host, port)
    return len(targets) > 0


class CdpConnection:
    """轻量级同步 CDP WebSocket 客户端（在独立线程的 event loop 中运行）。"""

    def __init__(self, ws_url: str, timeout: float = CDP_TIMEOUT):
        self._ws_url = ws_url
        self._timeout = timeout
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ws = None
        self._msg_id = 0
        self._connected = False

    def connect(self) -> bool:
        """建立 WebSocket 连接。"""
        try:
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            future = asyncio.run_coroutine_threadsafe(self._connect(), self._loop)
            future.result(timeout=self._timeout)
            self._connected = True
            return True
        except Exception as e:
            logger.debug("CDP 连接失败 %s: %s", self._ws_url[:60], e)
            return False

    def disconnect(self):
        """关闭连接。"""
        self._connected = False
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._close(), self._loop)
        if self._thread:
            self._thread.join(timeout=2)

    def evaluate(self, expression: str) -> Any:
        """在页面上下文中执行 JS 表达式，返回结果值。"""
        if not self._connected or not self._loop:
            return None
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._evaluate(expression), self._loop
            )
            return future.result(timeout=self._timeout)
        except Exception as e:
            logger.debug("CDP evaluate 失败: %s", str(e)[:120])
            return None

    def send_command(self, method: str, params: dict | None = None) -> dict | None:
        """发送 CDP 命令。"""
        if not self._connected or not self._loop:
            return None
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._send(method, params or {}), self._loop
            )
            return future.result(timeout=self._timeout)
        except Exception as e:
            logger.debug("CDP command %s 失败: %s", method, str(e)[:120])
            return None

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ─── async 内部实现 ───

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _connect(self):
        import websockets.client as wsc
        self._ws = await wsc.connect(self._ws_url, close_timeout=2, open_timeout=self._timeout)

    async def _close(self):
        if self._ws:
            await self._ws.close()
            self._ws = None
        self._loop.call_soon_threadsafe(self._loop.stop)

    async def _send(self, method: str, params: dict) -> dict:
        self._msg_id += 1
        msg_id = self._msg_id
        msg = json.dumps({"id": msg_id, "method": method, "params": params})
        await self._ws.send(msg)
        while True:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=self._timeout)
            resp = json.loads(raw)
            if resp.get("id") == msg_id:
                if "error" in resp:
                    raise RuntimeError(resp["error"].get("message", "CDP error"))
                return resp.get("result", {})

    async def _evaluate(self, expression: str) -> Any:
        result = await self._send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        })
        exc = result.get("exceptionDetails")
        if exc:
            desc = (exc.get("exception") or {}).get("description", exc.get("text", "eval error"))
            raise RuntimeError(desc)
        remote = result.get("result", {})
        return remote.get("value")


# ═══════════════════════════════════════════════════════════
#  DOM 提取 JS — 在 Cursor 页面上下文执行
# ═══════════════════════════════════════════════════════════

_JS_EXTRACT_STATE = r"""
(() => {
    const state = {
        agentRole: '',
        allRoles: [],
        roleStates: {},
        chatPanelOpen: false,
        agentMode: false,
        currentMode: '',
        isBusy: false,
        busyHint: '',
        sidebarVisible: false,
        inputBoxFound: false,
        windowTitle: document.title || '',
        agentStatus: 'unknown',
        modelName: '',
        messageCount: 0,
        pendingApprovals: 0,
        chatTabs: [],
        activeTab: '',
    };

    // ── 1. Agent Tab 栏（精确选择器：role="tab" 含角色名）──
    const rolePattern = /^\s*(\d{1,2})[\s\-\.]+([A-Za-z][A-Za-z0-9\-]+)\s*$/;
    const seenRoles = new Set();

    // 方法 A：顶部 Tab 栏 — div[role="tab"] 直接取 textContent
    document.querySelectorAll('div[role="tab"]').forEach(tab => {
        const text = (tab.textContent || '').trim();
        const m = text.match(rolePattern);
        if (!m) return;
        const role = `${String(parseInt(m[1])).padStart(2, '0')}-${m[2].toUpperCase()}`;
        if (seenRoles.has(role)) return;
        seenRoles.add(role);
        state.allRoles.push(role);

        const isActive = tab.getAttribute('aria-selected') === 'true' ||
                         tab.classList.contains('active');
        state.chatTabs.push({ role, text: text.substring(0, 60), active: isActive });
        if (isActive) {
            state.agentRole = role;
            state.activeTab = role;
        }
    });

    // 方法 B：右侧 Agent 侧栏 — span.agent-sidebar-cell-text
    const sidebarCells = document.querySelectorAll('span.agent-sidebar-cell-text');
    sidebarCells.forEach(cell => {
        const text = (cell.textContent || '').trim();
        const m = text.match(rolePattern);
        if (!m) return;
        const role = `${String(parseInt(m[1])).padStart(2, '0')}-${m[2].toUpperCase()}`;
        if (!seenRoles.has(role)) {
            seenRoles.add(role);
            state.allRoles.push(role);
            state.chatTabs.push({ role, text: text.substring(0, 60), active: false });
        }
    });
    if (sidebarCells.length > 0) state.sidebarVisible = true;

    // ── 3. Agent 忙碌检测 ──
    // 只检测 Composer / 聊天区域内明确的忙碌指示器，避免全局 class 误判
    // 策略：查找 Stop 按钮（Agent 运行时 Cursor 显示 Stop 按钮）
    const stopBtns = document.querySelectorAll(
        'button[aria-label="Cancel"], button[aria-label="Stop"], ' +
        'button[class*="stop"], button[class*="cancel-generation"]'
    );
    for (const btn of stopBtns) {
        const t = (btn.textContent || '').toLowerCase().trim();
        const vis = btn.offsetParent !== null;
        if (vis && (t.includes('stop') || t.includes('cancel') || t === '' || btn.getAttribute('aria-label'))) {
            state.isBusy = true;
            state.busyHint = 'stop_button_visible';
            break;
        }
    }

    // 补充：Composer 区域内的 animate-spin（旋转动画，排除全局 loading）
    if (!state.isBusy) {
        const composerArea = document.querySelector(
            '[class*="composer"], [class*="chat-panel"], [class*="conversation"]'
        );
        if (composerArea) {
            const spins = composerArea.querySelectorAll('[class*="animate-spin"], [class*="spinner"]');
            for (const s of spins) {
                if (s.offsetParent !== null) {
                    state.isBusy = true;
                    state.busyHint = 'composer_spinner';
                    break;
                }
            }
        }
    }

    // 补充：状态文字（只在短文本元素中匹配，排除长段正文）
    if (!state.isBusy) {
        const statusPhrases = ['generating', 'thinking', 'planning', 'running terminal',
                               'running command', 'applying patch', 'searching'];
        const statusEls = document.querySelectorAll(
            '[class*="agent-status"], [class*="thinking"], [class*="generating"]'
        );
        statusEls.forEach(el => {
            if (state.isBusy) return;
            const t = (el.textContent || '').toLowerCase().trim();
            if (t.length > 80) return;
            for (const ph of statusPhrases) {
                if (t.includes(ph)) {
                    state.isBusy = true;
                    state.busyHint = `status:${t.substring(0, 56)}`;
                    state.agentStatus = 'running';
                    return;
                }
            }
        });
    }

    // ── 4. 输入框检测 ──
    const inputSelectors = [
        'textarea[placeholder*="plan"]',
        'textarea[placeholder*="message"]',
        'textarea[placeholder*="anything"]',
        'textarea[placeholder*="follow"]',
        'textarea[class*="input"]',
        'div[contenteditable="true"][class*="input"]',
        'div[contenteditable="true"][class*="composer"]',
        '[class*="chat-input"] textarea',
        '[class*="composer"] textarea',
    ];
    for (const sel of inputSelectors) {
        const input = document.querySelector(sel);
        if (input) {
            state.inputBoxFound = true;
            state.chatPanelOpen = true;
            break;
        }
    }

    // ── 5. Mode 检测（Agent / Ask / Chat）──
    const modeEls = document.querySelectorAll(
        '[class*="mode"], [class*="chat-mode"], [data-mode], ' +
        '[class*="mode-selector"], [class*="mode-switch"]'
    );
    modeEls.forEach(el => {
        const t = (el.textContent || '').toLowerCase().trim();
        if (['agent', 'ask', 'chat', 'plan', 'manual'].includes(t)) {
            const classes = (el.className || '');
            if (classes.includes('active') || classes.includes('selected') ||
                el.getAttribute('aria-selected') === 'true') {
                state.currentMode = t;
                if (t === 'agent') state.agentMode = true;
            }
            if (!state.currentMode && state.chatPanelOpen) {
                state.currentMode = t;
            }
        }
    });

    // ── 6. Model 名称 ──
    const modelEls = document.querySelectorAll(
        '[class*="model"], [class*="model-select"], [data-model]'
    );
    modelEls.forEach(el => {
        const t = (el.textContent || '').trim();
        if (t.match(/opus|sonnet|claude|gpt|gemini|o[134]|deepseek/i) && t.length < 60) {
            state.modelName = t;
        }
    });

    // ── 7. 消息计数 + 内容提取 ──
    const msgEls = document.querySelectorAll(
        '[data-message-id], [class*="chat-message"], [class*="message-row"], ' +
        '[class*="turn-"], [class*="conversation-turn"]'
    );
    state.messageCount = msgEls.length;

    // 7b. 提取最近 20 条消息摘要（只读监控用，非全文）
    state.recentMessages = [];
    const lastN = Array.from(msgEls).slice(-20);
    lastN.forEach((el, idx) => {
        const msg = { idx: msgEls.length - lastN.length + idx };

        // 角色判断：user 发的消息 vs assistant 回复
        const cls = (el.className || '').toLowerCase();
        const authorEl = el.querySelector('[class*="author"], [class*="role"], [class*="sender"]');
        const authorText = (authorEl?.textContent || '').trim().toLowerCase();
        if (authorText.includes('user') || authorText.includes('human') || cls.includes('user') || cls.includes('human')) {
            msg.role = 'user';
        } else if (authorText.includes('assistant') || authorText.includes('agent') || cls.includes('assistant') || cls.includes('agent')) {
            msg.role = 'assistant';
        } else {
            msg.role = idx % 2 === 0 ? 'user' : 'assistant';
        }

        // 代码块检测
        const codeBlocks = el.querySelectorAll('pre, code[class*="language-"], [class*="code-block"]');
        const codeCount = codeBlocks.length;
        let codeLangs = [];
        let codeLines = 0;
        codeBlocks.forEach(cb => {
            const langCls = (cb.className || '').match(/language-(\w+)/);
            if (langCls) codeLangs.push(langCls[1]);
            codeLines += (cb.textContent || '').split('\n').length;
        });

        // 终端/命令检测
        const termEls = el.querySelectorAll('[class*="terminal"], [class*="shell"], [class*="command"]');
        const hasTerminal = termEls.length > 0;

        // 文件编辑检测
        const fileEls = el.querySelectorAll('[class*="file-diff"], [class*="diff"], [class*="patch"], [class*="file-edit"]');
        const hasFileDiff = fileEls.length > 0;

        // 工具调用检测
        const toolEls = el.querySelectorAll('[class*="tool-call"], [class*="tool-use"], [class*="function-call"]');
        const hasTool = toolEls.length > 0;
        let toolName = '';
        if (hasTool && toolEls[0]) {
            toolName = (toolEls[0].textContent || '').trim().substring(0, 60);
        }

        // 思考块检测
        const thinkEls = el.querySelectorAll('[class*="thinking"], [class*="thought"], [class*="reasoning"]');
        const hasThinking = thinkEls.length > 0;

        // 图片检测
        const imgEls = el.querySelectorAll('img:not([width="16"]):not([height="16"]):not([class*="icon"]):not([class*="avatar"])');
        const hasImage = imgEls.length > 0;

        // 纯文本提取（排除代码块、工具调用等子元素的文本）
        let plainText = '';
        const clone = el.cloneNode(true);
        clone.querySelectorAll('pre, [class*="code-block"], [class*="terminal"], [class*="tool-call"], [class*="tool-use"], [class*="thinking"], [class*="thought"]').forEach(n => n.remove());
        plainText = (clone.textContent || '').trim().replace(/\s+/g, ' ').substring(0, 300);

        // 分类 + 生成摘要
        if (hasThinking) {
            msg.type = 'thinking';
            const preview = (thinkEls[0]?.textContent || '').trim().replace(/\s+/g, ' ').substring(0, 120);
            msg.summary = preview || 'thinking...';
        } else if (hasTool) {
            msg.type = 'tool';
            msg.summary = (toolName ? toolName + ': ' : '') + (plainText.substring(0, 150) || 'tool call');
        } else if (hasTerminal) {
            msg.type = 'terminal';
            const cmd = (termEls[0]?.textContent || '').trim().split('\n')[0].substring(0, 100);
            msg.summary = cmd || 'terminal';
        } else if (hasFileDiff) {
            msg.type = 'file_edit';
            const fileNames = Array.from(fileEls).map(f => (f.textContent||'').trim().split('\n')[0]).filter(Boolean).slice(0, 3);
            msg.summary = fileNames.join(', ') || `${fileEls.length} file(s)`;
        } else if (codeCount > 0 && codeLines > 3) {
            msg.type = 'code';
            const codeHint = plainText.substring(0, 120) || `${codeLines} lines`;
            msg.summary = codeHint;
            if (codeLangs.length > 0) msg.lang = codeLangs[0];
        } else if (hasImage) {
            msg.type = 'image';
            msg.summary = plainText.substring(0, 100) || `${imgEls.length} image(s)`;
        } else {
            msg.type = 'text';
            msg.summary = plainText.substring(0, 200);
        }

        // 附加：纯文本开头（所有类型都带一点上下文）
        if (msg.type !== 'text' && plainText.length > 0) {
            msg.context = plainText.substring(0, 100);
        }

        state.recentMessages.push(msg);
    });

    // ── 8. 待审批检测 ──
    const approvalBtns = document.querySelectorAll(
        'button[class*="approve"], button[class*="accept"], ' +
        '[class*="approval"] button, [class*="tool-call"] button'
    );
    let approvalCount = 0;
    approvalBtns.forEach(btn => {
        const t = (btn.textContent || '').toLowerCase();
        if (t.includes('approve') || t.includes('accept') || t.includes('run') ||
            t.includes('allow') || t.includes('yes')) {
            approvalCount++;
        }
    });
    state.pendingApprovals = approvalCount;

    // ── 9. Agent 状态推导 ──
    if (state.pendingApprovals > 0) {
        state.agentStatus = 'waiting_approval';
    } else if (state.isBusy) {
        state.agentStatus = 'running';
    } else if (state.allRoles.length > 0) {
        state.agentStatus = 'idle';
    }

    if (state.allRoles.length > 0) {
        state.agentMode = true;
        state.chatPanelOpen = true;
        if (!state.currentMode) state.currentMode = 'agent';
    }

    state.found = true;
    return state;
})()
"""

# ═══════════════════════════════════════════════════════════
#  JS 操作函数 — 点击角色、输入文字、按键
# ═══════════════════════════════════════════════════════════

def _js_find_role_position(role_name: str) -> str:
    """查找角色 Tab 或侧栏元素的屏幕坐标，供 CDP 鼠标事件使用。

    优先点击 Tab 栏 div[role="tab"]（直接切换 Agent），
    其次点击侧栏 span.agent-sidebar-cell-text。
    """
    return f"""
    (() => {{
        const target = {json.dumps(role_name)}.toUpperCase();
        const shortName = target.replace(/^\\d+-/, '');
        const roleRe = /^\\s*(\\d{{1,2}})[\\s\\-\\.]+(\\w+)\\s*$/;
        function match(text) {{
            const m = text.trim().match(roleRe);
            if (!m) return false;
            const n = String(parseInt(m[1])).padStart(2, '0') + '-' + m[2].toUpperCase();
            return n === target || m[2].toUpperCase() === shortName;
        }}

        // 优先：Tab 栏 div[role="tab"]
        for (const tab of document.querySelectorAll('div[role="tab"]')) {{
            if (match(tab.textContent || '')) {{
                const rect = tab.getBoundingClientRect();
                return {{ found: true, x: Math.round(rect.x + rect.width / 2), y: Math.round(rect.y + rect.height / 2), text: tab.textContent.trim(), source: 'tab' }};
            }}
        }}

        // 其次：侧栏 span.agent-sidebar-cell-text
        for (const cell of document.querySelectorAll('span.agent-sidebar-cell-text')) {{
            if (match(cell.textContent || '')) {{
                const rect = cell.getBoundingClientRect();
                return {{ found: true, x: Math.round(rect.x + rect.width / 2), y: Math.round(rect.y + rect.height / 2), text: cell.textContent.trim(), source: 'sidebar' }};
            }}
        }}

        return {{ found: false, x: 0, y: 0 }};
    }})()
    """


def _js_type_and_send(text: str) -> str:
    """生成在输入框中粘贴文字并发送的 JS。"""
    escaped = json.dumps(text)
    return f"""
    (() => {{
        const selectors = [
            'textarea[placeholder*="plan"]',
            'textarea[placeholder*="message"]',
            'textarea[placeholder*="anything"]',
            'textarea[class*="input"]',
            'div[contenteditable="true"][class*="input"]',
            'div[contenteditable="true"][class*="composer"]',
            '[class*="chat-input"] textarea',
            '[class*="composer"] textarea',
        ];
        let input = null;
        for (const sel of selectors) {{
            input = document.querySelector(sel);
            if (input) break;
        }}
        if (!input) return {{ ok: false, reason: 'input_not_found' }};

        input.focus();

        if (input.tagName === 'TEXTAREA' || input.tagName === 'INPUT') {{
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            )?.set || Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            )?.set;
            if (nativeInputValueSetter) {{
                nativeInputValueSetter.call(input, {escaped});
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }} else {{
                input.value = {escaped};
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} else {{
            input.textContent = {escaped};
            input.dispatchEvent(new InputEvent('input', {{ bubbles: true, data: {escaped} }}));
        }}

        return {{ ok: true, reason: 'text_set' }};
    }})()
    """


def _js_press_enter() -> str:
    """生成按 Enter 提交的 JS。"""
    return """
    (() => {
        const selectors = [
            'textarea[placeholder*="plan"]',
            'textarea[placeholder*="message"]',
            'textarea[placeholder*="anything"]',
            'textarea[class*="input"]',
            'div[contenteditable="true"][class*="input"]',
            'div[contenteditable="true"][class*="composer"]',
            '[class*="chat-input"] textarea',
            '[class*="composer"] textarea',
        ];
        let input = null;
        for (const sel of selectors) {
            input = document.querySelector(sel);
            if (input) break;
        }
        if (!input) return false;
        input.focus();
        input.dispatchEvent(new KeyboardEvent('keydown', {
            key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
        }));
        return true;
    })()
    """


def _js_click_approve() -> str:
    """生成点击审批按钮的 JS。"""
    return """
    (() => {
        const btns = document.querySelectorAll(
            'button[class*="approve"], button[class*="accept"], ' +
            '[class*="approval"] button, [class*="tool-call"] button'
        );
        for (const btn of btns) {
            const t = (btn.textContent || '').toLowerCase();
            if (t.includes('approve') || t.includes('accept') || t.includes('run') ||
                t.includes('allow') || t.includes('yes')) {
                btn.scrollIntoView({ block: 'center', behavior: 'instant' });
                btn.click();
                return true;
            }
        }
        return false;
    })()
    """


# ═══════════════════════════════════════════════════════════
#  高层 API — 供 nudger.py 调用
# ═══════════════════════════════════════════════════════════

_conn_cache: dict[str, CdpConnection] = {}
_conn_lock = threading.Lock()


def _get_connection(ws_url: str) -> CdpConnection | None:
    """获取或创建到指定目标的 CDP 连接（带缓存）。"""
    with _conn_lock:
        conn = _conn_cache.get(ws_url)
        if conn and conn.is_connected:
            return conn
        if conn:
            conn.disconnect()
        conn = CdpConnection(ws_url)
        if conn.connect():
            _conn_cache[ws_url] = conn
            logger.info("CDP 连接建立: %s", ws_url[:60])
            return conn
        return None


def _get_main_target() -> dict | None:
    """找到主 Cursor 编辑器目标。"""
    targets = _get_targets()
    cursor_targets = _find_cursor_targets(targets)
    if not cursor_targets:
        return None
    # 优先选标题含 "Cursor" 的，其次取第一个
    for t in cursor_targets:
        title = t.get("title", "")
        if "Cursor" in title or "cursor" in title.lower():
            return t
    return cursor_targets[0]


def scan(host: str = CDP_HOST, port: int = CDP_PORT) -> CdpCursorState:
    """
    CDP 扫描 — 对标 cursor_vision.scan()。
    返回 CdpCursorState（字段兼容 CursorState）。
    """
    t0 = time.perf_counter()
    state = CdpCursorState()

    target = _get_main_target()
    if not target:
        state.error = _T("cdp_no_target")
        state.scan_ms = (time.perf_counter() - t0) * 1000
        return state

    ws_url = target.get("webSocketDebuggerUrl", "")
    if not ws_url:
        state.error = _T("cdp_no_ws_url")
        state.scan_ms = (time.perf_counter() - t0) * 1000
        return state

    conn = _get_connection(ws_url)
    if not conn:
        state.error = _T("cdp_ws_fail", url=ws_url[:60])
        state.scan_ms = (time.perf_counter() - t0) * 1000
        return state

    try:
        raw = conn.evaluate(_JS_EXTRACT_STATE)
        if not raw or not isinstance(raw, dict):
            state.error = _T("cdp_empty_result")
            state.scan_ms = (time.perf_counter() - t0) * 1000
            return state

        state.found = raw.get("found", False)
        state.window_title = raw.get("windowTitle", "")
        state.active_tab = raw.get("activeTab", "")
        state.agent_role = raw.get("agentRole", "")
        state.pinned_active_role = raw.get("agentRole", "")
        state.all_roles = raw.get("allRoles", [])
        state.role_states = raw.get("roleStates", {})
        state.chat_panel_open = raw.get("chatPanelOpen", False)
        state.agent_mode = raw.get("agentMode", False)
        state.current_mode = raw.get("currentMode", "")
        state.is_busy = raw.get("isBusy", False)
        state.busy_hint = raw.get("busyHint", "")
        state.sidebar_visible = raw.get("sidebarVisible", False)
        state.agent_status = raw.get("agentStatus", "unknown")
        state.model_name = raw.get("modelName", "")
        state.chat_tabs = raw.get("chatTabs", [])

        raw_msgs = raw.get("recentMessages", [])
        if isinstance(raw_msgs, list):
            state.messages = raw_msgs[:20]

        if raw.get("inputBoxFound"):
            from cursor_vision import Rect
            state.input_box = Rect(0, 0, 100, 30)

    except Exception as e:
        state.error = _T("cdp_extract_error", err=e)
        logger.warning("CDP scan 异常: %s", e)

    state.scan_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "CDP scan: %.0fms found=%s roles=%s active=%s busy=%s status=%s",
        state.scan_ms, state.found, state.all_roles,
        state.agent_role, state.is_busy, state.agent_status,
    )
    return state


def click_role(role: str) -> bool:
    """通过 CDP 鼠标事件点击指定 Agent Tab/侧栏项切换角色。

    先用 JS 定位元素坐标，再用 Input.dispatchMouseEvent 发送真实鼠标事件
    （el.click() 在 React/Electron 中不可靠）。
    """
    target = _get_main_target()
    if not target:
        return False
    ws_url = target.get("webSocketDebuggerUrl", "")
    conn = _get_connection(ws_url)
    if not conn:
        return False

    pos = conn.evaluate(_js_find_role_position(role))
    if not pos or not isinstance(pos, dict) or not pos.get("found"):
        logger.info("CDP click_role(%s) → 未找到元素", role)
        return False

    x, y = pos["x"], pos["y"]
    logger.info("CDP click_role(%s) 定位: (%d, %d) text=%s", role, x, y, pos.get("text", ""))

    for evt_type in ("mousePressed", "mouseReleased"):
        conn.send_command("Input.dispatchMouseEvent", {
            "type": evt_type,
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": 1,
        })

    logger.info("CDP click_role(%s) → 鼠标点击已发送 (%d, %d)", role, x, y)
    return True


def type_and_send(text: str) -> bool:
    """通过 CDP 在输入框中填入文字（不自动发送，需配合 press_enter）。"""
    target = _get_main_target()
    if not target:
        return False
    ws_url = target.get("webSocketDebuggerUrl", "")
    conn = _get_connection(ws_url)
    if not conn:
        return False

    result = conn.evaluate(_js_type_and_send(text))
    if isinstance(result, dict) and result.get("ok"):
        logger.info("CDP type_and_send: ok, %d chars", len(text))
        return True
    logger.warning("CDP type_and_send 失败: %s", result)
    return False


def press_enter() -> bool:
    """通过 CDP 按 Enter 提交。"""
    target = _get_main_target()
    if not target:
        return False
    ws_url = target.get("webSocketDebuggerUrl", "")
    conn = _get_connection(ws_url)
    if not conn:
        return False

    # 优先用 Input.dispatchKeyEvent（更可靠）
    resp = conn.send_command("Input.dispatchKeyEvent", {
        "type": "keyDown",
        "key": "Enter",
        "code": "Enter",
        "windowsVirtualKeyCode": 13,
        "nativeVirtualKeyCode": 13,
    })
    if resp is not None:
        conn.send_command("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "key": "Enter",
            "code": "Enter",
            "windowsVirtualKeyCode": 13,
            "nativeVirtualKeyCode": 13,
        })
        logger.info("CDP press_enter: Input.dispatchKeyEvent ok")
        return True

    # 降级到 JS 事件
    result = conn.evaluate(_js_press_enter())
    logger.info("CDP press_enter (JS fallback): %s", result)
    return bool(result)


def insert_text(text: str) -> bool:
    """通过 CDP Input.insertText 直接插入文字（最可靠的输入方式）。"""
    target = _get_main_target()
    if not target:
        return False
    ws_url = target.get("webSocketDebuggerUrl", "")
    conn = _get_connection(ws_url)
    if not conn:
        return False
    resp = conn.send_command("Input.insertText", {"text": text})
    if resp is not None:
        logger.info("CDP insert_text: ok, %d chars", len(text))
        return True
    return False


def click_approve() -> bool:
    """通过 CDP 点击审批按钮。"""
    target = _get_main_target()
    if not target:
        return False
    ws_url = target.get("webSocketDebuggerUrl", "")
    conn = _get_connection(ws_url)
    if not conn:
        return False
    result = conn.evaluate(_js_click_approve())
    logger.info("CDP click_approve → %s", result)
    return bool(result)


def get_all_windows() -> list[dict]:
    """获取所有 Cursor 窗口及其状态。"""
    targets = _get_targets()
    windows = []
    for t in _find_cursor_targets(targets):
        ws_url = t.get("webSocketDebuggerUrl", "")
        conn = _get_connection(ws_url)
        if not conn:
            continue
        try:
            raw = conn.evaluate(_JS_EXTRACT_STATE)
            if raw and isinstance(raw, dict):
                windows.append({
                    "id": t.get("id", ""),
                    "title": t.get("title", ""),
                    "url": t.get("url", ""),
                    "ws_url": ws_url,
                    "state": raw,
                })
        except Exception:
            pass
    return windows


def close_all_connections():
    """关闭所有缓存的 CDP 连接。"""
    with _conn_lock:
        for ws_url, conn in _conn_cache.items():
            try:
                conn.disconnect()
            except Exception:
                pass
        _conn_cache.clear()
    logger.info("CDP 所有连接已关闭")


# ═══════════════════════════════════════════════════════════
#  DOM 探查 — 帮助了解 Cursor 真实 DOM 结构
# ═══════════════════════════════════════════════════════════

_JS_DOM_PROBE = r"""
(() => {
    const results = { tabs: [], pinned: [], roleTexts: [] };

    // 1. 收集所有包含数字+字母角色名模式的叶子节点
    const roleRe = /\b(\d{1,2})[\s\-\.]+([A-Za-z]\w+)\b/;
    const walker = document.createTreeWalker(
        document.body, NodeFilter.SHOW_ELEMENT,
        { acceptNode: n => n.children.length === 0 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP }
    );
    let node;
    while (node = walker.nextNode()) {
        const text = (node.textContent || '').trim();
        if (!text || text.length > 80) continue;
        const m = text.match(roleRe);
        if (m) {
            const rect = node.getBoundingClientRect();
            let ancestorInfo = [];
            let p = node;
            for (let i = 0; i < 6 && p; i++) {
                const tag = p.tagName || '';
                const cls = (p.className && typeof p.className === 'string') ? p.className.split(' ').filter(c=>c.length>2).slice(0,4).join(' ') : '';
                const role = p.getAttribute('role') || '';
                const aria = p.getAttribute('aria-selected') || '';
                const data = p.getAttribute('data-tab') || p.getAttribute('data-testid') || '';
                ancestorInfo.push({ tag, cls: cls.substring(0, 80), role, aria, data });
                p = p.parentElement;
            }
            results.roleTexts.push({
                text: text,
                x: Math.round(rect.x), y: Math.round(rect.y),
                w: Math.round(rect.width), h: Math.round(rect.height),
                tag: node.tagName,
                cls: (node.className && typeof node.className === 'string') ? node.className.substring(0, 100) : '',
                ancestors: ancestorInfo,
            });
        }
    }

    // 2. 收集顶部 Tab 栏元素
    const tabEls = document.querySelectorAll('[role="tab"], [data-tab], [class*="composer-tab"]');
    tabEls.forEach(el => {
        const rect = el.getBoundingClientRect();
        results.tabs.push({
            text: (el.textContent || '').trim().substring(0, 60),
            cls: (el.className && typeof el.className === 'string') ? el.className.substring(0, 100) : '',
            role: el.getAttribute('role') || '',
            ariaSelected: el.getAttribute('aria-selected') || '',
            x: Math.round(rect.x), y: Math.round(rect.y),
            w: Math.round(rect.width), h: Math.round(rect.height),
        });
    });

    return results;
})()
"""


def dom_probe(host: str = CDP_HOST, port: int = CDP_PORT) -> dict | None:
    """探查 Cursor DOM 结构，返回与 Agent 相关的元素详情。"""
    target = _get_main_target()
    if not target:
        return None
    ws_url = target.get("webSocketDebuggerUrl", "")
    conn = _get_connection(ws_url)
    if not conn:
        return None
    try:
        return conn.evaluate(_JS_DOM_PROBE)
    except Exception as e:
        logger.warning("DOM probe 异常: %s", e)
        return None


# ═══════════════════════════════════════════════════════════
#  独立运行：测试 CDP 识别效果
# ═══════════════════════════════════════════════════════════

def _test():
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    SEP = "=" * 60
    print(SEP)
    print("  Cursor CDP 巡检器 — 测试模式")
    print(SEP)

    print(f"\n[1] 检测 CDP 端口 ({CDP_HOST}:{CDP_PORT})...")
    if not is_cdp_available():
        print("  × CDP 不可用")
        print("  请以 --remote-debugging-port=9222 启动 Cursor")
        print("  示例: Cursor.exe --remote-debugging-port=9222")
        sys.exit(1)

    targets = _get_targets()
    print(f"  找到 {len(targets)} 个目标:")
    for t in targets:
        print(f"    [{t.get('type','?')}] {t.get('title','')[:50]}")

    print("\n[2] CDP 扫描...")
    state = scan()
    print(f"  扫描耗时: {state.scan_ms:.0f}ms")
    print(f"  找到: {state.found}")
    print(f"  窗口标题: {state.window_title}")
    print(f"  Agent 角色: {state.agent_role or '(无)'}")
    print(f"  全部角色: {state.all_roles}")
    print(f"  当前模式: {state.current_mode or '(未检测到)'}")
    print(f"  Agent 模式: {state.agent_mode}")
    print(f"  忙碌: {state.is_busy} ({state.busy_hint})")
    print(f"  Agent 状态: {state.agent_status}")
    print(f"  模型: {state.model_name}")
    print(f"  输入框: {'是' if state.input_box else '否'}")
    print(f"  错误: {state.error or '(无)'}")

    print(f"\n[3] JSON:")
    print(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))

    print(f"\n[4] 对比 OCR 方案:")
    print(f"  CDP: {state.scan_ms:.0f}ms, 精度 100%, 零依赖图像")
    try:
        from cursor_vision import scan as ocr_scan
        t0 = time.perf_counter()
        ocr_state = ocr_scan()
        ocr_ms = (time.perf_counter() - t0) * 1000
        print(f"  OCR: {ocr_ms:.0f}ms, roles={ocr_state.all_roles}")
        print(f"  速度提升: {ocr_ms / max(state.scan_ms, 1):.1f}x")
    except Exception as e:
        print(f"  OCR 不可用: {e}")

    close_all_connections()
    print(f"\n{SEP}")
    print("  CDP 测试完成")
    print(SEP)


if __name__ == "__main__":
    _test()
