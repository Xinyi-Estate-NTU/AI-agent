# AI_agent/query_processor.py
import json
import logging
import re
from typing import Optional, Dict, Any
import pandas as pd
import traceback
from langsmith import traceable
from langchain_groq import ChatGroq
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType
import json

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
            temperature=0
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
    
    def handle_price_query(self, text: str, parsed_params=None) -> Dict[str, Any]:
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
                    "result": "抱歉，我無法理解您查詢的城市。請明確指定您想查詢的城市，例如「台北市大安區的平均房價」。"
                }
            
            # 加載城市數據
            df = self.data_loader.load_city_data(city)
            if df is None or df.empty:
                return {
                    "success": False,
                    "message": f"無法加載 {city} 的數據或數據為空",
                    "result": f"抱歉，我找不到 {city} 的房價數據。"
                }
            
            # 提取其他過濾條件
            filters = {}
            if parsed_params.get("時間範圍"):
                filters["時間範圍"] = parsed_params.get("時間範圍")
            
            # 添加房型過濾條件
            for key in ["建物現況格局-房", "建物現況格局-廳", "建物現況格局-衛", "電梯", "屋齡"]:
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
                "result": "抱歉，處理您的查詢時出現了技術問題。請稍後再試或換一種方式提問。"
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
            
            # 使用專用趨勢圖生成方法
            if "趨勢" in query_text or "走勢" in query_text or "變化" in query_text:
                logger.info("檢測到趨勢查詢，使用專用趨勢圖生成方法")
                trend_result = self.analyzer.generate_price_trend_chart(df, city, district)
                
                # 這裡是關鍵修改部分 - 確保將趨勢圖結果直接合併到最終結果中
                if trend_result["success"]:
                    result = {
                        "success": True,
                        "message": "成功生成房價趨勢圖",
                        "original_text": query_text,
                        "result": trend_result["result"],
                        "dataframe": trend_result.get("dataframe"),
                        "query_type": QueryType.PLOT.value,
                        "model_used": self.model_name
                    }
                    
                    # 新增：確保將圖表相關信息添加到結果中
                    if trend_result.get("has_chart", False):
                        result["has_chart"] = True
                        result["chart_image"] = trend_result["chart_image"]
                        result["trend_direction"] = trend_result.get("trend_direction")
                    
                    return result
            
            # 否則嘗試使用 Agent 生成圖表
            logger.info("使用 Pandas Agent 生成圖表")
            agent_result = self.analyzer.execute_pandas_agent_query(
                df, 
                query_text, 
                self.llm_service.llm,
                generate_plot=True
            )
            
            # 如果 Agent 成功生成圖表，返回結果
            if agent_result["success"] and agent_result.get("result"):
                return {
                    "success": True,
                    "message": "成功使用 Agent 處理製圖查詢",
                    "original_text": query_text,
                    "result": agent_result["result"],
                    "query_type": QueryType.PLOT.value,
                    "model_used": self.model_name
                }
            
            # 如果以上方法都失敗，使用備用方法
            logger.info("嘗試使用備用方法生成基本分析")
            fallback_result = self.analyzer.generate_price_trend_chart(df, city, district)
            
            return {
                "success": fallback_result.get("success", False),
                "message": "使用備用方法處理製圖查詢",
                "original_text": query_text,
                "result": fallback_result.get("result", "無法生成有效的圖表和分析。"),
                "dataframe": fallback_result.get("dataframe"),
                "query_type": QueryType.PLOT.value,
                "model_used": self.model_name
            }
            
        except Exception as e:
            logger.error(f"處理製圖查詢時出錯: {e}")
            logger.debug(f"錯誤堆疊: {traceback.format_exc()}")
            return {}
    
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
            direct_result = self.handle_price_query(text, parsed_params)
            if direct_result:
                return direct_result
            logger.info("直接處理房價查詢失敗，轉用一般方法")
        
        elif query_type == QueryType.PLOT:
            # 使用已解析的參數處理製圖查詢
            return self.handle_plot_query(text, parsed_params)
        
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
                district_exists = district in df['鄉鎮市區'].unique()
                logger.info(f"查詢區域 '{district}' 是否存在於數據集: {district_exists}")
            
            # 構建簡化問題
            concise_question = text  # 如果無法獲取簡化問題，則使用原始文本
            
            # 使用分析器執行查詢
            result = self.analyzer.execute_pandas_agent_query(
                df,
                concise_question,
                self.llm_service.llm
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
                "model_used": self.model_name
            }
            
        except Exception as e:
            logger.error(f"處理房地產查詢時出錯: {e}")
            logger.debug(f"錯誤堆疊: {traceback.format_exc()}")
            return {}