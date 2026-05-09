"""ShopPilot — 电商智能客服 Agent."""

import os as _os
from pathlib import Path as _Path

# tiktoken 默认把 cl100k_base 等 BPE 词表缓存到 CWD，会在项目根产生
# 40 字符 hex hash 命名的散文件（如 9b5ad71b...）。把缓存改到用户目录。
# 必须在 common.token_utils 触发 tiktoken.get_encoding() 之前设——所以放在
# shoppilot 包顶部，让所有入口 import 时就生效。
_os.environ.setdefault(
    "TIKTOKEN_CACHE_DIR",
    str(_Path.home() / ".cache" / "tiktoken"),
)

__version__ = "0.1.0"
