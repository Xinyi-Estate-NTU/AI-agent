# AI_agent/config.py
import os
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory
from langsmith import Client

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

#########################################################
# 系統常數
#########################################################
# 目前年份設定
CURRENT_YEAR = 2025

# 輸入類型常量
INPUT_TYPE_GENERAL = "general"
INPUT_TYPE_DATA_ANALYSIS = "data_analysis"


# 查詢類型常量
class QueryType(Enum):
    PLOT = "plot"  # 製圖
    AVERAGE_PRICE = "price"  # 平均價格
    OTHER = "other"  # 其他類型


# 平均價格相關關鍵詞
PRICE_KEYWORDS = [
    "房價",
    "價格",
    "行情",
    "均價",
    "單價",
    "多少錢",
    "價位",
    "平均",
    "值多少",
    "房子多少",
    "一坪",
    "每坪",
]

# 製圖相關關鍵詞
PLOT_KEYWORDS = [
    "圖表",
    "統計圖",
    "長條圖",
    "折線圖",
    "圓餅圖",
    "視覺化",
    "趨勢圖",
    "分布圖",
    "比較圖",
    "走勢",
    "顯示",
    "製圖",
    "畫出",
    "繪製",
    "視覺呈現",
    "圖形",
    "趨勢",
    "走勢",
    "變化",
    "漲跌",
    "成長",
    "歷史",
]

#########################################################
# 模型和 LangSmith 設定
#########################################################
# LLM 模型設定
MODELS = [
    "llama3-8b-8192",
    "llama3-70b-8192",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
]
DEFAULT_MODEL = MODELS[0]

# 默認LLM實例
DEFAULT_LLM = ChatGroq(model_name=DEFAULT_MODEL, temperature=0)

# 創建持久化記憶存儲
CONVERSATION_MEMORY = ConversationBufferMemory(
    memory_key="chat_history", return_messages=True
)

# LangSmith設定
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT")
LANGSMITH_CLIENT = Client()
SESSION_ID = "thread-id-1"
LANGSMITH_EXTRA = {
    "project_name": LANGSMITH_PROJECT,
    "metadata": {"session_id": SESSION_ID},
}

#########################################################
# 地理位置資料
#########################################################
# 台北市行政區列表
TAIPEI_DISTRICTS = [
    "大安區",
    "信義區",
    "中正區",
    "松山區",
    "大同區",
    "萬華區",
    "文山區",
    "南港區",
    "內湖區",
    "士林區",
    "北投區",
]

# 新北市行政區列表
NEW_TAIPEI_DISTRICTS = [
    "板橋區",
    "三重區",
    "中和區",
    "永和區",
    "新莊區",
    "新店區",
    "土城區",
    "蘆洲區",
    "汐止區",
    "樹林區",
    "淡水區",
    "三峽區",
    "鶯歌區",
    "林口區",
    "五股區",
    "泰山區",
    "瑞芳區",
    "八里區",
    "深坑區",
    "石碇區",
    "三芝區",
    "金山區",
    "萬里區",
    "平溪區",
    "雙溪區",
    "貢寮區",
    "坪林區",
    "石門區",
    "烏來區",
]

# 合併兩市行政區，用於包含所有可能的區域搜索
ALL_DISTRICTS = TAIPEI_DISTRICTS + NEW_TAIPEI_DISTRICTS

# 區域簡稱映射
DISTRICT_MAPPING = {
    # 台北市
    "大安": "大安區",
    "信義": "信義區",
    "中正": "中正區",
    "松山": "松山區",
    "大同": "大同區",
    "萬華": "萬華區",
    "文山": "文山區",
    "南港": "南港區",
    "內湖": "內湖區",
    "士林": "士林區",
    "北投": "北投區",
    # 新北市
    "板橋": "板橋區",
    "三重": "三重區",
    "中和": "中和區",
    "永和": "永和區",
    "新莊": "新莊區",
    "新店": "新店區",
    "土城": "土城區",
    "蘆洲": "蘆洲區",
    "汐止": "汐止區",
    "樹林": "樹林區",
    "淡水": "淡水區",
}

# 有效的城市列表 (統一命名格式)
VALID_CITIES = ["台北市", "新北市"]

