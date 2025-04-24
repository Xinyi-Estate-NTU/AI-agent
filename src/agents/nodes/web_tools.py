# agents/nodes/web_tools.py
import logging
import asyncio
import json
import re
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from ..tools import (
    build_url,
    generate_search_explanation,
    map_llm_params_to_internal,
    scrape_property_listings,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default model
DEFAULT_MODEL = "llama3-8b-8192"

# Parameter extraction prompt
PARAM_EXTRACTION_PROMPT = """You are a real estate search URL generator. You need to parse the user's natural language query and extract the following parameters:

1. City (city): e.g., Taipei City, New Taipei City
2. District (district): e.g., Daan District, Xinyi District, Banqiao District, etc.
3. Property type (property_type): Apartment, Building, Studio, Villa, Office
4. Price range (price_range): e.g., "above 2 million", "5-10 million", etc.
5. Area range (area_range): e.g., "above 10 ping", "20-30 ping", etc.
6. Number of rooms (rooms): e.g., "1-2 bedrooms", "3+ bedrooms", etc.
7. Floor (floor): e.g., "above 1st floor", "below 5th floor", etc.
8. Building age (year): e.g., "below 5 years", "above 10 years", etc.
9. Special conditions (special_conditions): e.g., "with parking", "without parking", "excluding 4th floor", etc.
10. Amenities (amenities): e.g., "near MRT", "near park", "with swimming pool", "with gym", etc.
11. Keyword (keyword): e.g., MRT station name, school district name, etc.

Please output in JSON format, only including parameters that are explicitly mentioned in the query. Do not add assumed parameters.
"""


async def web_search_node(state):
    """LangGraph node for web search tasks."""
    # Extract relevant information from state
    query = state["user_input"]
    web_search_requested = "web_search" in state.get("tools_to_use", [])

    # Skip if web search not requested
    if not web_search_requested:
        return {"web_result": None}

    logger.info(f"Processing web search query: {query}")

    try:
        # Initialize LLM for parameter extraction
        llm = ChatGroq(model_name=DEFAULT_MODEL, temperature=0)

        # Extract search parameters from query
        url_result = await parse_query_to_url(query, llm)

        if not url_result.get("success", False):
            return {
                "web_result": {
                    "success": False,
                    "message": "Failed to parse search parameters",
                    "result": f"Sorry, I couldn't understand your real estate search query. Please try being more specific about what you're looking for.",
                }
            }

        # Scrape property listings if URL was generated successfully
        if "url" in url_result:
            property_data = await scrape_property_listings(url_result["url"], llm)

            # Generate response based on scraped data
            if property_data and len(property_data) > 0:
                explanation = url_result.get("explanation", "")
                properties_count = len(property_data)

                # Format a human-readable response
                result_text = f"I found {properties_count} properties matching your search criteria:\n\n"
                result_text += f"{explanation}\n\n"

                # Add summary of top properties
                for i, prop in enumerate(property_data[:3]):  # Show top 3 properties
                    price = f"{prop.get('current_price', 'N/A')} {prop.get('price_unit', '')}"
                    result_text += f"{i+1}. {prop.get('property_name', 'Property')}\n"
                    result_text += f"   Location: {prop.get('location', 'N/A')}\n"
                    result_text += f"   Price: {price}\n"
                    result_text += f"   Size: {prop.get('total_size', 'N/A')}\n"
                    result_text += f"   Layout: {prop.get('layout', 'N/A')}\n"

                    # Add features if available
                    if "features" in prop and prop["features"]:
                        features = [f["feature"] for f in prop["features"]]
                        result_text += f"   Features: {', '.join(features)}\n"

                    result_text += "\n"

                if properties_count > 3:
                    result_text += f"... and {properties_count - 3} more properties\n"

                return {
                    "web_result": {
                        "success": True,
                        "message": "Successfully retrieved property listings",
                        "result": result_text,
                        "properties_count": properties_count,
                        "properties": property_data,
                        "url": url_result["url"],
                        "explanation": explanation,
                    }
                }
            else:
                return {
                    "web_result": {
                        "success": False,
                        "message": "No properties found with your criteria",
                        "result": "I didn't find any properties matching your search criteria. Try broadening your search parameters.",
                        "url": url_result.get("url"),
                    }
                }

        return {
            "web_result": {
                "success": False,
                "message": "Failed to generate search URL",
                "result": "Sorry, I couldn't process your real estate search query.",
            }
        }

    except Exception as e:
        logger.error(f"Error in web search: {str(e)}")
        return {
            "web_result": {
                "success": False,
                "message": f"Error processing web search: {str(e)}",
                "result": "Sorry, an error occurred while searching for real estate listings.",
            }
        }


async def parse_query_to_url(query: str, llm) -> Dict[str, Any]:
    """
    Parse a natural language query into a real estate search URL.

    Args:
        query: The user's natural language query
        llm: Language model for parameter extraction

    Returns:
        Dict: Result containing the generated URL and explanation
    """
    logger.info(f"Parsing query to URL: '{query}'")

    try:
        # Use LLM to extract parameters from query
        prompt = ChatPromptTemplate.from_messages(
            [("system", PARAM_EXTRACTION_PROMPT), ("human", query)]
        )

        # Call LLM to parse parameters
        logger.debug(f"Sending request to LLM to parse parameters, query: '{query}'")
        response = await llm.ainvoke(prompt.format_messages())

        # Extract JSON from LLM response
        raw_params = extract_json_from_llm_response(response.content)

        # If JSON parsing failed, try manual parameter extraction
        if not raw_params:
            logger.warning(
                "LLM JSON parsing failed, trying manual parameter extraction"
            )
            raw_params = extract_params_manually(query)

        # Map parameters to internal format
        params = map_llm_params_to_internal(raw_params)

        # Build URL
        url = build_url(params, query)

        # Generate search explanation
        explanation = generate_search_explanation(params)
        logger.info(f"Parsing complete: {explanation}")

        return {
            "success": True,
            "url": url,
            "params": params,
            "explanation": explanation,
        }

    except Exception as e:
        logger.error(f"Error parsing query to URL: {str(e)}")
        import traceback

        logger.debug(f"Error details: {traceback.format_exc()}")

        # Return default URL
        return {
            "success": False,
            "url": "https://www.sinyi.com.tw/buy/list/NewTaipei-city/1",
            "error": str(e),
            "explanation": "Could not parse your query, showing default search results for New Taipei City.",
        }


def extract_params_manually(query: str) -> Dict[str, Any]:
    """
    Manually extract key parameters when JSON parsing fails

    Args:
        query: The user's natural language query

    Returns:
        Dict: Extracted parameter dictionary
    """
    from ..tools.url_builder import CITY_MAPPING, DISTRICT_ZIP_MAPPING, TYPE_MAPPING

    logger.info(f"Starting manual parameter extraction: '{query}'")
    params = {}

    # Try to extract city
    for city, code in CITY_MAPPING.items():
        if city in query:
            params["city"] = city
            logger.debug(f"Manually extracted city: {city}")
            break

    # Try to extract district
    for district, zip_code in DISTRICT_ZIP_MAPPING.items():
        if district in query:
            params["district"] = district
            logger.debug(f"Manually extracted district: {district}")
            break

    # Try to extract property type
    house_types = []
    for house_type, type_code in TYPE_MAPPING.items():
        if house_type in query:
            house_types.append(house_type)
            logger.debug(f"Manually extracted property type: {house_type}")

    if house_types:
        params["property_type"] = house_types

    # Check for special keywords
    if "捷運" in query or "mrt" in query.lower():
        params["keyword"] = "捷運"
        logger.debug("Manually extracted keyword: MRT")

    # Check for special conditions
    if "車位" in query:
        if "有車位" in query or "含車位" in query:
            params["special_conditions"] = ["有車位"]
            logger.debug("Manually extracted condition: with parking")
        elif "無車位" in query or "不含車位" in query:
            params["special_conditions"] = ["無車位"]
            logger.debug("Manually extracted condition: without parking")

    logger.info(f"Manual extraction complete, found {len(params)} parameters")
    return params


def extract_json_from_llm_response(response_content: str) -> Dict[str, Any]:
    """
    Extract JSON data from LLM response text

    Args:
        response_content: Raw text of LLM response

    Returns:
        Dict: Parsed JSON data
    """
    logger.debug(
        f"Attempting to extract JSON from LLM response: {response_content[:100]}..."
    )

    # Look for JSON pattern
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response_content)
    if json_match:
        json_str = json_match.group(1)
        logger.debug("Extracted JSON from Markdown code block")
    else:
        json_str = response_content
        logger.debug("No Markdown code block found, using entire response")

    # Clean non-JSON content
    json_str = re.sub(r"^[^{]*", "", json_str)
    json_str = re.sub(r"[^}]*$", "", json_str)

    try:
        params = json.loads(json_str)
        logger.info(f"Successfully parsed JSON: found {len(params)} parameters")
        return params
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing failed: {str(e)}, JSON string: {json_str}")
        return {}
