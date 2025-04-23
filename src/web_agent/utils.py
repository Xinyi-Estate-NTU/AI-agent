"""工具函數 - 房地產網頁搜尋代理輔助功能"""

import re
import json
import logging
from typing import Dict, Any, Optional, List

# 設定日誌
logger = logging.getLogger(__name__)

def extract_json_from_llm_response(response_content: str) -> Dict[str, Any]:
    """
    從LLM回應中提取JSON數據
    
    Args:
        response_content: LLM回應的原始文本
        
    Returns:
        Dict: 解析後的JSON數據
    """
    logger.debug(f"嘗試從LLM回應提取JSON: {response_content[:100]}...")
    
    # 尋找JSON模式的內容
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_content)
    if json_match:
        json_str = json_match.group(1)
        logger.debug("從Markdown代碼塊中提取JSON")
    else:
        json_str = response_content
        logger.debug("未找到Markdown代碼塊，使用整個回應")
        
    # 清理非JSON內容
    json_str = re.sub(r'^[^{]*', '', json_str)
    json_str = re.sub(r'[^}]*$', '', json_str)
    
    try:
        params = json.loads(json_str)
        logger.info(f"成功解析JSON: 找到 {len(params)} 個參數")
        return params
    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失敗: {str(e)}, JSON字符串: {json_str}")
        return {}

def parse_range_param(value, suffix: str) -> str:
    """
    解析各種範圍參數並轉換為URL格式
    
    Args:
        value: 要解析的值
        suffix: URL參數後綴
        
    Returns:
        str: 格式化的URL參數
    
    Examples:
        "10坪以上" -> "10-up-area"
        "5-10年" -> "5-10-year"
    """
    if not value:
        return ""
    
    # 記錄處理過程
    logger.debug(f"解析範圍參數: {value}, 後綴: {suffix}")
    
    # 轉換為字符串
    if not isinstance(value, str):
        value = str(value)
    
    # 檢查是否包含「以上」「以下」
    if "以上" in value:
        num = re.search(r'\d+', value)
        if num:
            result = f"{num.group(0)}-up-{suffix}"
            logger.debug(f"解析為「以上」範圍: {result}")
            return result
    elif "以下" in value:
        num = re.search(r'\d+', value)
        if num:
            result = f"{num.group(0)}-down-{suffix}"
            logger.debug(f"解析為「以下」範圍: {result}")
            return result
    
    # 檢查範圍格式
    range_match = re.search(r'(\d+)[-~到至](\d+)', value)
    if range_match:
        result = f"{range_match.group(1)}-{range_match.group(2)}-{suffix}"
        logger.debug(f"解析為範圍值: {result}")
        return result
    
    # 如果只有數字，檢查是否為單一值
    num_match = re.search(r'^\d+$', value.strip())
    if num_match:
        if suffix == "room":  # 特別處理房間數
            result = f"1-{value.strip()}-{suffix}"
            logger.debug(f"解析為房間數範圍: {result}")
            return result
        else:
            result = f"{value.strip()}-up-{suffix}"
            logger.debug(f"解析為預設「以上」範圍: {result}")
            return result
    
    logger.debug(f"無法解析範圍參數: {value}")
    return ""

def generate_search_explanation(params: Dict[str, Any]) -> str:
    """
    根據解析的參數生成人類可讀的搜尋說明
    
    Args:
        params: 解析的參數字典
        
    Returns:
        str: 人類可讀的搜尋說明
    """
    parts = []
    
    if "城市" in params:
        parts.append(params["城市"])
    
    if "行政區" in params:
        parts.append(params["行政區"])
    
    if "房屋類型" in params:
        if isinstance(params["房屋類型"], list):
            parts.append("、".join(params["房屋類型"]))
        else:
            parts.append(str(params["房屋類型"]))
    
    if "設施標籤" in params:
        if isinstance(params["設施標籤"], list):
            parts.append("、".join(params["設施標籤"]))
        else:
            parts.append(str(params["設施標籤"]))
    
    if "關鍵字" in params:
        parts.append(f"關鍵字「{params['關鍵字']}」")
    
    if "價格範圍" in params:
        parts.append(f"價格{params['價格範圍']}")
    
    if "坪數範圍" in params:
        parts.append(f"坪數{params['坪數範圍']}")
    
    if "排除4樓" in params and params["排除4樓"]:
        parts.append("排除4樓")
    
    if "車位" in params:
        parts.append(params["車位"])
    
    if parts:
        return "搜尋：" + "，".join(parts)
    else:
        return "搜尋全部房屋"

def map_llm_params_to_internal(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    將LLM輸出的參數映射到內部使用的參數格式
    
    Args:
        params: LLM輸出的參數字典
        
    Returns:
        Dict: 轉換後的內部參數字典
    """
    logger.debug(f"將LLM參數映射到內部格式: {params}")
    
    # 深拷貝避免修改原始數據
    import copy
    result = copy.deepcopy(params)
    
    # 映射常見欄位
    field_mappings = {
        "city": "城市",
        "district": "行政區",
        "property_type": "房屋類型",
        "price_range": "價格範圍",
        "area_range": "坪數範圍", 
        "rooms": "房間數",
        "floor": "樓層",
        "year": "屋齡",
        "amenities": "設施標籤",
        "keyword": "關鍵字"
    }
    
    # 執行轉換
    for eng_field, ch_field in field_mappings.items():
        if eng_field in result:
            # 特殊處理房屋類型欄位，確保是列表
            if eng_field == "property_type":
                value = result.pop(eng_field)
                if isinstance(value, list):
                    result[ch_field] = value
                else:
                    result[ch_field] = [value]
            else:
                result[ch_field] = result.pop(eng_field)
    
    # 特殊處理特殊條件
    if "special_conditions" in result:
        conditions = result.pop("special_conditions")
        if isinstance(conditions, list):
            for condition in conditions:
                process_special_condition(result, condition)
        else:
            process_special_condition(result, conditions)
    
    logger.debug(f"映射後的內部參數: {result}")
    return result

def process_special_condition(params: Dict[str, Any], condition: str):
    """處理特殊條件"""
    if "有車位" in condition:
        params["車位"] = "有車位"
    elif "無車位" in condition:
        params["車位"] = "無車位"
    elif "排除4樓" in condition or "不要4樓" in condition:
        params["排除4樓"] = True