"""房地產數據分析和視覺化功能。"""

import logging
import pandas as pd
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
    def generate_price_trend_chart(df: pd.DataFrame, city: str = None, district: str = None, 
                                   chart_type: str = "trend", time_range: dict = None) -> Dict[str, Any]:
        """生成房價趨勢圖表和分析。
        
        Args:
            df: 房價數據框
            city: 城市名稱
            district: 區域名稱
            chart_type: 圖表類型，預設為"trend"（趨勢圖）
            time_range: 時間範圍，格式為 {'start_year': int, 'end_year': int, 'description': str}
        
        Returns:
            包含分析結果和圖表的字典
        """
        logger.info(f"開始生成房價趨勢圖，城市: {city}, 區域: {district}, 圖表類型: {chart_type}")
        
        try:
            # 確保有交易年月日欄位
            if '交易年月日' not in df.columns:
                return {
                    "success": False,
                    "error": "數據缺少必要的交易年月日欄位",
                    "result": "無法生成趨勢圖：數據格式不正確"
                }
            
            # 處理區域過濾
            area_text = f"{city}"
            if district:
                df = df[df['鄉鎮市區'] == district].copy()
                area_text = f"{city}{district}"
                if len(df) == 0:
                    return {
                        "success": False,
                        "error": f"找不到 {district} 的資料",
                        "result": f"找不到 {area_text} 的房價資料。"
                    }
            
            # 創建一個數據副本以防止修改原始數據
            analysis_df = df.copy()
            
            # 1. 清理缺失值：先過濾掉交易年月日為空的記錄
            analysis_df = analysis_df.dropna(subset=['交易年月日'])
            
            # 2. 將交易日期轉換為日期格式
            analysis_df['交易日期'] = pd.to_datetime(analysis_df['交易年月日'], errors='coerce')
            
            # 3. 過濾掉轉換失敗（產生NaT）的記錄
            analysis_df = analysis_df.dropna(subset=['交易日期'])
            
            # 4. 使用pandas datetime屬性提取年份和月份（更穩健且符合最佳實踐）
            analysis_df['年份'] = analysis_df['交易日期'].dt.year
            analysis_df['月份'] = analysis_df['交易日期'].dt.month
            
            # 5. 根據時間範圍過濾數據
            time_range_text = ""
            if time_range and isinstance(time_range, dict):
                start_year = time_range.get('start_year')
                end_year = time_range.get('end_year')
                
                if start_year:
                    analysis_df = analysis_df[analysis_df['年份'] >= start_year]
                    
                if end_year:
                    analysis_df = analysis_df[analysis_df['年份'] <= end_year]
                    
                # 使用提供的描述或自動生成
                if 'description' in time_range and time_range['description']:
                    time_range_text = time_range['description']
                elif start_year and end_year:
                    if start_year == end_year:
                        time_range_text = f"{start_year}年"
                    else:
                        time_range_text = f"{start_year}年至{end_year}年"
            
            if len(analysis_df) == 0:
                return {
                    "success": False,
                    "error": "指定時間範圍內無資料",
                    "result": f"找不到 {area_text} {time_range_text} 的房價資料。"
                }
            
            # 6. 檢查數據年份範圍（使用安全的方法獲取最小最大值）
            years = sorted(analysis_df['年份'].unique())
            logger.info(f"數據年份範圍: {years[0]}-{years[-1]}, 共 {len(years)} 年")
            
            # 7. 判斷是否為單一年份
            is_single_year = len(years) == 1
            
            # 8. 根據年份範圍決定分組方式，使用更穩健的方法
            if is_single_year:
                # 單一年度：按月份分組
                logger.info(f"單一年度數據 ({years[0]}), 按月份分組")
                
                # 使用agg()進行分組彙總，更加清晰和彈性
                time_grouped = analysis_df.groupby(['年份', '月份']).agg({
                    '每坪單價': 'mean',
                    '交易年月日': 'count'
                }).reset_index()
                
                # 格式化月份標籤
                time_grouped['時間標籤'] = time_grouped['月份'].map(lambda m: f"{int(m)}月")
                time_grouped = time_grouped.sort_values(['年份', '月份'])
                x_label = f"{int(years[0])}年月份"
                
                # 如果時間範圍文字為空，生成
                if not time_range_text:
                    time_range_text = f"{int(years[0])}年各月份"
                
            else:
                # 多年數據：按年份分組
                logger.info(f"多年度數據 ({years[0]}-{years[-1]}), 按年份分組")
                
                # 使用agg()進行分組彙總
                time_grouped = analysis_df.groupby('年份').agg({
                    '每坪單價': 'mean',
                    '交易年月日': 'count'
                }).reset_index()
                
                # 格式化年份標籤
                time_grouped['時間標籤'] = time_grouped['年份'].map(lambda y: f"{int(y)}年")
                time_grouped = time_grouped.sort_values('年份')
                x_label = "年份"
                
                # 如果時間範圍文字為空，生成
                if not time_range_text:
                    time_range_text = f"{int(years[0])}年至{int(years[-1])}年"
            
            # 檢查時間分組後的數據，確保不含NA
            time_grouped = time_grouped.dropna(subset=['每坪單價'])
            
            # 確保有足夠的資料點
            if len(time_grouped) < 2:
                return {
                    "success": False,
                    "error": "資料點不足以產生趨勢",
                    "result": f"{area_text} {time_range_text} 的資料點不足以分析趨勢。",
                    "dataframe": time_grouped
                }
            
            # 9. 分析趨勢，使用更安全的索引方法
            first_price = time_grouped['每坪單價'].iloc[0]
            last_price = time_grouped['每坪單價'].iloc[-1]
            price_change = ((last_price - first_price) / first_price) * 100
            trend_desc = "上升" if price_change > 0 else "下降"
            
            # 找出最高點和最低點
            max_idx = time_grouped['每坪單價'].idxmax()
            min_idx = time_grouped['每坪單價'].idxmin()
            max_period = time_grouped.loc[max_idx, '時間標籤']
            min_period = time_grouped.loc[min_idx, '時間標籤']
            max_price = time_grouped.loc[max_idx, '每坪單價']
            min_price = time_grouped.loc[min_idx, '每坪單價']
            
            # 10. 生成結果描述
            result = (
                f"{area_text}的房價在{time_range_text}"
                f"整體呈{trend_desc}趨勢，變化幅度約 {abs(price_change):.2f}%。\n\n"
                f"起始平均每坪單價: {first_price:,.0f} 元\n"
                f"最終平均每坪單價: {last_price:,.0f} 元\n\n"
                f"期間最高點出現在 {max_period}，價格為 {max_price:,.0f} 元/坪\n"
                f"期間最低點出現在 {min_period}，價格為 {min_price:,.0f} 元/坪"
            )
            
            # 11. 根據圖表類型生成不同圖表，使用matplotlib的最佳實踐
            try:
                # 設置中文字體支援
                plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Microsoft YaHei', 'SimHei', 'sans-serif']
                plt.rcParams['axes.unicode_minus'] = False
                
                # 初始化高質量的圖表，使用constrained_layout改善佈局
                fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True, dpi=100)
                
                # 根據圖表類型繪製圖表
                if chart_type == "trend" or chart_type == "line":
                    # 使用標準化的時間序列繪圖方法
                    ax.plot(range(len(time_grouped)), time_grouped['每坪單價'], 
                            marker='o', linestyle='-', color='#3498db', linewidth=2,
                            label=f"{area_text}房價趨勢")
                    
                    # 標記最高點和最低點
                    max_pos = time_grouped.index.get_loc(max_idx)
                    min_pos = time_grouped.index.get_loc(min_idx)
                    
                    ax.scatter([max_pos], [max_price], color='red', s=100, zorder=5, 
                               label=f'最高點: {max_price:,.0f}元/坪')
                    ax.scatter([min_pos], [min_price], color='green', s=100, zorder=5, 
                               label=f'最低點: {min_price:,.0f}元/坪')
                    
                elif chart_type == "bar":
                    # 使用統一的方法創建柱狀圖
                    bars = ax.bar(range(len(time_grouped)), time_grouped['每坪單價'], 
                                  color='#3498db', alpha=0.7, width=0.7)
                    
                    # 在最高和最低點的柱狀圖上標記
                    bars[time_grouped.index.get_loc(max_idx)].set_color('red')
                    bars[time_grouped.index.get_loc(min_idx)].set_color('green')
                    
                    # 添加數據標籤（使用更簡潔的方法）
                    for i, bar in enumerate(bars):
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height,
                                f'{int(height):,}',
                                ha='center', va='bottom', rotation=0)
                
                # 12. 設置x軸刻度和標籤
                ax.set_xticks(range(len(time_grouped)))
                ax.set_xticklabels(time_grouped['時間標籤'], rotation=45 if len(time_grouped) > 6 else 0)
                
                # 13. 共用的圖表設置，使用matplotlib的最佳實踐
                ax.set_title(f'{area_text}房價趨勢圖 ({time_range_text})', fontsize=16, pad=15)
                ax.set_xlabel(x_label, fontsize=12, labelpad=10)
                ax.set_ylabel('平均每坪單價 (元)', fontsize=12, labelpad=10)
                
                # 格式化y軸為千分位
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x):,}'))
                
                # 添加網格線（使用更現代的樣式）
                ax.grid(True, linestyle='--', alpha=0.6, axis='y')
                
                # 添加圖例（優化位置和樣式）
                if chart_type in ["trend", "line"]:
                    ax.legend(loc='upper left', frameon=True, framealpha=0.9)
                
                # 14. 直接保存圖像到字節流
                import io
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=100)
                buf.seek(0)
                
                # 關閉圖表以釋放資源
                plt.close(fig)
                
                # 15. 創建簡化版的dataframe用於顯示
                # 創建更加清晰美觀的DataFrame用於顯示
                display_cols = ['月份' if is_single_year else '年份', '平均每坪單價', '交易數量']
                
                if is_single_year:
                    display_df = pd.DataFrame({
                        '月份': time_grouped['月份'].apply(lambda x: int(x)),
                        '平均每坪單價': time_grouped['每坪單價'].round(0).astype(int),
                        '交易數量': time_grouped['交易年月日'].astype(int)
                    })
                else:
                    display_df = pd.DataFrame({
                        '年份': time_grouped['年份'].apply(lambda x: int(x)),
                        '平均每坪單價': time_grouped['每坪單價'].round(0).astype(int),
                        '交易數量': time_grouped['交易年月日'].astype(int)
                    })
                
                # 16. 返回完整的結果字典
                result_dict = {
                    "success": True,
                    "result": result,
                    "dataframe": display_df,  # 使用簡化版的 dataframe
                    "trend_direction": trend_desc,
                    "price_change_percent": price_change,
                    "chart_image": buf,  # 直接傳遞BytesIO對象
                    "has_chart": True,
                    "chart_type": chart_type,
                    "time_range": time_range_text
                }
                
                logger.info(f"房價趨勢圖生成成功")
                return result_dict
                
            except Exception as chart_error:
                logger.error(f"生成圖表時出錯: {chart_error}")
                
        except Exception as e:
            logger.error(f"生成房價趨勢圖出錯: {e}")

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
