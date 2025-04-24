# agents/nodes/data_tools.py
import logging
from typing import Dict, Any, List, Optional

# Import tools
from ..tools import (
    load_city_data,
    calculate_average_price,
    format_price_result,
    generate_price_trend_chart,
    execute_pandas_agent_query,
    filter_data_by_attributes,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for query classification
AVERAGE_PRICE_KEYWORDS = [
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


def data_analysis_node(state):
    """LangGraph node for data analysis tasks."""
    # Extract relevant information from state
    query = state["user_input"]
    query_type = state.get("query_type", "")
    classification = state.get("classification", {})
    data_requested = "data_analysis" in state.get("tools_to_use", [])

    # Skip if data analysis not requested
    if not data_requested:
        return {"data_result": None}

    logger.info(f"Processing data analysis query: {query}")

    # Extract parameters from classification
    city = classification.get("city")
    district = classification.get("district")
    time_range = classification.get("time_range")
    filters = classification.get("filters", {})

    # Load relevant data
    try:
        df = load_city_data(city)

        # If dataframe is empty or None
        if df is None or df.empty:
            return {
                "data_result": {
                    "success": False,
                    "message": f"Could not load data for {city if city else 'requested location'}",
                    "result": f"Sorry, I couldn't find real estate data for {city if city else 'the requested location'}.",
                }
            }

        # Determine query type based on keywords if not specified
        if not query_type:
            if any(keyword in query.lower() for keyword in PLOT_KEYWORDS):
                query_type = "plot"
            elif any(keyword in query.lower() for keyword in AVERAGE_PRICE_KEYWORDS):
                query_type = "average_price"
            else:
                query_type = "general"

        # Process based on query type
        if query_type == "plot" or "plot" in query.lower():
            # Generate chart
            chart_type = "trend"  # Default chart type
            if "bar" in query.lower() or "column" in query.lower():
                chart_type = "bar"

            result = generate_price_trend_chart(
                df, city, district, chart_type, time_range
            )

        elif query_type == "average_price":
            # Calculate average prices
            calc_result = calculate_average_price(df, district, filters)
            result = format_price_result(calc_result, city, filters)

        else:
            # General data analysis using pandas agent
            # In a real implementation, we'd use the LLM agent here
            result = {
                "success": True,
                "result": f"Analysis for {city} {district if district else ''} data. Please specify what analysis you're looking for (prices, trends, etc.)",
                "dataframe": None,
            }

        logger.info(
            f"Data analysis completed successfully, result type: {result.get('success')}"
        )
        return {"data_result": result}

    except Exception as e:
        logger.error(f"Error in data analysis: {str(e)}")
        return {
            "data_result": {
                "success": False,
                "message": f"Error processing data: {str(e)}",
                "result": f"Sorry, an error occurred during data analysis: {str(e)}",
            }
        }


def parse_query_parameters(state):
    """LangGraph node to parse query parameters using LLM."""
    query = state["user_input"]
    llm = state.get("llm")

    # Simple keyword-based parsing as a fallback without LLM
    parsed = {}

    # City detection (simplified)
    if "台北" in query or "臺北" in query:
        parsed["city"] = "臺北市"
    elif "新北" in query:
        parsed["city"] = "新北市"

    # District detection would normally use pattern matching or LLM

    # Time range detection (simplified)
    if "今年" in query:
        parsed["time_range"] = {
            "start_year": 2025,
            "end_year": 2025,
            "description": "2025年(今年)",
        }
    elif "去年" in query:
        parsed["time_range"] = {
            "start_year": 2024,
            "end_year": 2024,
            "description": "2024年(去年)",
        }
    elif "近五年" in query or "最近五年" in query:
        parsed["time_range"] = {
            "start_year": 2021,
            "end_year": 2025,
            "description": "近五年(2021-2025)",
        }

    # In real implementation, we'd use the LLM to extract more parameters

    return {"classification": parsed}
