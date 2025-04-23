# src/web_agent/__init__.py
"""房地產網頁搜尋代理 - 從自然語言查詢生成搜尋URL並分析結果"""

import logging
from typing import Dict, Any, Optional

# 設定日誌 - 避免重複日誌輸出
logger = logging.getLogger(__name__)

# 防止日誌重複輸出 - 只保留一個處理器
if logger.hasHandlers():
    # 如果已經有處理器，則移除所有處理器
    logger.handlers.clear()

# 只讓根處理器處理輸出，避免重複日誌
logger.propagate = True

# 公開API接口
from .api import (
    process_web_query,
    get_default_model,
    get_available_models,
    get_conversation_memory,
)

__all__ = [
    "process_web_query",
    "get_default_model",
    "get_available_models",
    "get_conversation_memory",
]
