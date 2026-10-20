"""模型与运行配置。Key 走环境变量，缺省走 mock 模式（无 Key 也能测全管线）。"""
import os

# DeepSeek（默认，OpenAI 兼容）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 任意 OpenAI 兼容端点（智谱 / MiniMax / 通义 等），设置后自动覆盖
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")

# 数据文件存放目录（与本项目同级的 data 运行时目录）
DATA_DIR = os.getenv("OU_DATA_DIR", os.path.join(os.path.dirname(__file__), "runtime"))