# 有效的行政區映射 (擴展 DISTRICT_MAPPING)
VALID_DISTRICTS = {"台北市": TAIPEI_DISTRICTS, "新北市": NEW_TAIPEI_DISTRICTS}

# 結構化輸出回應 schemas 配置
RESPONSE_SCHEMAS_CONFIG = [
    {
        "name": "城市",
        "description": "查詢的城市，必須是以下城市之一：台北市、新北市。注意：統一使用「台北市」而非「臺北市」",
        "type": "string",
        "examples": ["台北市", "新北市"],
    },
    {
        "name": "鄉鎮市區",
        "description": "行政區，必須是有效的行政區名稱，例如「大安區」、「信義區」等",
        "type": "string",
        "examples": ["大安區", "信義區", "中正區", "板橋區"],
    },
    {
        "name": "時間範圍",
        "description": "查詢的時間範圍。如果用戶未明確提及時間範圍，請返回null。時間範圍必須是JSON格式，包含start_year、end_year和description三個字段",
        "examples": [
            {"start_year": 2020, "end_year": 2024, "description": "2020-2024年"},
            {
                "start_year": 2023,
                "end_year": 2024,
                "description": "近兩年（2023-2024）",
            },
            None,
        ],
    },
    {
        "name": "建物現況格局-房",
        "description": "房間數量，必須是阿拉伯數字（整數），如果查詢中未提及則返回null",
        "type": "integer",
        "examples": [2, 3, 4, None],
    },
    {
        "name": "建物現況格局-廳",
        "description": "客廳數量，必須是阿拉伯數字（整數），如果查詢中未提及則返回null",
        "type": "integer",
        "examples": [1, 2, None],
    },
    {
        "name": "建物現況格局-衛",
        "description": "衛浴數量，必須是阿拉伯數字（整數），如果查詢中未提及則返回null",
        "type": "integer",
        "examples": [1, 2, None],
    },
    {
        "name": "電梯",
        "description": "有無電梯，值必須是「有」或「無」，如果查詢中未提及則返回null",
        "type": "string",
        "examples": ["有", "無", None],
    },
    {
        "name": "屋齡",
        "description": "屋齡年數，必須是阿拉伯數字（整數），如果查詢中未提及則返回null",
        "type": "integer",
        "examples": [5, 10, 30, None],
    },
]

# 解析查詢模板 (將模板移至配置中，以便統一管理)
QUERY_PARSING_TEMPLATE = """
你是一個專門處理台灣房地產查詢的助手。從用戶查詢中提取以下關鍵參數。

【格式要求】
1. 所有數字必須使用阿拉伯數字，禁止使用中文數字
2. 地名統一使用「台北市」而非「臺北市」
3. 電梯狀態只能使用「有」或「無」
4. 房、廳、衛的數量必須是整數
5. 未提及的字段必須返回null，不要猜測或默認值

【時間範圍處理規則】
當前年份為{current_year}年。
1. 如果查詢包含明確的時間範圍（如「2020年」、「2018到2022年」），提取該範圍
2. 如果包含「近X年」，計算確切的年份範圍。例如，「近兩年」表示{current_year_minus_1}年至{current_year}年
3. 如果用戶完全沒有提及任何時間範圍，將「時間範圍」設為null

【有效的城市和行政區】
有效城市: 台北市, 新北市
台北市行政區: {taipei_districts}
新北市行政區: {new_taipei_districts}

【輸出範例】
範例1 - 完整查詢:
{{
  "城市": "台北市",
  "鄉鎮市區": "大安區",
  "時間範圍": {{
    "start_year": 2022,
    "end_year": 2024,
    "description": "近三年（2022-2024）"
  }},
  "建物現況格局-房": 3,
  "建物現況格局-廳": 2,
  "建物現況格局-衛": 1,
  "電梯": "有",
  "屋齡": 15
}}

範例2 - 部分查詢:
{{
  "城市": "新北市",
  "鄉鎮市區": "淡水區",
  "時間範圍": null,
  "建物現況格局-房": null,
  "建物現況格局-廳": null,
  "建物現況格局-衛": null,
  "電梯": null,
  "屋齡": null
}}

{format_instructions}

用戶查詢: {query}
"""
