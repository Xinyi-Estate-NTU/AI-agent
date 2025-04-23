"""配置和常量定義 - 房地產網頁搜尋代理配置"""

from typing import Dict, List, Any
import logging

# 設定日誌
logger = logging.getLogger(__name__)

# 從現有的配置導入相關設定
from data_agent.config import DEFAULT_MODEL, MODELS, CONVERSATION_MEMORY

# URL 基礎
SINYI_BASE_URL = "https://www.sinyi.com.tw/buy/list"

# 城市對應
CITY_MAPPING = {
    "台北": "Taipei-city",
    "台北市": "Taipei-city",
    "新北": "NewTaipei-city",
    "新北市": "NewTaipei-city",
}

# 行政區對應 (郵遞區號)
DISTRICT_ZIP_MAPPING = {
    # 台北市
    "中正區": "100", "大同區": "103", "中山區": "104", "松山區": "105",
    "大安區": "106", "萬華區": "108", "信義區": "110", "士林區": "111", 
    "北投區": "112", "內湖區": "114", "南港區": "115", "文山區": "116",
    # 新北市
    "萬里區": "207", "金山區": "208", "板橋區": "220", "汐止區": "221",
    "深坑區": "222", "石碇區": "223", "瑞芳區": "224", "平溪區": "226",
    "雙溪區": "227", "貢寮區": "228", "新店區": "231", "坪林區": "232",
    "烏來區": "233", "永和區": "234", "中和區": "235", "土城區": "236",
    "三峽區": "237", "樹林區": "238", "鶯歌區": "239", "三重區": "241",
    "新莊區": "242", "泰山區": "243", "林口區": "244", "蘆洲區": "247",
    "五股區": "248", "八里區": "249", "淡水區": "251", "三芝區": "252",
    "石門區": "253",
}

# 房屋類型對應
TYPE_MAPPING = {
    "公寓": "apartment",
    "大樓": "dalou",
    "套房": "flat",
    "別墅": "townhouse-villa",
    "透天": "townhouse-villa",
    "辦公": "office",
}

# 標籤對應
TAG_MAPPING = {
    "有陽台": "4",
    "游泳池": "9",
    "健身房": "8",
    "警衛管理": "12",
    "近捷運": "17",
    "近公園": "19",
    "近學校": "16",
    "近市場": "18",
}

# 設施標籤查詢映射
AMENITY_TAG_MAPPING = {
    "近學校": "16",
    "近公園": "19", 
    "有游泳池": "9", 
    "有健身房": "8",
    "近捷運站": "17",
    "近市場": "18",
    "有陽台": "4",
    "有警衛管理": "12"
}

# 系統提示詞 - 參數提取
PARAM_EXTRACTION_PROMPT = """你是一個房地產搜尋URL生成器。你需要解析用戶的自然語言查詢，並提取以下參數：

1. 城市（city）：例如台北市、新北市
2. 行政區（district）：例如大安區、信義區、新店區等
3. 房屋類型（property_type）：公寓、大樓、套房、別墅/透天、辦公室
4. 價格範圍（price_range）：例如"200萬以上"，"500-1000萬"等
5. 坪數範圍（area_range）：例如"10坪以上"，"20-30坪"等
6. 房間數（rooms）：例如"1-2房"，"3房以上"等
7. 樓層（floor）：例如"1樓以上"，"5樓以下"等
8. 屋齡（year）：例如"5年以下"，"10年以上"等
9. 特殊條件（special_conditions）：例如"有車位"、"無車位"、"排除4樓"等
10. 設施標籤（amenities）：例如"近捷運"、"近公園"、"游泳池"、"健身房"等
11. 關鍵字（keyword）：例如某捷運站名、學區名等

請輸出JSON格式，只包含在查詢中明確提到的參數。不要添加假設的參數。
"""


# Define schema for extraction
EXTRACT_SCHEMA = {
    "name": "Real Estate Listings",
    "baseSelector": "//div[contains(@class, 'buy-list-item')]",
    "fields": [
        {
            "name": "property_name",
            "selector": ".//div[contains(@class, 'LongInfoCard_Type_Name')]",
            "type": "text"
        },
        {
            "name": "community_name", 
            "selector": ".//span[contains(@class, 'longInfoCard_communityName')]",
            "type": "text"
        },
        {
            "name": "location",
            "selector": ".//div[contains(@class, 'LongInfoCard_Type_Address')]//span[1]",
            "type": "text"
        },
        {
            "name": "property_age",
            "selector": ".//div[contains(@class, 'LongInfoCard_Type_Address')]//span[2]",
            "type": "text"
        },
        {
            "name": "property_type",
            "selector": ".//div[contains(@class, 'LongInfoCard_Type_Address')]//span[3]",
            "type": "text"
        },
        {
            "name": "total_size",
            "selector": ".//div[contains(@class, 'LongInfoCard_Type_HouseInfo')]//span[1]",
            "type": "text"
        },
        {
            "name": "main_size",
            "selector": ".//div[contains(@class, 'LongInfoCard_Type_HouseInfo')]//span[contains(text(), '主 + 陽')]",
            "type": "text"
        },
        {
            "name": "layout",
            "selector": ".//div[contains(@class, 'LongInfoCard_Type_HouseInfo')]//span[contains(text(), '房')]",
            "type": "text"
        },
        {
            "name": "floor",
            "selector": ".//div[contains(@class, 'LongInfoCard_Type_HouseInfo')]//span[contains(text(), '樓')]",
            "type": "text"
        },
        {
            "name": "parking",
            "selector": ".//span[contains(@class, 'LongInfoCard_Type_Parking')]/span",
            "type": "text"
        },
        {
            "name": "original_price",
            "selector": ".//span[contains(@style, 'text-decoration: line-through')]",
            "type": "text"
        },
        {
            "name": "current_price",
            "selector": ".//span[contains(@style, 'font-weight: 500; color: rgb(221, 37, 37)')]",
            "type": "text"
        },
        {
            "name": "price_unit",
            "selector": ".//span[contains(@style, 'font-weight: 500; color: rgb(221, 37, 37)')]/following-sibling::span[1]",
            "type": "text"
        },
        {
            "name": "discount_percentage",
            "selector": ".//div[contains(@class, 'longInfoCard_lowprice')]//span[not(contains(@style, 'color'))]",
            "type": "text"
        },
        {
            "name": "features",
            "selector": ".//span[contains(@class, 'longInfoCard_specificTag')]",
            "type": "list",
            "fields": [
                {"name": "feature", "type": "text"}
            ]
        },
        {
            "name": "interest_count",
            "selector": ".//span[contains(@class, 'longInfoCard_clicks')]//span[contains(@style, 'color: rgb(222, 37, 37)')]",
            "type": "text"
        },
        {
            "name": "has_manager_recommend",
            "selector": ".//div[contains(@class, 'longInfoCard_bossgreat')]",
            "type": "boolean"
        },
        {
            "name": "has_3d_vr",
            "selector": ".//div[contains(@class, 'LongInfoCard_VRicon')]/img",
            "type": "boolean"
        },
        {
            "name": "image_url",
            "selector": ".//div[contains(@class, 'longInfoCard_largeImg')]/img",
            "type": "attribute",
            "attribute": "src"
        }
    ]
}

