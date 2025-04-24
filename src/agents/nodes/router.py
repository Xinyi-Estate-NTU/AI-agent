# agents/nodes/router.py
import logging
from typing import Dict, Any, List, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for tool keywords
DATA_ANALYSIS_KEYWORDS = [
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

WEB_SEARCH_KEYWORDS = [
    "搜尋",
    "找",
    "物件",
    "房屋",
    "公寓",
    "大樓",
    "套房",
    "別墅",
    "透天",
    "辦公",
    "車位",
    "台北",
    "新北",
    "捷運",
    "學區",
    "近",
    "信義房屋",
    "網站",
    "有沒有",
    "網路",
    "查詢",
    "找到",
]

# System prompt for router
ROUTER_SYSTEM_PROMPT = """You are an intelligent query router for a real estate assistant system. 
Your task is to analyze the user's query and determine which tools to use.

Available tools:
1. data_analysis - For analyzing real estate price data, generating charts, and answering questions about price trends
2. web_search - For searching real estate listings, finding properties, and retrieving property information from websites

Analyze the query and return a JSON with the following fields:
1. "tools_to_use": Array of tool names to use (from the available tools list above)
2. "reasoning": Brief explanation of why you chose these tools
3. "query_type": One of ["data_analysis", "web_search", "both", "general"]

Examples:
- "台北市大安區的平均房價是多少?" → data_analysis
- "幫我找新北市3房2廳有車位的房子" → web_search
- "台北市松山區最近五年的房價趨勢，並幫我找有近捷運站的物件" → both

Consider the query carefully and return the most appropriate tool(s) for handling it.
"""


async def router(state):
    """
    Route the user query to the appropriate tools based on content analysis.
    This is the entrypoint of the graph that decides which tools to use.
    """
    query = state["user_input"]
    logger.info(f"Routing query: '{query}'")

    try:
        # Initialize LLM
        llm = ChatGroq(
            model_name=state.get("model_name", "llama3-8b-8192"), temperature=0
        )

        # First attempt: Use heuristics for faster routing
        tools_to_use = _route_with_heuristics(query)

        # If heuristics are inconclusive, use LLM for more accurate classification
        if not tools_to_use:
            tools_to_use, reasoning, query_type = await _route_with_llm(query, llm)
        else:
            # Set default reasoning based on heuristic match
            reasoning = "Based on keywords in the query"
            query_type = (
                "data_analysis" if "data_analysis" in tools_to_use else "web_search"
            )
            if len(tools_to_use) > 1:
                query_type = "both"

        logger.info(f"Decided to use tools: {tools_to_use}, query type: {query_type}")

        # Add classification data to state for use by downstream nodes
        return {
            "tools_to_use": tools_to_use,
            "classification": {"query_type": query_type, "reasoning": reasoning},
        }

    except Exception as e:
        logger.error(f"Error in router: {str(e)}")
        # On error, use both tools to be safe
        return {
            "tools_to_use": ["data_analysis", "web_search"],
            "classification": {
                "query_type": "both",
                "reasoning": f"Error in routing, using both tools: {str(e)}",
            },
        }


def _route_with_heuristics(query: str) -> List[str]:
    """
    Use keyword-based heuristics to route queries quickly.

    Args:
        query: User's query text

    Returns:
        List of tool names to use
    """
    tools_to_use = []

    # Check for data analysis keywords
    if any(keyword in query for keyword in DATA_ANALYSIS_KEYWORDS):
        tools_to_use.append("data_analysis")

    # Check for web search keywords
    if any(keyword in query for keyword in WEB_SEARCH_KEYWORDS):
        tools_to_use.append("web_search")

    # City/district mentions are a strong signal for both tools
    city_district_pattern = r"(台北市|臺北市|新北市|大安區|信義區|中正區|松山區|大同區|萬華區|文山區|南港區|內湖區|士林區|北投區|板橋區|三重區|中和區|永和區|新莊區|新店區|土城區|蘆洲區|汐止區|樹林區|淡水區)"
    if re.search(city_district_pattern, query):
        # If specific web search phrases are present, prioritize web search
        web_specific = ["找", "物件", "房屋", "公寓", "查詢"]
        if any(word in query for word in web_specific):
            if "web_search" not in tools_to_use:
                tools_to_use.append("web_search")
        # If specific data analysis phrases are present, add data analysis
        data_specific = ["房價", "價格", "行情", "均價", "圖表", "趨勢"]
        if any(word in query for word in data_specific):
            if "data_analysis" not in tools_to_use:
                tools_to_use.append("data_analysis")

    # If no specific heuristics matched, let the LLM decide
    return tools_to_use


async def _route_with_llm(query: str, llm) -> tuple:
    """
    Use LLM to determine which tools to use for more accurate routing.

    Args:
        query: User's query text
        llm: Language model to use

    Returns:
        Tuple of (tools_to_use, reasoning, query_type)
    """
    logger.info("Using LLM for query routing")

    prompt = ChatPromptTemplate.from_messages(
        [("system", ROUTER_SYSTEM_PROMPT), ("human", query)]
    )

    # Call LLM to analyze and route the query
    response = await llm.ainvoke(prompt.format_messages())

    # Extract JSON from response
    try:
        import json
        import re

        # Look for JSON pattern
        json_pattern = r"```json\s*([\s\S]*?)\s*```"
        json_match = re.search(json_pattern, response.content)

        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without code block
            json_str = re.search(r"{[\s\S]*}", response.content).group(0)

        result = json.loads(json_str)

        tools_to_use = result.get("tools_to_use", [])
        reasoning = result.get("reasoning", "No reasoning provided")
        query_type = result.get("query_type", "general")

        # Validate and fix tools list if needed
        if not tools_to_use:
            tools_to_use = ["data_analysis", "web_search"]

        return tools_to_use, reasoning, query_type

    except Exception as e:
        logger.error(f"Error parsing LLM routing response: {str(e)}")
        logger.debug(f"Raw LLM response: {response.content}")

        # Default to both tools on error
        return (
            ["data_analysis", "web_search"],
            f"Error parsing response: {str(e)}",
            "both",
        )
