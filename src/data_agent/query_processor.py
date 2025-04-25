# AI_agent/query_processor.py
import logging
import re
from typing import Optional, Dict, Any
import pandas as pd
import traceback
from langsmith import traceable
from langchain_groq import ChatGroq
from langchain.agents.agent_types import AgentType

from .config import DEFAULT_MODEL, QueryType
from .data_loader import DataLoader
from .utils import identify_query_type, parse_query_to_json
from .data_analysis import RealEstateAnalyzer  # 導入新的分析器

logger = logging.getLogger(__name__)


class LLMService:
    """LLM服務，負責提供LLM相關功能。"""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.llm = ChatGroq(
            model_name=model_name,
            temperature=0,
            # the following parameters only works in certain models
            # service_name="房地產查詢解析服務",
            # description="從用戶查詢中提取房地產查詢相關參數",
            # response_mode="structured"
        )

    def extract_query_params(self, text: str) -> Dict[str, Any]:
        """使用統一的 parse_query_to_json 函數解析查詢參數"""

        logger.info(f"開始處理查詢: '{text}'")
        try:
            # 統一調用 parse_query_to_json
            result = parse_query_to_json(self, text)
            logger.info(f"成功解析查詢參數: {result}")
            return result
        except Exception as e:
            logger.error(f"使用結構化解析處理查詢時出錯: {e}")
            logger.debug(traceback.format_exc())
            return {}


