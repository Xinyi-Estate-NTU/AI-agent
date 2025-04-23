"""公共API接口 - 房地產網頁搜尋代理"""

import logging
from typing import Dict, Any, Optional
from langsmith import traceable

from .processor import WebQueryProcessor
from .config import DEFAULT_MODEL, MODELS, CONVERSATION_MEMORY

# 設定日誌
logger = logging.getLogger(__name__)

@traceable(name="web_search_query")
async def process_web_query(question: str, model_name: Optional[str] = None, scrape_results: bool = True) -> Dict[str, Any]:
    """
    處理網頁搜尋查詢，生成對應的URL並可選擇性地抓取結果。
    
    Args:
        question: 用戶的自然語言查詢
        model_name: 使用的語言模型名稱
        scrape_results: 是否抓取和分析結果
        
    Returns:
        Dict: 包含處理結果的字典
    """
    logger.info(f"API調用: 處理Web查詢: '{question}'")
    
    # 初始化處理器
    processor = WebQueryProcessor(model_name or DEFAULT_MODEL)
    
    # 處理查詢
    result = await processor.process_web_query(question, scrape_results)
    
    if result.get("success", False):
        logger.info(f"查詢處理成功: {result.get('explanation', '')}")
    else:
        logger.warning(f"查詢處理失敗: {result.get('error', 'Unknown error')}")
    
    return result

def get_default_model() -> str:
    """獲取默認模型名稱。"""
    return DEFAULT_MODEL

def get_available_models() -> list:
    """獲取所有可用模型列表。"""
    return MODELS

def get_conversation_memory():
    """獲取對話記憶體實例。"""
    return CONVERSATION_MEMORY
