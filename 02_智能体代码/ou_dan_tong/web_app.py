"""瓯单通 · 可体验网页智能体（零依赖，仅用 Python 标准库）。

运行：python web_app.py  →  浏览器打开 http://127.0.0.1:8000
- 配置 DEEPSEEK_API_KEY 环境变量 → 启用真实抽取；否则自动进入 Mock 模式（用预置数据演示流程）。
- 队友/评委直接粘贴群聊、问「XX 那单到哪了」、说「出今日简报」即可体验。
"""
import os
import sys
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from store import Store
from agent import handle_message
from sim_chats import SCENARIO1_MOCK

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, "static", "index.html")

_store = Store()
USE_MOCK = not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"))
MODE_LABEL = "模拟模式（未配置 API Key，演示用预置数据）" if USE_MOCK \
    else f"真实模式（{os.getenv('DEEPSEEK_MODEL', os.getenv('OPENAI_MODEL', 'LLM'))}）"
_LOCK = threading.Lock()


def ledger_state():
    return {"orders": _store.orders, "tasks": _store.tasks,
            "mode": MODE_LABEL, "mock": USE_MOCK}


def do_chat(text):
    with _LOCK:
        mock = SCENARIO1_MOCK if USE_MOCK else None
        result = handle_message(text, _store, llm=None, mock=mock)
    result["ledger"] = ledger_state()
    return result


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        self._send(200, json.dumps(obj, ensure_ascii=False))

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(INDEX, encoding="utf-8") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "index.html 未找到，请确认 static/index.html 存在。")
        elif self.path == "/api/ledger":
            self._json(ledger_state())
        else:
            self._send(404, "Not Found")

    def do_POST(self):
        if self.path == "/api/chat":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                payload = {}
            text = (payload.get("message") or "").strip()
            self._json(do_chat(text))
        elif self.path == "/api/reset":
            with _LOCK:
                _store.reset()
            self._json(ledger_state())
        else:
            self._send(404, "Not Found")

    def log_message(self, *args):
        pass  # 安静运行


def main():
    port = int(os.getenv("OU_PORT", "8000"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"瓯单通已启动 → http://127.0.0.1:{port}")
    print(f"当前模式：{MODE_LABEL}")
    print("Ctrl+C 停止。")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
