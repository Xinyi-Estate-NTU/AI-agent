# AI_agent/utils.py
import re
import logging
import json
import datetime
from typing import Optional, Dict, Any, List, Tuple
from langchain.schema import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import ChatPromptTemplate
from .config import (
    TAIPEI_DISTRICTS, NEW_TAIPEI_DISTRICTS, ALL_DISTRICTS, 
    DISTRICT_MAPPING, PRICE_KEYWORDS, PLOT_KEYWORDS, QueryType,
    CURRENT_YEAR, VALID_CITIES, VALID_DISTRICTS, 
    RESPONSE_SCHEMAS_CONFIG, QUERY_PARSING_TEMPLATE
)

logger = logging.getLogger(__name__)

def dict_to_langchain_messages(messages: List[Dict[str, str]]) -> List[BaseMessage]:
    """將字典消息轉換為LangChain消息對象。"""
    lc_messages = []
    for msg in messages:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))
        elif msg["role"] == "system":
            lc_messages.append(SystemMessage(content=msg["content"]))
    return lc_messages

def langchain_messages_to_dict(messages: List[BaseMessage]) -> List[Dict[str, str]]:
    """將LangChain消息對象轉換為字典消息。"""
    dict_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            dict_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            dict_messages.append({"role": "assistant", "content": msg.content})
        elif isinstance(msg, SystemMessage):
            dict_messages.append({"role": "system", "content": msg.content})
    return dict_messages

def identify_query_type(text: str, parsed_params=None, llm_service=None) -> QueryType:
    """通過關鍵詞和規則識別查詢類型。
    
    Args:
        text: 查詢文本
        parsed_params: 已經解析好的查詢參數，如果提供則直接使用
        llm_service: LLM服務，如果parsed_params未提供則必須提供此參數
        
    Returns:
        查詢類型
    """
    # 初始化變數
    has_city = False
    has_district = False
    
    # 如果提供了已解析的參數，優先使用
    if parsed_params:
        city = parsed_params.get("城市")
        district = parsed_params.get("鄉鎮市區")
        has_city = city is not None
        has_district = district is not None
    # 如果沒有提供已解析參數且提供了llm_service，用LLM解析
    elif llm_service:
        try:
            query_params = parse_query_to_json(llm_service, text)
            city = query_params.get("城市")
            district = query_params.get("鄉鎮市區")
            has_city = city is not None
            has_district = district is not None
        except Exception as e:
            logger.error(f"使用 parse_query_to_json 獲取城市和行政區失敗: {e}")
            # 仍然設置為False，因為我們沒有獲取到任何信息
    else:
        logger.error("需要提供 parsed_params 或 llm_service 才能識別查詢類型")
    
    # 查詢類型識別邏輯
    # 規則1: 製圖類查詢
    if any(keyword in text for keyword in PLOT_KEYWORDS):
        return QueryType.PLOT
    
    # 規則2: 平均價格查詢
    if any(keyword in text for keyword in PRICE_KEYWORDS):
        if has_city or has_district:
            return QueryType.AVERAGE_PRICE
    
    # 規則3: 更複雜的平均價格查詢模式
    price_patterns = [
        r'(新北市|台北市|臺北市).*?(房價|價格|行情|均價|單價|多少錢)',
        r'(房價|價格|行情|均價|單價).*?(新北市|台北市|臺北市)',
        r'(大安|信義|中正|松山|大同|萬華|文山|南港|內湖|士林|北投|板橋|三重|中和|永和|新莊|新店|汐止|淡水).*?(房價|價格|行情|均價|單價)',
        r'(房價|價格|行情|均價|單價).*?(大安|信義|中正|松山|大同|萬華|文山|南港|內湖|士林|北投|板橋|三重|中和|永和|新莊|新店|汐止|淡水)',
        r'(大安區|信義區|中正區|松山區|大同區|萬華區|文山區|南港區|內湖區|士林區|北投區|板橋區|三重區|中和區|永和區|新莊區|新店區|汐止區|淡水區).*?(多少|如何)'
    ]
    
    for pattern in price_patterns:
        if re.search(pattern, text):
            return QueryType.AVERAGE_PRICE
    
    # 規則4: 短查詢 + 城市或行政區可能是隱含的價格查詢
    if (has_city or has_district) and len(text) < 25:
        return QueryType.AVERAGE_PRICE
    
    # 默認為其他類型
    return QueryType.OTHER

def parse_query_to_json(llm_service, query_text: str) -> Dict[str, Any]:
    """使用 StructuredOutputParser 解析房地產查詢"""
    logger.debug(f"開始解析查詢: '{query_text}'")
    
    # 從配置創建 ResponseSchema 對象
    response_schemas = [
        ResponseSchema(**schema_config)
        for schema_config in RESPONSE_SCHEMAS_CONFIG
    ]
    
    # 創建 parser
    output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = output_parser.get_format_instructions()
    
    # 建立提示模板，直接使用配置中的模板
    template = QUERY_PARSING_TEMPLATE
    
    # 格式化提示詞
    prompt = ChatPromptTemplate.from_template(template)
    formatted_prompt = prompt.format(
        format_instructions=format_instructions,
        query=query_text,
        current_year=CURRENT_YEAR,
        current_year_minus_1=CURRENT_YEAR-1,
        taipei_districts=", ".join(TAIPEI_DISTRICTS),
        new_taipei_districts=", ".join(NEW_TAIPEI_DISTRICTS)
    )
    
    try:
        # 調用 LLM
        response = llm_service.llm.invoke(formatted_prompt)
        
        # 解析回應
        parsed_output = output_parser.parse(response.content)
        
        # 處理時間範圍 (可能以字符串形式返回)
        if parsed_output.get("時間範圍") and parsed_output["時間範圍"] not in [None, "null"]:
            if isinstance(parsed_output["時間範圍"], str):
                # 處理JSON格式時間範圍
                if parsed_output["時間範圍"].startswith('{') and parsed_output["時間範圍"].endswith('}'):
                    try:
                        time_range = json.loads(parsed_output["時間範圍"])
                        parsed_output["時間範圍"] = time_range
                    except:
                        logger.warning(f"無法解析JSON時間範圍: {parsed_output['時間範圍']}")
        
        # 確保有時間範圍 - 如果沒有指定或為null，默認為2015-2024
        if "時間範圍" not in parsed_output or parsed_output["時間範圍"] in [None, "null"]:
            parsed_output["時間範圍"] = {
                "start_year": 2015,
                "end_year": 2024,
                "description": "2015-2024年"
            }
            logger.info(f"未指定時間範圍，使用默認值: {parsed_output['時間範圍']}")
        
        logger.info(f"成功解析查詢參數: {parsed_output}")
        return parsed_output
    
    except Exception as e:
        logger.error(f"解析查詢參數失敗: {str(e)}")
        # 返回包含默認時間範圍的最小字典
        default_output = {
            "時間範圍": {
                "start_year": 2015,
                "end_year": 2024,
                "description": "2015-2024年(默認)"
            }
        }
        logger.info(f"解析失敗，返回默認參數: {default_output}")
        return default_output