class RealEstateQueryProcessor:
    """房地產查詢處理器，負責處理和執行房地產查詢。"""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.llm_service = LLMService(model_name)
        self.data_loader = DataLoader()
        self.analyzer = RealEstateAnalyzer()  # 創建分析器實例

    def handle_average_price_query(
        self, text: str, parsed_params=None
    ) -> Dict[str, Any]:
        """
        處理房價查詢，使用 JSON 模式解析查詢參數

        Args:
            text: 用戶查詢文本
            parsed_params: 已解析的查詢參數，如果提供則不再重新解析

        Returns:
            Dict: 包含處理結果的字典
        """

        logger.info(f"處理房價查詢: {text}")

        try:
            # 如果沒有提供已解析的參數，調用parse_query_to_json
            if not parsed_params:
                parsed_params = parse_query_to_json(self.llm_service, text)

            city = parsed_params.get("城市")
            district = parsed_params.get("鄉鎮市區")

            # 如果沒有識別到城市，返回錯誤
            if not city:
                return {
                    "success": False,
                    "message": "未能識別查詢的城市，請指定一個城市，例如「台北市」。",
                    "result": "抱歉，我無法理解您查詢的城市。請明確指定您想查詢的城市，例如「台北市大安區的平均房價」。",
                }

            # 加載城市數據
            df = self.data_loader.load_city_data(city)
            if df is None or df.empty:
                return {
                    "success": False,
                    "message": f"無法加載 {city} 的數據或數據為空",
                    "result": f"抱歉，我找不到 {city} 的房價數據。",
                }

            # 提取其他過濾條件
            filters = {}
            if parsed_params.get("時間範圍"):
                filters["時間範圍"] = parsed_params.get("時間範圍")

            # 添加房型過濾條件
            for key in [
                "建物現況格局-房",
                "建物現況格局-廳",
                "建物現況格局-衛",
                "電梯",
                "屋齡",
            ]:
                if parsed_params.get(key) is not None:
                    filters[key] = parsed_params.get(key)

            # 計算平均房價
            result = self.analyzer.calculate_average_price(df, district, filters)

            # 格式化結果
            formatted_result = self.analyzer.format_price_result(result, city, filters)
            return formatted_result

        except Exception as e:
            logger.error(f"處理房價查詢時發生錯誤: {str(e)}")
            return {
                "success": False,
                "message": "處理查詢時發生錯誤",
                "result": "抱歉，處理您的查詢時出現了技術問題。請稍後再試或換一種方式提問。",
            }

    def handle_plot_query(self, query_text: str, parsed_params=None) -> Dict[str, Any]:
        """處理繪圖查詢，生成數據視覺化。"""
        logger.info(f"處理製圖查詢: '{query_text}'")

        try:
            # 如果沒有提供已解析的參數，調用parse_query_to_json
            if not parsed_params:
                parsed_params = parse_query_to_json(self.llm_service, query_text)

            city = parsed_params.get("城市")
            district = parsed_params.get("鄉鎮市區")

            # 如果沒有識別到城市，使用默認值
            if not city:
                city = "台北市"
                logger.info(f"未識別到城市，使用默認值: {city}")

            # 載入數據
            df = self.data_loader.load_city_data(city)

            # 決定圖表類型
            chart_type = "trend"  # 預設為趨勢圖

            # 可以根據查詢文本識別其他圖表類型
            if (
                "柱狀圖" in query_text
                or "長條圖" in query_text
                or "bar" in query_text.lower()
            ):
                chart_type = "bar"

            # 提取時間範圍
            time_range = parsed_params.get("時間範圍")
            logger.info(f"解析出的時間範圍: {time_range}")

            # 使用專用趨勢圖生成方法
            if (
                "趨勢" in query_text
                or "走勢" in query_text
                or "變化" in query_text
                or True
            ):  # 預設使用趨勢圖
                logger.info(f"使用圖表類型: {chart_type}")
                trend_result = self.analyzer.generate_price_trend_chart(
                    df, city, district, chart_type, time_range
                )

                # 處理結果
                if trend_result["success"]:
                    result = {
                        "success": True,
                        "message": f"成功生成房價{chart_type}圖",
                        "original_text": query_text,
                        "result": trend_result["result"],
                        "dataframe": trend_result.get("dataframe"),
                        "query_type": QueryType.PLOT.value,
                        "model_used": self.model_name,
                        "chart_type": chart_type,
                        "time_range": trend_result.get("time_range"),
                    }

                    # 確保將圖表相關信息添加到結果中
                    if trend_result.get("has_chart", False):
                        result["has_chart"] = True
                        result["chart_image"] = trend_result["chart_image"]
                        result["trend_direction"] = trend_result.get("trend_direction")

                    return result
                else:
                    return {
                        "success": False,
                        "message": trend_result.get("error", "生成圖表失敗"),
                        "result": trend_result.get("result", "無法生成房價趨勢圖"),
                        "query_type": QueryType.PLOT.value,
                        "model_used": self.model_name,
                    }
        except Exception as e:
            logger.error(f"處理製圖查詢時出錯: {e}")
            logger.debug(f"錯誤堆疊: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"處理製圖查詢時出錯: {str(e)}",
                "result": f"生成圖表時發生錯誤: {str(e)}",
                "query_type": QueryType.PLOT.value,
                "model_used": self.model_name,
            }

    def handle_area_search_query(self, text: str, parsed_params=None) -> Dict[str, Any]:
        """處理區域搜尋查詢，尋找符合條件的行政區。"""
        logger.info(f"處理區域搜尋查詢: '{text}'")

        try:
            # 如果沒有提供已解析的參數，調用parse_query_to_json
            if not parsed_params:
                parsed_params = parse_query_to_json(self.llm_service, text)

            city = parsed_params.get("城市")

            # 如果沒有識別到城市，使用默認值
            if not city:
                city = "臺北市"
                logger.info(f"未識別到城市，使用默認值: {city}")

            # 加載城市數據
            df = self.data_loader.load_city_data(city)
            if df is None or df.empty:
                return {
                    "success": False,
                    "message": f"無法加載 {city} 的數據或數據為空",
                    "result": f"抱歉，我找不到 {city} 的房價數據。",
                }

            # 尋找預算金額
            budget_patterns = [
                r"預算(\d+)[萬千億]",
                r"(\d+)[萬千億]以[內下]",
                r"(\d+)[萬千億]左右",
                r"只有(\d+)[萬千億]",
            ]

            budget = None
            for pattern in budget_patterns:
                match = re.search(pattern, text)
                if match:
                    budget = float(match.group(1))
                    break

            # 如果未找到預算，從文本中提取
            if budget is None:
                # 尋找所有數字+單位的組合
                amount_matches = re.findall(r"(\d+)([萬千億])", text)
                if amount_matches:
                    for amount, unit in amount_matches:
                        if unit == "萬":
                            budget = float(amount)
                            break
                        elif unit == "億":
                            budget = float(amount) * 10000
                            break
                        elif unit == "千":
                            budget = float(amount) / 10
                            break

            # 如果仍未找到預算，使用默認值
            if budget is None:
                budget = 2000  # 默認2000萬
                logger.info(f"未識別到預算，使用默認值: {budget}萬元")

            # 提取房間數要求
            min_rooms = 3  # 默認至少3房
            rooms_match = re.search(r"(\d+)房", text)
            if rooms_match:
                min_rooms = int(rooms_match.group(1))
            elif parsed_params.get("建物現況格局-房"):
                min_rooms = parsed_params.get("建物現況格局-房")

            # 提取電梯要求
            has_elevator = True  # 默認需要電梯
            if "電梯" in text and "無電梯" in text:
                has_elevator = False
            elif parsed_params.get("電梯") == "無":
                has_elevator = False

            # 執行區域搜尋
            result = self.analyzer.find_districts_within_budget(
                df, budget, min_rooms, has_elevator, city
            )

            # 格式化結果
            return {
                "success": result.get("success", False),
                "message": (
                    "成功分析符合預算的行政區"
                    if result.get("success", False)
                    else result.get("error", "分析失敗")
                ),
                "original_text": text,
                "result": result.get("result", ""),
                "affordable_districts": result.get("affordable_districts", {}),
                "district_sizes": result.get("district_sizes", {}),
                "closest_districts": result.get("closest_districts", {}),
                "budget": budget,
                "conditions": result.get("conditions", {}),
                "query_type": QueryType.AREA_SEARCH.value,
                "model_used": self.model_name,
            }

        except Exception as e:
            logger.error(f"處理區域搜尋查詢時出錯: {e}")
            logger.debug(f"錯誤堆疊: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"處理區域搜尋查詢時出錯: {str(e)}",
                "result": f"分析符合預算的區域時發生錯誤: {str(e)}",
                "query_type": QueryType.AREA_SEARCH.value,
                "model_used": self.model_name,
            }

    @traceable(name="realestate_query_processing")
    def process_query(self, text: str) -> Dict[str, Any]:
        """處理房地產相關查詢的主函數。"""
        logger.info(f"開始處理房地產查詢: '{text}'")

        # 首先解析查詢參數，只調用一次parse_query_to_json
        try:
            parsed_params = parse_query_to_json(self.llm_service, text)
            logger.info(f"查詢參數提取結果: {parsed_params}")
        except Exception as e:
            logger.error(f"解析查詢參數失敗: {str(e)}")
            parsed_params = {}  # 使用空字典作為後備

        # 識別查詢類型，傳入已解析的參數
        query_type = identify_query_type(text, parsed_params, self.llm_service)
        logger.info(f"識別查詢類型: {query_type.value}")

        # 根據類型分發處理
        if query_type == QueryType.AVERAGE_PRICE:
            # 使用已解析的參數處理房價查詢
            direct_result = self.handle_average_price_query(text, parsed_params)
            if direct_result:
                return direct_result
            logger.info("直接處理房價查詢失敗，轉用一般方法")

        elif query_type == QueryType.PLOT:
            # 使用已解析的參數處理製圖查詢
            return self.handle_plot_query(text, parsed_params)

        elif query_type == QueryType.AREA_SEARCH:
            # 使用已解析的參數處理區域搜尋查詢
            direct_result = self.handle_area_search_query(text, parsed_params)
            if direct_result:
                return direct_result
            logger.info("直接處理區域搜尋查詢失敗，轉用一般方法")

        # 一般查詢處理流程（包括其他查詢或降級處理）
        try:
            # 已經解析過參數，直接使用

            # 確定要查詢的城市
            city = parsed_params.get("城市")
            logger.info(f"識別的城市: {city}")

            # 如果沒有識別到城市，使用默認值
            if not city:
                city = "台北市"
                logger.info(f"未識別到城市，使用默認值: {city}")

            # 載入數據
            df = self.data_loader.load_city_data(city)
            logger.info(f"數據載入完成，數據框形狀: {df.shape}")

            # 檢查數據中是否包含所需的區域
            district = parsed_params.get("鄉鎮市區")
            if district:
                district_exists = district in df["鄉鎮市區"].unique()
                logger.info(
                    f"查詢區域 '{district}' 是否存在於數據集: {district_exists}"
                )

            # 構建簡化問題
            concise_question = text  # 如果無法獲取簡化問題，則使用原始文本

            # 使用分析器執行查詢
            result = self.analyzer.execute_pandas_agent_query(
                df, concise_question, self.llm_service.llm
            )

            # 返回結果
            return {
                "success": True,
                "message": "成功處理房地產數據查詢",
                "original_text": text,
                "concise_question": concise_question,
                "query_params": parsed_params,
                "result": result.get("result"),
                "query_type": query_type.value,
                "model_used": self.model_name,
            }

        except Exception as e:
            logger.error(f"處理房地產查詢時出錯: {e}")
            logger.debug(f"錯誤堆疊: {traceback.format_exc()}")
            return {}
