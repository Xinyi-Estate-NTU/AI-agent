# agents/tools/data_analysis.py
import logging
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from typing import Dict, Any, List, Optional, Tuple
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for time filtering
CURRENT_YEAR = 2025


def calculate_average_price(
    df: pd.DataFrame,
    district: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Calculate average real estate prices with additional statistics."""
    logger.info(
        f"Calculating average price, district: {district if district else 'all'}, filters: {filters}"
    )

    # Filter by district if specified
    if district and district in df["鄉鎮市區"].values:
        logger.info(f"Filtering for {district}")
        df = df[df["鄉鎮市區"] == district]

    # Apply other filters
    if filters and isinstance(filters, dict):
        df = filter_data_by_attributes(df, filters)

    # If there's enough data after filtering
    if len(df) > 0:
        # Basic statistics
        avg_price_per_ping = df["每坪單價"].mean()
        avg_total_price = df["總價元"].mean()
        avg_size_ping = df["建物移轉總坪數"].mean()
        count = len(df)

        # Additional statistics
        stats = {
            "median": df["每坪單價"].median(),
            "min": df["每坪單價"].min(),
            "max": df["每坪單價"].max(),
            "std": df["每坪單價"].std(),
            "avg_total_price": avg_total_price,
            "avg_size_ping": avg_size_ping,
        }

        # Calculate district averages if not filtering by district
        district_avg = None
        if district is None and count > 10:
            try:
                district_avg = df.groupby("鄉鎮市區")["每坪單價"].mean().reset_index()
                district_avg = district_avg.sort_values("每坪單價", ascending=False)
                district_avg.columns = ["行政區", "平均每坪價格"]
                district_avg["平均每坪價格"] = district_avg["平均每坪價格"].round(2)
            except Exception as e:
                logger.warning(f"Failed to calculate district averages: {e}")

        return {
            "avg_price": avg_price_per_ping,
            "avg_total_price": avg_total_price,
            "avg_size_ping": avg_size_ping,
            "count": count,
            "district": district,
            "filters": filters,
            "dataframe": district_avg,
            "stats": stats,
        }

    # Empty dataset case
    return {
        "avg_price": None,
        "avg_total_price": None,
        "avg_size_ping": None,
        "count": 0,
        "district": district,
        "filters": filters,
        "dataframe": None,
        "error": "No relevant data found",
    }


def format_price_result(
    result: Dict[str, Any], city: str, filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format real estate price analysis results for readability."""
    # Organize condition info
    conditions_dict = {
        "district": result.get("district"),
        "filters": filters or result.get("filters", {}),
    }

    # Format conditions
    condition_text = _format_conditions(conditions_dict)

    if result.get("avg_price") is None:
        return {
            "success": False,
            "message": f"Could not find data for {city}{condition_text} or dataset is empty",
            "result": f"Sorry, could not find real estate data for {city}{condition_text}.",
            "dataframe": None,
        }

    avg_price = result["avg_price"]
    avg_total_price = result.get("avg_total_price", 0)
    avg_size_ping = result.get("avg_size_ping", 0)
    count = result["count"]

    # Get additional statistics if available
    stats = {}
    if "stats" in result and isinstance(result["stats"], dict):
        stats = result["stats"]

    # Format prices (convert to 10,000s)
    avg_price_wan = round(avg_price / 10000, 1)
    avg_price_ping_formatted = f"{avg_price_wan} 萬元"

    avg_total_price_wan = round(avg_total_price / 10000)
    avg_total_price_formatted = f"{avg_total_price_wan:,} 萬元"

    # Format ping size (round to 1 decimal place)
    avg_size_formatted = f"{avg_size_ping:.1f} 坪"

    # Format count with commas
    count_formatted = f"{count:,}"

    # Build rich result text (Markdown format)
    formatted_result = f"Based on {count_formatted} transaction records, the average real estate prices for {city}{condition_text} are:\n"
    formatted_result += f"- Average price per ping: {avg_price_ping_formatted}\n"

    # Add extra statistics if available
    if stats and "median" in stats:
        median_wan = round(stats["median"] / 10000, 1)
        median_formatted = f"{median_wan} 萬元"
        formatted_result += f"\n- Median price per ping: {median_formatted}\n"

    formatted_result += f"- Average total price: {avg_total_price_formatted}\n"
    formatted_result += f"- Average property size: {avg_size_formatted}\n"
    formatted_result += (
        f"\nData source: Ministry of Interior Real Estate Transaction Data"
    )

    return {
        "success": True,
        "message": "Successfully processed real estate data query",
        "result": formatted_result,
        "dataframe": result.get("dataframe"),
        "stats": stats,
        "avg_price_ping": avg_price,
        "avg_total_price": avg_total_price,
        "avg_size_ping": avg_size_ping,
    }


def generate_price_trend_chart(
    df: pd.DataFrame,
    city: str = None,
    district: str = None,
    chart_type: str = "trend",
    time_range: dict = None,
) -> Dict[str, Any]:
    """Generate price trend chart from real estate data."""
    logger.info(
        f"Generating {chart_type} chart for {city} {district if district else ''}"
    )

    try:
        # Ensure dataframe is not empty
        if df.empty:
            return {
                "success": False,
                "error": "Dataset is empty",
                "result": "Sorry, cannot generate chart from empty dataset.",
            }

        # Filter by district if specified
        if district:
            df = df[df["鄉鎮市區"] == district]
            if df.empty:
                return {
                    "success": False,
                    "error": f"No data for district {district}",
                    "result": f"Sorry, no data available for {district}.",
                }

        # Ensure '交易年月' column exists
        if "交易年月" not in df.columns:
            return {
                "success": False,
                "error": "Missing transaction date column",
                "result": "Sorry, transaction date data is missing.",
            }

        # Apply time range filter if specified
        original_time_range = time_range
        if not time_range:
            time_range = {
                "start_year": CURRENT_YEAR - 5,
                "end_year": CURRENT_YEAR,
                "description": f"{CURRENT_YEAR-5}-{CURRENT_YEAR}",
            }

        # Convert transaction date to year and filter by time range
        df = filter_by_time_range(df, time_range)
        if df.empty:
            return {
                "success": False,
                "error": f"No data for time range {time_range['description']}",
                "result": f"Sorry, no data available for {time_range['description']}.",
            }

        # Group by year and month, calculate average price per ping
        grouped = df.groupby(["交易年", "交易月"])["每坪單價"].mean().reset_index()

        # Create time series index
        grouped["date"] = grouped.apply(
            lambda x: f"{int(x['交易年'])}-{int(x['交易月']):02d}", axis=1
        )
        grouped = grouped.sort_values("date")

        # Calculate trend direction
        trend_direction = "stable"
        if len(grouped) > 1:
            first_avg = grouped["每坪單價"].iloc[0]
            last_avg = grouped["每坪單價"].iloc[-1]
            percent_change = ((last_avg - first_avg) / first_avg) * 100

            if percent_change > 5:
                trend_direction = "up"
            elif percent_change < -5:
                trend_direction = "down"

        # Create plot
        plt.figure(figsize=(10, 6))

        if chart_type == "bar":
            plt.bar(grouped["date"], grouped["每坪單價"] / 10000)
            plt.title(
                f"Average Price per Ping in {city} {district if district else ''} ({time_range['description']})"
            )
        else:  # trend line chart
            plt.plot(grouped["date"], grouped["每坪單價"] / 10000, marker="o")
            plt.title(
                f"Price Trend in {city} {district if district else ''} ({time_range['description']})"
            )

        plt.xlabel("Date (Year-Month)")
        plt.ylabel("Average Price (10,000 NTD per ping)")
        plt.xticks(rotation=45)
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.tight_layout()

        # Save plot to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        chart_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        plt.close()

        # Prepare additional text analysis based on trend
        trend_text = ""
        if trend_direction == "up":
            trend_text = f"Prices have been trending upward in this period, with an increase of approximately {abs(percent_change):.1f}%."
        elif trend_direction == "down":
            trend_text = f"Prices have been trending downward in this period, with a decrease of approximately {abs(percent_change):.1f}%."
        else:
            trend_text = f"Prices have remained relatively stable in this period (change of {abs(percent_change):.1f}%)."

        result_text = f"Price trends for {city} {district if district else ''} during {time_range['description']}:\n\n{trend_text}"

        return {
            "success": True,
            "result": result_text,
            "has_chart": True,
            "chart_image": chart_image,
            "trend_direction": trend_direction,
            "time_range": time_range,
            "dataframe": grouped[["date", "每坪單價"]].rename(
                columns={"每坪單價": "Average Price per Ping (NTD)"}
            ),
        }

    except Exception as e:
        logger.error(f"Error generating trend chart: {e}")
        return {
            "success": False,
            "error": f"Failed to generate chart: {str(e)}",
            "result": f"Sorry, an error occurred while generating the chart: {str(e)}",
        }


def filter_data_by_attributes(
    df: pd.DataFrame, filters: Dict[str, Any]
) -> pd.DataFrame:
    """Filter real estate data by various attributes."""
    if not filters or not isinstance(filters, dict):
        return df

    filtered_df = df.copy()

    # Handle time range filter
    if "時間範圍" in filters and isinstance(filters["時間範圍"], dict):
        filtered_df = filter_by_time_range(filtered_df, filters["時間範圍"])

    # Room count filter
    if "建物現況格局-房" in filters and filters["建物現況格局-房"] is not None:
        filtered_df = filtered_df[
            filtered_df["建物現況格局-房"] == filters["建物現況格局-房"]
        ]

    # Living room count filter
    if "建物現況格局-廳" in filters and filters["建物現況格局-廳"] is not None:
        filtered_df = filtered_df[
            filtered_df["建物現況格局-廳"] == filters["建物現況格局-廳"]
        ]

    # Bathroom count filter
    if "建物現況格局-衛" in filters and filters["建物現況格局-衛"] is not None:
        filtered_df = filtered_df[
            filtered_df["建物現況格局-衛"] == filters["建物現況格局-衛"]
        ]

    # Elevator filter
    if "電梯" in filters and filters["電梯"] is not None:
        filtered_df = filtered_df[filtered_df["電梯"] == filters["電梯"]]

    # Building age filter
    if "屋齡" in filters and filters["屋齡"] is not None:
        if (
            isinstance(filters["屋齡"], dict)
            and "min" in filters["屋齡"]
            and "max" in filters["屋齡"]
        ):
            # Range filter
            filtered_df = filtered_df[
                (filtered_df["屋齡"] >= filters["屋齡"]["min"])
                & (filtered_df["屋齡"] <= filters["屋齡"]["max"])
            ]
        elif isinstance(filters["屋齡"], (int, float)):
            # Exact match filter
            filtered_df = filtered_df[filtered_df["屋齡"] == filters["屋齡"]]

    return filtered_df


def filter_by_time_range(df: pd.DataFrame, time_range: Dict[str, Any]) -> pd.DataFrame:
    """Filter dataframe by time range."""
    if not time_range or not isinstance(time_range, dict):
        return df

    if "start_year" not in time_range or "end_year" not in time_range:
        return df

    start_year = time_range["start_year"]
    end_year = time_range["end_year"]

    # Ensure column exists
    if "交易年" not in df.columns and "交易年月" in df.columns:
        # Extract year from '交易年月'
        df["交易年"] = df["交易年月"].astype(str).str[:3].astype(int) + 1911
        df["交易月"] = df["交易年月"].astype(str).str[3:].astype(int)

    # Filter by year range
    if "交易年" in df.columns:
        filtered_df = df[(df["交易年"] >= start_year) & (df["交易年"] <= end_year)]
        return filtered_df

    return df


def execute_pandas_agent_query(
    df: pd.DataFrame, query_text: str, llm, generate_plot: bool = False
) -> Dict[str, Any]:
    """Execute data query using Pandas Agent, with optional chart generation."""
    logger.info(f"Using Pandas Agent for query: '{query_text}'")

    try:
        # Ensure DataFrame is not empty
        if df.empty:
            return {
                "success": False,
                "error": "Dataset is empty",
                "result": "Sorry, cannot analyze empty dataset.",
            }

        # Reduce sample size for large datasets
        if len(df) > 50000:
            logger.info(f"Large dataset ({len(df)} records), sampling for analysis")
            df = df.sample(50000, random_state=42)

        # Create Pandas DataFrame Agent
        pandas_agent = create_pandas_dataframe_agent(
            llm,
            df,
            verbose=True,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            allow_dangerous_code=True,
        )

        # Set timeout
        import time

        start_time = time.time()
        max_time = 60  # Maximum 60 seconds

        # If chart generation is needed, use more explicit instructions
        if generate_plot:
            modified_query = (
                "Please analyze the data and generate a chart for the following question: "
                f"{query_text}\n"
                "Provide detailed analysis and explanation."
            )
        else:
            modified_query = query_text

        # Execute query
        logger.info(f"Sending query to Agent: '{modified_query}'")
        response = pandas_agent.run(modified_query)

        elapsed_time = time.time() - start_time
        logger.info(f"Query execution completed in {elapsed_time:.2f} seconds")

        # Check for generated charts
        has_chart = False
        chart_data = None

        # In a real implementation, we would handle chart detection

        return {
            "success": True,
            "result": response,
            "has_chart": has_chart,
            "chart_data": chart_data,
            "execution_time": elapsed_time,
        }

    except Exception as e:
        logger.error(f"Error executing pandas agent query: {e}")
        return {
            "success": False,
            "error": f"Query execution failed: {str(e)}",
            "result": f"Sorry, an error occurred during analysis: {str(e)}",
        }


def _format_conditions(conditions_dict: Dict[str, Any]) -> str:
    """Convert conditions dictionary to human-readable text."""
    conditions = []

    # Handle district
    district = conditions_dict.get("district")
    if district:
        conditions.append(district)

    # Handle filters
    filters = conditions_dict.get("filters", {})
    if filters:
        # Time range
        if "時間範圍" in filters and isinstance(filters["時間範圍"], dict):
            conditions.append(filters["時間範圍"].get("description", ""))

        # Property attributes
        attr_mapping = {
            "建物現況格局-房": lambda v: f"{v}房",
            "建物現況格局-廳": lambda v: f"{v}廳",
            "建物現況格局-衛": lambda v: f"{v}衛",
            "電梯": lambda v: f"{'有' if v == '有' else '無'}電梯",
            "屋齡": lambda v: (
                f"{v}年屋齡"
                if isinstance(v, (int, float))
                else (
                    f"{v['min']}-{v['max']}年屋齡"
                    if isinstance(v, dict) and "min" in v and "max" in v
                    else None
                )
            ),
        }

        for attr, formatter in attr_mapping.items():
            if attr in filters and filters[attr] is not None and filters[attr] != "":
                formatted_value = formatter(filters[attr])
                if formatted_value:
                    conditions.append(formatted_value)

    return "、".join(conditions) if conditions else ""
