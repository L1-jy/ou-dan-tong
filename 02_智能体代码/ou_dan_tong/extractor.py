"""LLM 结构化抽取。支持 mock 模式（无 Key 也能测全管线）。"""
import json

from llm import LLM
from prompts import EXTRACTION_SYSTEM


def extract(chat_text: str, llm: LLM = None, mock=None):
    if mock is not None:
        return mock
    if llm is None:
        llm = LLM()
    raw = llm.chat(EXTRACTION_SYSTEM, chat_text, json_mode=True)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)
