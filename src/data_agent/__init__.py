# AI_agent/__init__.py
"""Taiwan Real Estate AI Agent module."""

# 匯出主要API，方便直接從包導入
from .api import (
    chat_pipeline,
    query_sales_data,
    process_real_estate_query,
    get_default_model,
    get_available_models,
    get_conversation_memory,
)
from .config import (
    MODELS,
    DEFAULT_MODEL,
    CONVERSATION_MEMORY,
    LANGSMITH_PROJECT,
    QueryType,
)
from .query_processor import RealEstateQueryProcessor
from .data_analysis import RealEstateAnalyzer

# 初始化日誌
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("AI_agent 初始化完成")
