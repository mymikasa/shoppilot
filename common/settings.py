"""精简 settings — shoppilot 对 RAGFlow common/settings.py 的本地化替换。

原 RAGFlow settings 文件顶层会 import 整套云存储/ES/Redis 连接器（rag.utils.es_conn,
infinity_conn, minio_conn, redis_conn, ... 以及 memory.utils.*），让任何 import 路径
触及 common.settings 都会引爆全栈，并要求 ES / Redis / MinIO / DB 全配齐。

shoppilot 只用 RAGFlow 的"文档解析 + 切分"能力（deepdoc.parser, rag.app.*, rag.nlp.*），
不用它的服务层。这里仅保留这些代码会读到的常量与函数 stub，副作用全部移除。

当 RAGFlow 升级时，重新 diff 原 common/settings.py（备份在 git 历史里），把新增的
解析/切分相关常量加到这里即可。所有 RAGFlow 服务相关项（云存储、DB、SSO、邮件等）
不必跟。
"""

from __future__ import annotations

import os
from typing import Any

# --- 基础常量 --- #

TIMEZONE = os.getenv("TZ", "Asia/Shanghai")

# RAGFlow 解析/切分模块会访问下列常量。值用安全默认（False / 0 / {}）
# 即可，不影响 deepdoc 与 rag.app 的解析路径。

# DOC engine 开关：rag.nlp.rag_tokenizer.tokenize() 检查此值决定是否走 Infinity
# 内置分词；走 False 分支就是普通中文分词（我们要的）。
DOC_ENGINE = os.getenv("DOC_ENGINE", "elasticsearch")
DOC_ENGINE_INFINITY = False
DOC_ENGINE_OCEANBASE = False

DOC_MAXIMUM_SIZE: int = 128 * 1024 * 1024
DOC_BULK_SIZE: int = 4
EMBEDDING_BATCH_SIZE: int = 16

PARALLEL_DEVICES: int = 0

# 云存储相关常量保留为空 dict（RAGFlow 某些代码会 .get(...) 访问）
ES: dict = {}
INFINITY: dict = {}
AZURE: dict = {}
S3: dict = {}
MINIO: dict = {}
OB: dict = {}
OSS: dict = {}
OS: dict = {}
GCS: dict = {}

STORAGE_IMPL = None
docStoreConn = None
msgStoreConn = None
retriever = None
kg_retriever = None

# LLM/Embedding 相关字段（解析层不会真正调用，但会读取）
LLM = None
LLM_FACTORY = None
LLM_BASE_URL = None
CHAT_MDL = ""
EMBEDDING_MDL = ""
RERANK_MDL = ""
ASR_MDL = ""
IMAGE2TEXT_MDL = ""
CHAT_CFG: dict = {}
EMBEDDING_CFG: dict = {}
RERANK_CFG: dict = {}
ASR_CFG: dict = {}
IMAGE2TEXT_CFG: dict = {}

API_KEY = None
PARSERS = "naive:General,qa:Q&A,resume:Resume,manual:Manual,table:Table,paper:Paper,book:Book,laws:Laws,presentation:Presentation,picture:Picture,one:One,audio:Audio,email:Email,tag:Tag"
HOST_IP = "127.0.0.1"
HOST_PORT = None
SECRET_KEY = None
FACTORY_LLM_INFOS: list = []
ALLOWED_LLM_FACTORIES = None

DATABASE_TYPE = os.getenv("DB_TYPE", "mysql")
DATABASE: dict = {}

# auth / oauth：解析层用不到
AUTHENTICATION_CONF = None
CLIENT_AUTHENTICATION = None
HTTP_APP_KEY = None
GITHUB_OAUTH = None
FEISHU_OAUTH = None
OAUTH_CONFIG = None

REGISTER_ENABLED = 1
DISABLE_PASSWORD_LOGIN = False
SANDBOX_HOST = None
STRONG_TEST_COUNT = 8

# 邮件
SMTP_CONF = None
MAIL_SERVER = ""
MAIL_PORT = 0
MAIL_USE_SSL = True
MAIL_USE_TLS = False
MAIL_USERNAME = ""
MAIL_PASSWORD = ""
MAIL_DEFAULT_SENDER: tuple = ()
MAIL_FRONTEND_URL = ""


# --- 函数 stub --- #

def init_settings() -> None:
    """RAGFlow 服务启动时调用以加载配置 — shoppilot 不需要做任何事。"""


def print_rag_settings() -> None:  # noqa: D401
    """RAGFlow 服务的诊断函数，stub。"""


def get_svr_queue_name(priority: int = 0) -> str:
    return "rag_flow_svr_queue" if priority == 0 else f"rag_flow_svr_queue_{priority}"


def get_svr_queue_names() -> list[str]:
    return [get_svr_queue_name(p) for p in (1, 0)]


def get_secret_key() -> str | None:
    return SECRET_KEY


def check_and_install_torch() -> None:
    """RAGFlow 自动安装 torch 的辅助函数 — 我们已经直接管理依赖，stub。"""


# --- 兜底：访问未列出的属性时返回 None，避免 RAGFlow 内部代码 AttributeError --- #


def __getattr__(name: str) -> Any:
    # 只有当模块顶层未定义时才触发；避免无限递归
    return None
