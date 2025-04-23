"""查詢處理器 - 負責解析用戶查詢並生成搜尋URL"""

import logging
from typing import Dict, Any, Optional, List
from langsmith import traceable
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from .config import PARAM_EXTRACTION_PROMPT, DEFAULT_MODEL, SINYI_BASE_URL
from .utils import (
    extract_json_from_llm_response,
    generate_search_explanation,
    map_llm_params_to_internal,
)
from .url_builder import SinyiUrlBuilder
from .scraper import PropertyScraper

# 設定日誌
logger = logging.getLogger(__name__)


class WebQueryProcessor:
    """房地產網頁查詢處理器，負責解析用戶查詢並生成搜尋URL。"""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        """
        初始化處理器

        Args:
            model_name: 使用的語言模型名稱
        """
        self.model_name = model_name
        logger.info(f"初始化WebQueryProcessor，使用模型: {model_name}")

        self.llm = ChatGroq(model_name=model_name, temperature=0)

        self.scraper = PropertyScraper(self.llm)

    @traceable(name="sinyi_url_generator")
    def parse_query_to_url(self, query: str) -> Dict[str, Any]:
        """
        解析用戶查詢，並生成對應的信義房屋搜尋URL。

        Args:
            query: 用戶的自然語言查詢

        Returns:
            Dict: 包含處理結果的字典，包括URL和解析參數
        """
        logger.info(f"開始解析查詢: '{query}'")

        try:
            # 使用LLM解析查詢參數
            prompt = ChatPromptTemplate.from_messages(
                [("system", PARAM_EXTRACTION_PROMPT), ("human", query)]
            )

            # 調用LLM解析參數
            logger.debug(f"發送請求給LLM解析參數，查詢: '{query}'")
            response = self.llm.invoke(prompt.format_messages())

            # 從LLM回應中提取JSON
            raw_params = extract_json_from_llm_response(response.content)

            # 如果JSON解析失敗，嘗試手動提取參數
            if not raw_params:
                logger.warning("LLM JSON解析失敗，嘗試手動提取參數")
                raw_params = self._extract_params_manually(query)

            # 映射參數到內部格式
            params = map_llm_params_to_internal(raw_params)

            # 構建URL
            url = SinyiUrlBuilder.build_url(params, query)

            # 生成搜尋說明
            explanation = generate_search_explanation(params)
            logger.info(f"解析完成: {explanation}")

            return {
                "success": True,
                "url": url,
                "params": params,
                "explanation": explanation,
            }

        except Exception as e:
            logger.error(f"解析查詢時發生錯誤: {str(e)}")
            import traceback

            logger.debug(f"錯誤詳情: {traceback.format_exc()}")

            # 返回默認URL
            return {
                "success": False,
                "url": f"{SINYI_BASE_URL}/NewTaipei-city/1",
                "error": str(e),
                "explanation": "無法解析您的查詢，顯示新北市的預設搜尋結果。",
            }

    def _extract_params_manually(self, query: str) -> Dict[str, Any]:
        """
        當JSON解析失敗時，嘗試手動提取關鍵參數

        Args:
            query: 用戶的自然語言查詢

        Returns:
            Dict: 提取的參數字典
        """
        from .config import CITY_MAPPING, DISTRICT_ZIP_MAPPING, TYPE_MAPPING

        logger.info(f"開始手動提取參數: '{query}'")
        params = {}

        # 嘗試提取城市
        for city, code in CITY_MAPPING.items():
            if city in query:
                params["城市"] = city
                logger.debug(f"手動提取城市: {city}")
                break

        # 嘗試提取行政區
        for district, zip_code in DISTRICT_ZIP_MAPPING.items():
            if district in query:
                params["行政區"] = district
                logger.debug(f"手動提取行政區: {district}")
                break

        # 嘗試提取房屋類型
        house_types = []
        for house_type, type_code in TYPE_MAPPING.items():
            if house_type in query:
                house_types.append(house_type)
                logger.debug(f"手動提取房屋類型: {house_type}")

        if house_types:
            params["房屋類型"] = house_types

        # 檢查特殊關鍵字
        if "捷運" in query:
            params["關鍵字"] = "捷運"
            logger.debug("手動提取關鍵字: 捷運")

        # 檢查特殊條件
        if "車位" in query:
            if "有車位" in query or "含車位" in query:
                params["車位"] = "有車位"
                logger.debug("手動提取條件: 有車位")
            elif "無車位" in query or "不含車位" in query:
                params["車位"] = "無車位"
                logger.debug("手動提取條件: 無車位")

        logger.info(f"手動提取完成，找到 {len(params)} 個參數")
        return params

    async def process_web_query(
        self, query: str, scrape_results: bool = True
    ) -> Dict[str, Any]:
        """
        處理網頁搜尋查詢，解析參數、生成URL並可選擇性地抓取結果

        Args:
            query: 用戶的自然語言查詢
            scrape_results: 是否抓取和分析結果

        Returns:
            Dict: 處理結果字典
        """
        logger.info(f"開始處理Web查詢: '{query}'，抓取結果: {scrape_results}")

        # 解析URL
        url_result = self.parse_query_to_url(query)

        if not url_result["success"]:
            logger.warning("URL解析失敗，返回錯誤結果")
            return url_result

        # 如果需要抓取數據
        if scrape_results:
            try:
                data = await self.scraper.scrape_property_listings(url_result["url"])
                url_result["data"] = data
                url_result["properties_count"] = len(data) if data else 0
            except Exception as e:
                logger.error(f"爬取數據時發生錯誤: {str(e)}")
                url_result["error_scraping"] = str(e)
                url_result["data"] = None
                url_result["properties_count"] = 0

        return url_result
