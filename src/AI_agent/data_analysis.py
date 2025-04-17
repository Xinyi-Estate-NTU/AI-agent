"""房地產數據分析和視覺化功能。"""

import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Optional, Tuple
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType

from .config import logger
logger = logging.getLogger(__name__)
class RealEstateAnalyzer:
    """房地產數據分析器，提供各種數據分析和視覺化功能。"""
    
    @staticmethod
    def calculate_average_price(df: pd.DataFrame, district: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """計算平均房價，增強版添加更多統計指標。"""
        logger.info(f"計算平均房價，行政區: {district if district else '全部'}, 額外過濾: {filters}")
        
        # 如果有指定行政區，則過濾該區域數據
        if district and district in df['鄉鎮市區'].values:
            logger.info(f"過濾 {district} 數據")
            df = df[df['鄉鎮市區'] == district]
        
        # 應用其他過濾條件
        if filters and isinstance(filters, dict):
            df = RealEstateAnalyzer.filter_data_by_attributes(df, filters)
        
        # 如果過濾後有足夠的數據
        if len(df) > 0:
            # 基本統計
            avg_price_per_ping = df['每坪單價'].mean()
            avg_total_price = df['總價元'].mean()
            avg_size_ping = df['建物移轉總坪數'].mean()
            count = len(df)
            
            # 增加更多統計指標
            stats = {
                "median": df['每坪單價'].median(),
                "min": df['每坪單價'].min(),
                "max": df['每坪單價'].max(),
                "std": df['每坪單價'].std(),
                "avg_total_price": avg_total_price,   # 平均總價
                "avg_size_ping": avg_size_ping        # 平均坪數
            }
            
            # 計算各區域平均價格
            district_avg = None
            if district is None and count > 10:
                try:
                    district_avg = df.groupby('鄉鎮市區')['每坪單價'].mean().reset_index()
                    district_avg = district_avg.sort_values('每坪單價', ascending=False)
                    district_avg.columns = ['行政區', '平均每坪價格']
                    district_avg['平均每坪價格'] = district_avg['平均每坪價格'].round(2)
                except Exception as e:
                    logger.warning(f"計算區域平均失敗: {e}")
            
            return {
                "avg_price": avg_price_per_ping,
                "avg_total_price": avg_total_price,
                "avg_size_ping": avg_size_ping,
                "count": count,
                "district": district,
                "filters": filters,
                "dataframe": district_avg,
                "stats": stats  # 新增統計資訊
            }
        
        # 數據集為空的情況
        return {
            "avg_price": None,
            "avg_total_price": None,
            "avg_size_ping": None,
            "count": 0,
            "district": district,
            "filters": filters,
            "dataframe": None,
            "error": "找不到相關數據"
        }
    
    @staticmethod
    def _format_conditions(conditions_dict: Dict[str, Any]) -> str:
        """將條件字典轉換為人類可讀的文本。"""
        conditions = []
        
        # 處理行政區
        district = conditions_dict.get("district")
        if district:
            conditions.append(district)
        
        # 處理過濾條件
        filters = conditions_dict.get("filters", {})
        if filters:
            # 時間範圍
            if '時間範圍' in filters and isinstance(filters['時間範圍'], dict):
                conditions.append(filters['時間範圍'].get('description', ''))
            
            # 房屋屬性
            attr_mapping = {
                '建物現況格局-房': lambda v: f"{v}房",
                '建物現況格局-廳': lambda v: f"{v}廳",
                '建物現況格局-衛': lambda v: f"{v}衛",
                '電梯': lambda v: f"{'有' if v == '有' else '無'}電梯",
                '屋齡': lambda v: f"{v}年屋齡" if isinstance(v, (int, float)) else 
                                 f"{v['min']}-{v['max']}年屋齡" if isinstance(v, dict) and 'min' in v and 'max' in v else None
            }
            
            for attr, formatter in attr_mapping.items():
                if attr in filters and filters[attr] is not None and filters[attr] != '':
                    formatted_value = formatter(filters[attr])
                    if formatted_value:
                        conditions.append(formatted_value)
        
        return "、".join(conditions) if conditions else ""

    @staticmethod
    def format_price_result(result: Dict[str, Any], city: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """格式化房價分析結果為可讀性佳的輸出，增強版輸出更多統計數據。"""
        # 組織條件信息
        conditions_dict = {
            "district": result.get("district"),
            "filters": filters or result.get("filters", {})
        }
        
        # 使用輔助方法格式化條件
        condition_text = RealEstateAnalyzer._format_conditions(conditions_dict)
        
        if result.get("avg_price") is None:
            return {
                "success": False,
                "message": f"找不到 {city}{condition_text} 的數據或數據為空",
                "result": f"抱歉，找不到 {city}{condition_text} 的房價數據。",
                "dataframe": None
            }
        
        avg_price = result["avg_price"]
        avg_total_price = result.get("avg_total_price", 0)
        avg_size_ping = result.get("avg_size_ping", 0)
        count = result["count"]
        
        # 獲取更多統計資訊（如果有的話）
        stats = {}
        if "stats" in result and isinstance(result["stats"], dict):
            stats = result["stats"]
        
        # 格式化價格（轉換為萬元）
        avg_price_wan = round(avg_price / 10000, 1)  # 四捨五入到小數點後一位
        avg_price_ping_formatted = f"{avg_price_wan} 萬元"
        
        avg_total_price_wan = round(avg_total_price / 10000)
        avg_total_price_formatted = f"{avg_total_price_wan:,} 萬元"
        
        # 格式化坪數（四捨五入到小數點第一位）
        avg_size_formatted = f"{avg_size_ping:.1f} 坪"
        
        # 格式化數據筆數，添加千分位逗號
        count_formatted = f"{count:,}"
        
        # 構建更豐富的結果文本 (Markdown 格式)
        formatted_result = f"基於 {count_formatted} 筆交易記錄，{city}{condition_text} 的平均房價數據如下：\n"
        formatted_result += f"- 每坪平均價格: {avg_price_ping_formatted}\n"
        formatted_result += f"- 平均房屋總價: {avg_total_price_formatted}\n"
        formatted_result += f"- 平均房屋大小: {avg_size_formatted}"
        
        # 添加額外統計信息（如果有）
        if stats and "median" in stats:
            median_wan = round(stats['median'] / 10000, 1)  # 轉換為萬元並四捨五入到小數點後一位
            median_formatted = f"{median_wan} 萬元"
            formatted_result += f"\n- 中位數每坪房價: {median_formatted}"
        
        # 注意：已移除價格範圍信息
        
        return {
            "success": True,
            "message": "成功處理房地產數據查詢",
            "result": formatted_result,
            "dataframe": result.get("dataframe"),
            "stats": stats,  # 包含原始統計數據，方便前端使用
            "avg_price_ping": avg_price,
            "avg_total_price": avg_total_price,
            "avg_size_ping": avg_size_ping
        }
    
    @staticmethod
    def execute_pandas_agent_query(df: pd.DataFrame, query_text: str, llm, generate_plot: bool = False) -> Dict[str, Any]:
        """使用 Pandas Agent 執行數據查詢，並可選擇性地生成圖表。修復版本。"""
        logger.info(f"使用Pandas Agent執行查詢: '{query_text}'")
        
        try:
            # 確保DataFrame不為空
            if df.empty:
                return {
                    "success": False,
                    "error": "數據為空，無法進行分析",
                    "result": "抱歉，無法分析空數據集。"
                }
            
            # 檢查數據量
            if len(df) > 50000:  # 降低樣本量以提高效率
                logger.info(f"數據量過大 ({len(df)}筆)，抽樣進行分析")
                df = df.sample(50000, random_state=42)
            
            # 建立Pandas DataFrame Agent
            pandas_agent = create_pandas_dataframe_agent(
                llm,
                df,
                verbose=True,
                agent_type=AgentType.OPENAI_FUNCTIONS,
                allow_dangerous_code=True
            )
            
            # 設置超時
            import time
            start_time = time.time()
            max_time = 60  # 最多60秒
            
            # 如果需要生成圖表，使用更明確的指示
            if generate_plot:
                modified_query = (
                    "請針對以下問題分析數據並生成圖表："
                    f"{query_text}\n"
                    "請務必提供詳細的分析結果和解釋。"
                )
            else:
                modified_query = query_text
            
            # 執行查詢
            logger.info(f"發送查詢給Agent: '{modified_query}'")
            
            try:
                agent_response = pandas_agent.invoke({"input": modified_query})
                result = agent_response.get("output", "")
            except Exception as agent_error:
                logger.warning(f"Agent執行出錯: {agent_error}，嘗試使用簡化查詢")
                # 嘗試使用簡化查詢
                try:
                    simple_query = f"分析{query_text}並提供簡短結論"
                    agent_response = pandas_agent.invoke({"input": simple_query})
                    result = agent_response.get("output", "")
                except:
                    result = ""
            
            # 獲取結果
            logger.info(f"Agent回應結果長度: {len(result) if result else 0}")
            
            # 處理空結果情況
            if not result or len(result.strip()) < 10:  # 結果太短不可用
                # 生成基本統計信息作為替代
                basic_stats = df['每坪單價'].describe().to_dict()
                stats_text = (
                    f"數據基本統計：\n"
                    f"均價: {basic_stats['mean']:,.2f} 元/坪\n"
                    f"最低價: {basic_stats['min']:,.2f} 元/坪\n"
                    f"最高價: {basic_stats['max']:,.2f} 元/坪\n"
                    f"數據筆數: {len(df)}"
                )
                
                if generate_plot:
                    result = f"無法自動生成詳細分析圖表，但這裡是基本統計信息：\n\n{stats_text}"
                else:
                    result = f"無法生成詳細分析，但這裡是基本統計信息：\n\n{stats_text}"
            
            return {
                "success": True,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"執行Pandas Agent查詢時出錯: {e}")
            import traceback
            logger.debug(f"錯誤堆疊: {traceback.format_exc()}")
            
            return {
                "success": False,
                "error": str(e),
                "result": f"數據分析過程中發生錯誤: {str(e)}"
            }
    
    @staticmethod
    def get_district_price_ranking(df: pd.DataFrame, city: str = None, top_n: int = 10) -> Dict[str, Any]:
        """獲取行政區平均房價排名。"""
        logger.info(f"獲取行政區房價排名，城市: {city if city else '全部'}")
        
        try:
            # 如果指定了城市，先過濾數據
            if city and '縣市' in df.columns:
                df = df[df['縣市'] == city]
            
            # 計算各區域平均價格
            district_avg = df.groupby('鄉鎮市區')['每坪單價'].agg(['mean', 'count']).reset_index()
            district_avg.columns = ['行政區', '平均每坪價格', '交易數量']
            district_avg = district_avg.sort_values('平均每坪價格', ascending=False)
            district_avg['平均每坪價格'] = district_avg['平均每坪價格'].round(2)
            
            # 取前N名
            top_districts = district_avg.head(top_n)
            
            # 格式化結果
            result_text = f"{'全台灣' if not city else city}各行政區平均房價排名 (前{top_n}名):\n\n"
            for i, row in top_districts.iterrows():
                result_text += f"{i+1}. {row['行政區']}: {row['平均每坪價格']:,.2f} 元/坪 (共{row['交易數量']}筆交易)\n"
            
            return {
                "success": True,
                "result": result_text,
                "dataframe": top_districts
            }
            
        except Exception as e:
            logger.error(f"計算行政區房價排名時出錯: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": f"計算房價排名時發生錯誤: {str(e)}"
            }

    @staticmethod
    def generate_price_trend_chart(df: pd.DataFrame, city: str = None, district: str = None) -> Dict[str, Any]:
        """生成房價趨勢圖表和分析。"""
        logger.info(f"開始生成房價趨勢圖，城市: {city}, 區域: {district}")
        print(f"[DEBUG] 開始生成房價趨勢圖，城市: {city}, 區域: {district}")
        
        try:
            # 確保有交易年月日欄位
            if '交易年月日' not in df.columns:
                print(f"[DEBUG] 數據缺少必要的交易年月日欄位")
                return {
                    "success": False,
                    "error": "數據缺少必要的交易年月日欄位",
                    "result": "無法生成趨勢圖：數據格式不正確"
                }
            
            print(f"[DEBUG] 資料欄位檢查通過，開始過濾數據")
            # 處理區域過濾
            area_text = f"{city}"
            if district:
                df = df[df['鄉鎮市區'] == district].copy()
                area_text = f"{city}{district}"
                if len(df) == 0:
                    print(f"[DEBUG] 找不到 {district} 的資料")
                    return {
                        "success": False,
                        "error": f"找不到 {district} 的資料",
                        "result": f"找不到 {area_text} 的房價資料。"
                    }
            
            print(f"[DEBUG] 過濾後數據量: {len(df)}")
            
            # 轉換日期並依年月分組計算平均
            df['交易年月'] = pd.to_datetime(df['交易年月日']).dt.strftime('%Y-%m')
            monthly_avg = df.groupby('交易年月')['每坪單價'].agg(['mean', 'count']).reset_index()
            monthly_avg = monthly_avg.sort_values('交易年月')
            monthly_avg.columns = ['交易年月', '平均每坪單價', '交易數量']
            monthly_avg['交易年月'] = pd.to_datetime(monthly_avg['交易年月'])

            print(f"[DEBUG] 分組後數據點數量: {len(monthly_avg)}")
            
            # 確保有足夠的資料點
            if len(monthly_avg) < 2:
                print(f"[DEBUG] 資料點不足以產生趨勢")
                return {
                    "success": False,
                    "error": "資料點不足以產生趨勢",
                    "result": f"{area_text}的資料點不足以分析趨勢。",
                    "dataframe": monthly_avg
                }
            
            # 分析趨勢
            first_price = monthly_avg['平均每坪單價'].iloc[0]
            last_price = monthly_avg['平均每坪單價'].iloc[-1]
            price_change = ((last_price - first_price) / first_price) * 100
            trend_desc = "上升" if price_change > 0 else "下降"
            
            # 找出最高點和最低點
            max_idx = monthly_avg['平均每坪單價'].idxmax()
            min_idx = monthly_avg['平均每坪單價'].idxmin()
            max_period = monthly_avg.loc[max_idx, '交易年月']
            min_period = monthly_avg.loc[min_idx, '交易年月']
            max_price = monthly_avg.loc[max_idx, '平均每坪單價']
            min_price = monthly_avg.loc[min_idx, '平均每坪單價']
            
            print(f"[DEBUG] 趨勢分析完成，趨勢方向: {trend_desc}, 變化幅度: {abs(price_change):.2f}%")
            
            # 生成結果描述
            result = (
                f"{area_text}的房價從 {monthly_avg['交易年月'].iloc[0]} 到 {monthly_avg['交易年月'].iloc[-1]} "
                f"整體呈{trend_desc}趨勢，變化幅度約 {abs(price_change):.2f}%。\n\n"
                f"起始平均每坪單價: {first_price:,.2f} 元\n"
                f"最終平均每坪單價: {last_price:,.2f} 元\n\n"
                f"期間最高點出現在 {max_period}，價格為 {max_price:,.2f} 元/坪\n"
                f"期間最低點出現在 {min_period}，價格為 {min_price:,.2f} 元/坪"
            )
            
            # 創建圖表
            try:
                print(f"[DEBUG] 開始生成圖表")
                # 設置中文字體支援
                plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Microsoft YaHei', 'SimHei', 'sans-serif']
                plt.rcParams['axes.unicode_minus'] = False
                
                # 創建圖表
                fig, ax = plt.subplots(figsize=(12, 6))
                
                # 繪製價格趨勢線
                ax.plot(monthly_avg['交易年月'], monthly_avg['平均每坪單價'], marker='o', linestyle='-', color='#3498db', linewidth=2)
                
                # 標記最高點和最低點
                ax.scatter(max_period, max_price, color='red', s=100, zorder=5, label=f'最高點: {max_price:,.0f}元/坪')
                ax.scatter(min_period, min_price, color='green', s=100, zorder=5, label=f'最低點: {min_price:,.0f}元/坪')
                
                print(f"[DEBUG] 繪製圖表主體完成")
                
                # 設置標題和軸標籤
                ax.set_title(f'{area_text}房價趨勢圖', fontsize=16)
                ax.set_xlabel('交易年月', fontsize=12)
                ax.set_ylabel('平均每坪單價 (元)', fontsize=12)
                
                # 格式化y軸為千分位
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x):,}'))
                
                # 設置x軸刻度，間隔顯示避免擁擠
                total_months = len(monthly_avg)
                if total_months > 12:
                    step = total_months // 12 + 1
                    ax.set_xticks(monthly_avg['交易年月'][::step])
                    ax.set_xticklabels(monthly_avg['交易年月'][::step], rotation=45)
                else:
                    ax.set_xticks(monthly_avg['交易年月'])
                    ax.set_xticklabels(monthly_avg['交易年月'], rotation=45)
                
                # 添加網格線
                ax.grid(True, linestyle='--', alpha=0.7)
                
                # 添加圖例
                ax.legend()
                
                # 調整布局
                plt.tight_layout()
                
                print(f"[DEBUG] 圖表格式設置完成，準備保存")
                
                # 直接保存圖像到字節流
                import io
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=100)
                buf.seek(0)
                
                print(f"[DEBUG] 圖表已保存到BytesIO對象，大小: {len(buf.getvalue())} 字節")
                
                # 關閉圖表以釋放資源
                plt.close(fig)
                
                result_dict = {
                    "success": True,
                    "result": result,
                    "dataframe": monthly_avg,
                    "trend_direction": trend_desc,
                    "price_change_percent": price_change,
                    "chart_image": buf,  # 直接傳遞BytesIO對象
                    "has_chart": True
                }
                
                print(f"[DEBUG] 返回結果字典，包含圖表: has_chart={result_dict['has_chart']}")
                logger.info(f"房價趨勢圖生成成功，包含圖表: has_chart={result_dict['has_chart']}")
                
                return result_dict
                
            except Exception as chart_error:
                logger.error(f"生成圖表時出錯: {chart_error}")
                print(f"[DEBUG-ERROR] 生成圖表時出錯: {chart_error}")
                import traceback
                print(f"[DEBUG-ERROR] 圖表錯誤堆疊: {traceback.format_exc()}")
                
                # 即使圖表生成失敗也返回數據分析結果
                return {
                    "success": True,
                    "result": result + "\n\n(圖表生成失敗，僅顯示數據分析結果)",
                    "dataframe": monthly_avg,
                    "trend_direction": trend_desc,
                    "price_change_percent": price_change,
                    "chart_error": str(chart_error),
                    "has_chart": False
                }
                
        except Exception as e:
            logger.error(f"生成房價趨勢圖出錯: {e}")
            print(f"[DEBUG-ERROR] 生成房價趨勢圖出錯: {e}")
            import traceback
            trace = traceback.format_exc()
            logger.debug(f"錯誤堆疊: {trace}")
            print(f"[DEBUG-ERROR] 錯誤堆疊: {trace}")
            
            return {
                "success": False,
                "error": str(e),
                "result": f"生成房價趨勢圖時發生錯誤: {str(e)}",
                "has_chart": False
            }

    @staticmethod
    def filter_data_by_attributes(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """根據篩選條件過濾數據框，增強版支持更多過濾邏輯和性能優化。"""
        # 不立即複製整個DF，使用過濾條件表達式
        filter_conditions = []
        logger.info(f"原始數據量: {len(df)}")
        
        for attr, value in filters.items():
            # 修改跳過條件檢查
            if value is None or value == '' or (isinstance(value, str) and value.strip() == ""):
                logger.info(f"跳過空值欄位: {attr}")
                continue
            
            # 處理時間範圍特殊邏輯，支持年份和年月
            if attr == '時間範圍' and isinstance(value, dict):
                logger.info(f"應用時間範圍過濾: {value}")
                
                # 年度過濾
                if '交易年度' in df.columns:
                    start_year = value.get('start_year')
                    end_year = value.get('end_year')
                    
                    if start_year and end_year:
                        year_filter = (df['交易年度'] >= start_year) & (df['交易年度'] <= end_year)
                        filter_conditions.append(year_filter)
                        logger.info(f"添加年度過濾條件: {start_year}-{end_year}")
                
                # 時間精確到月份的過濾可以加在這裡
                # 如果有 '交易年月' 或類似欄位        
                continue
            
            # 處理屋齡範圍 - 特別處理
            if attr == '屋齡' and isinstance(value, dict):
                min_age = value.get('min')
                max_age = value.get('max')
                
                if '屋齡' in df.columns:
                    if min_age is not None:
                        filter_conditions.append(df['屋齡'] >= min_age)
                    if max_age is not None:
                        filter_conditions.append(df['屋齡'] <= max_age)
                continue
            
            # 其他屬性處理
            if attr in df.columns:
                if isinstance(value, dict) and ('min' in value or 'max' in value):
                    # 範圍過濾
                    if 'min' in value and value['min'] is not None:
                        filter_conditions.append(df[attr] >= value['min'])
                    if 'max' in value and value['max'] is not None:
                        filter_conditions.append(df[attr] <= value['max'])
                elif isinstance(value, list):
                    # 多選過濾
                    if value:  # 非空列表
                        filter_conditions.append(df[attr].isin(value))
                else:
                    # 精確匹配，處理數值和字符串類型自動轉換
                    try:
                        if attr in ['建物現況格局-房', '建物現況格局-廳', '建物現況格局-衛'] and isinstance(value, str):
                            # 嘗試將字符串轉換為數字
                            value = int(value)
                        filter_conditions.append(df[attr] == value)
                    except (ValueError, TypeError):
                        # 如果轉換失敗，使用原始值
                        filter_conditions.append(df[attr] == value)
        
        # 應用所有過濾條件
        if filter_conditions:
            # 組合所有條件（AND邏輯）
            final_filter = filter_conditions[0]
            for condition in filter_conditions[1:]:
                final_filter = final_filter & condition
            
            filtered_df = df[final_filter]
            logger.info(f"應用 {len(filter_conditions)} 個過濾條件後數據量: {len(filtered_df)}")
            return filtered_df
        else:
            logger.info("未應用過濾條件，返回原始數據")
            return df
