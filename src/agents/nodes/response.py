# agents/nodes/response.py
import logging
from typing import Dict, Any, List, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# System prompt for response generation
RESPONSE_SYSTEM_PROMPT = """You are a helpful real estate assistant that provides clear, accurate information about property prices, trends, and listings in Taiwan.

You have access to two main data sources:
1. Real estate price data analysis (historical transaction data, price trends, charts)
2. Web search results from real estate listing websites

Given the user's query and the results from these data sources, generate a comprehensive, concise response that directly answers their question. Focus on providing factual information without unnecessary embellishments.

Format your response according to these guidelines:
- Start with the most relevant information that directly answers the user's question
- Use bullet points for listing multiple properties or data points
- Include both textual insights and reference any charts or graphs when available
- Mention the source of information (e.g., "Based on historical transaction data..." or "From current property listings...")
- Keep your response focused and concise

Note: If the data shows "N/A" or is missing for certain fields, don't mention those fields in your response.
"""


def generate_response(state):
    """
    Generate a comprehensive response by combining results from different tools.
    This is the final node in the graph that produces the response to the user.
    """
    query = state["user_input"]
    data_result = state.get("data_result")
    web_result = state.get("web_result")

    logger.info(f"Generating response for query: '{query}'")

    try:
        # If both results are None or unsuccessful, create a fallback response
        if (not data_result or not data_result.get("success", False)) and (
            not web_result or not web_result.get("success", False)
        ):

            final_response = (
                "I'm sorry, I couldn't find information to answer your question about real estate. "
                "Could you please provide more specific details about what you're looking for?"
            )

            return {"final_response": final_response}

        # Determine if we need advanced response generation
        needs_advanced_generation = _check_if_needs_advanced_generation(
            data_result, web_result, query
        )

        if needs_advanced_generation:
            # Use LLM to combine results in a natural way
            final_response = _generate_combined_response(query, data_result, web_result)
        else:
            # Simple concatenation for straightforward cases
            final_response = _create_simple_response(data_result, web_result)

        # Check if we have chart data to include
        has_chart = False
        chart_image = None

        if data_result and data_result.get("has_chart", False):
            has_chart = True
            chart_image = data_result.get("chart_image")

        return {
            "final_response": final_response,
            "has_chart": has_chart,
            "chart_image": chart_image,
        }

    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")

        # Create fallback response on error
        error_response = (
            "I apologize, but I encountered an error while generating your response. "
            "Please try asking your question again or rephrase it for better results."
        )

        return {"final_response": error_response}


def _check_if_needs_advanced_generation(data_result, web_result, query):
    """
    Determine if the response needs advanced LLM-based generation.

    Returns:
        bool: True if advanced generation is needed
    """
    # If we have both data and web results, we need to combine them coherently
    if (
        data_result
        and web_result
        and data_result.get("success")
        and web_result.get("success")
    ):
        return True

    # If the query is complex (based on length or structure)
    if len(query) > 50 or "，" in query or "。" in query or "、" in query:
        return True

    # For simpler queries with a single result, simple response is fine
    return False


def _create_simple_response(data_result, web_result):
    """
    Create a simple concatenated response when advanced generation isn't needed.

    Returns:
        str: Formatted response text
    """
    if data_result and data_result.get("success", False):
        return data_result.get("result", "No data results available.")

    if web_result and web_result.get("success", False):
        return web_result.get("result", "No web results available.")

    # Fallback
    return "I couldn't find the specific information you're looking for."


def _generate_combined_response(query, data_result, web_result):
    """
    Use LLM to generate a natural combined response from multiple data sources.

    Returns:
        str: Natural language response combining all available data
    """
    # Initialize LLM
    llm = ChatGroq(model_name="llama3-8b-8192", temperature=0.1)

    # Construct context from available results
    context = "Here is the information I have:\n\n"

    if data_result and data_result.get("success", False):
        context += "DATA ANALYSIS RESULTS:\n"
        context += data_result.get("result", "No data results available.") + "\n\n"

    if web_result and web_result.get("success", False):
        context += "WEB SEARCH RESULTS:\n"
        context += web_result.get("result", "No web results available.") + "\n\n"

    # Create prompt for response generation
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", RESPONSE_SYSTEM_PROMPT),
            (
                "human",
                f"User query: {query}\n\n{context}\n\nPlease generate a comprehensive response that combines these results in a natural way.",
            ),
        ]
    )

    # Generate response
    response = llm.invoke(prompt.format_messages())

    # Clean up any potential artifacts
    final_response = response.content.strip()

    # Remove any markdown formatting artifacts
    final_response = final_response.replace("```", "").replace("markdown", "")

    logger.info(f"Generated combined response of length: {len(final_response)}")

    return final_response
