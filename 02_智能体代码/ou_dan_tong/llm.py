"""极简 OpenAI 兼容 LLM 调用封装，仅用标准库，零依赖。"""
import json
import urllib.request

from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL,
)


class LLM:
    def __init__(self, provider: str = "deepseek"):
        self.provider = provider

    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        if self.provider == "deepseek":
            key, base, model = DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
        else:
            key, base, model = OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
        if not key:
            raise RuntimeError(
                "未检测到 API Key。请设置环境变量 DEEPSEEK_API_KEY "
                "(或 OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL) 后运行真实抽取。"
            )
        url = base.rstrip("/") + "/chat/completions"
        messages = [{"role": "system", "content": system}]
        if user:
            messages.append({"role": "user", "content": user})
        payload = {"model": model, "messages": messages, "temperature": 0.2, "stream": False}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
