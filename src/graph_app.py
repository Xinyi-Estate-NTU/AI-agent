# graph_app.py
import streamlit as st
import os
import pandas as pd
import uuid
import base64
from io import BytesIO
import logging
from dotenv import load_dotenv

# Import the LangGraph agent components
from agents.graph import process_query, get_thread_history
from agents.config import MODELS, DEFAULT_MODEL, TAIPEI_DISTRICTS, NEW_TAIPEI_DISTRICTS

# Configure root logger once
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

# Prevent duplicate logs in imported modules
for logger_name in logging.root.manager.loggerDict:
    logging.getLogger(logger_name).propagate = True
    logging.getLogger(logger_name).handlers = []

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ------ Page Configuration ------
st.set_page_config(page_title="AI Real Estate Assistant", page_icon="🏠", layout="wide")

# ------ Custom CSS for UI ------
st.markdown(
    """
    <style>
    .chat-container {
        max-width: 800px;
        margin: auto;
    }
    .source-box {
        font-size: 12px;
        color: #555;
        margin-top: 5px;
        padding: 5px;
        border-left: 3px solid #4CAF50;
    }
    .property-card {
        border: 1px solid #eee;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        transition: all 0.3s;
    }
    .property-card:hover {
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }
    .price-tag {
        color: #e63946;
        font-weight: bold;
        font-size: 1.2em;
    }
    .discount-tag {
        background-color: #e63946;
        color: white;
        padding: 2px 5px;
        border-radius: 4px;
        font-size: 0.8em;
    }
    .feature-tag {
        background-color: #f1faee;
        padding: 3px 6px;
        margin-right: 5px;
        border-radius: 4px;
        font-size: 0.8em;
        display: inline-block;
        margin-bottom: 3px;
    }
    .stTextInput>div>div>input {
        caret-color: #4CAF50;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------ Initialize Session State ------
def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"thread-{uuid.uuid4()}"

    if "selected_model" not in st.session_state:
        st.session_state.selected_model = DEFAULT_MODEL

    if "property_data" not in st.session_state:
        st.session_state.property_data = None

    if "advanced_options" not in st.session_state:
        st.session_state.advanced_options = False


# Initialize
initialize_session_state()


# ------ Sidebar Design ------
def render_sidebar():
    """Render the sidebar"""
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=80)
        st.header("Taiwan Real Estate Assistant")
        st.markdown(
            "🏠 **AI Real Estate Assistant** can analyze real estate data for Taipei and New Taipei, helping you make informed decisions."
        )

        # Model selection
        selected_model = st.selectbox("Select LLM Model", MODELS)

        # Store the selected model in session state
        if st.session_state.selected_model != selected_model:
            st.session_state.selected_model = selected_model
            if len(st.session_state.messages) > 0:
                st.info("Model changed. New model will be used for your next query.")

        # Advanced options
        st.session_state.advanced_options = st.checkbox(
            "Show Advanced Options", value=st.session_state.advanced_options
        )

        if st.session_state.advanced_options:
            # Thread ID
            st.text_input(
                "Thread ID",
                value=st.session_state.thread_id,
                disabled=True,
                help="This identifies your conversation history.",
            )

            # Option to create a new thread
            if st.button("Start New Conversation"):
                st.session_state.thread_id = f"thread-{uuid.uuid4()}"
                st.session_state.messages = []
                st.rerun()

        st.markdown("---")
        st.markdown("💡 **Example Questions:**")
        st.markdown(
            "- What's the average price of 3-bedroom apartments in Daan District, Taipei from 2020-2024?"
        )
        st.markdown("- Find me apartments near MRT stations in Xinyi District")
        st.markdown("- Show me the price trend in New Taipei City for the last 5 years")
        st.markdown("- What are the most expensive districts in Taipei?")


# Display chat history
def render_chat_history():
    """Render chat history"""
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(message["content"])
            elif message["role"] == "assistant":
                with st.chat_message("assistant"):
                    st.markdown(message["content"])

                    # Display chart if present
                    if message.get("has_chart", False) and message.get("chart_image"):
                        st.image(
                            message["chart_image"],
                            caption="Real Estate Price Trend",
                            use_container_width=True,
                        )

                    # Display property data if present
                    if message.get("properties") and len(message["properties"]) > 0:
                        with st.expander("View Property Listings", expanded=True):
                            render_property_listings(message["properties"])


# Render property listings
def render_property_listings(property_data):
    """Render property listings"""
    if not property_data or len(property_data) == 0:
        st.info("No property listings found.")
        return

    st.subheader(f"Found {len(property_data)} Properties")

    # Display each property
    for property_item in property_data:
        with st.container():
            # Create a card-style container
            with st.expander(
                property_item.get("property_name", "Unknown"), expanded=True
            ):
                # Two-column layout - image and info
                col1, col2 = st.columns([1, 1])

                with col1:
                    # Handle image URL
                    image_url = property_item.get("image_url", "")
                    if image_url:
                        st.image(image_url, use_container_width=True)

                with col2:
                    # Display main information
                    if property_item.get("community_name"):
                        st.markdown(
                            f"**Community**: {property_item.get('community_name')}"
                        )

                    st.markdown(
                        f"**Location**: {property_item.get('location', 'Unknown location')}"
                    )

                    # Price information
                    price_html = f"**Price**: <span style='color:#e63946; font-weight:bold; font-size:1.2em;'>{property_item.get('current_price', '')} {property_item.get('price_unit', '萬')}</span>"
                    if property_item.get("original_price"):
                        price_html += f" <small><s>{property_item.get('original_price', '')}</s></small>"
                    st.markdown(price_html, unsafe_allow_html=True)

                    # Basic info
                    st.markdown(f"**Layout**: {property_item.get('layout', 'Unknown')}")
                    st.markdown(f"**Size**: {property_item.get('total_size', '')}")
                    st.markdown(f"**Floor**: {property_item.get('floor', '')}")
                    st.markdown(
                        f"**Age**: {property_item.get('property_age', '')} | **Type**: {property_item.get('property_type', '')}"
                    )

                # Bottom section for features and interest count
                st.markdown("---")

                # Process features without duplicates
                features_list = []
                if property_item.get("features"):
                    features_list = [
                        f.get("feature", "")
                        for f in property_item.get("features", [])
                        if f.get("feature")
                    ]
                    # Remove duplicates
                    features_list = list(dict.fromkeys(features_list))

                # Display features
                if features_list:
                    feature_cols = st.columns(min(3, len(features_list)))
                    for i, feature in enumerate(features_list[:3]):
                        feature_cols[i].markdown(f"🏷️ {feature}")

                # Display interest count
                if property_item.get("interest_count"):
                    st.markdown(
                        f"👀 **{property_item.get('interest_count', '0')}** people interested"
                    )


# Main application workflow
def main():
    # Render sidebar
    render_sidebar()

    # Main interface title
    st.title("🏠 Taiwan Real Estate Assistant")
    st.markdown(
        "**Ask any real estate related questions about Taiwan. I can analyze data, search listings, and provide insights.**"
    )

    # Display chat history
    render_chat_history()

    # User input
    user_question = st.chat_input("💬 Ask about real estate in Taiwan...")

    # Process user input
    if user_question:
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": user_question})

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_question)

        # Process with AI
        with st.spinner("Analyzing your query..."):
            try:
                # Get the selected model
                model_name = st.session_state.selected_model
                logger.info(f"Using model: {model_name}")

                # Process query using LangGraph
                result = process_query(
                    query=user_question,
                    thread_id=st.session_state.thread_id,
                    model_name=model_name,
                )

                # Format the response
                ai_message = {
                    "role": "assistant",
                    "content": result.get("response", "I couldn't process your query."),
                    "has_chart": result.get("has_chart", False),
                }

                # Add chart image if available
                if result.get("has_chart", False) and result.get("chart_image"):
                    ai_message["chart_image"] = result.get("chart_image")

                # Add property data if available
                if result.get("web_result") and "properties" in result.get(
                    "web_result", {}
                ):
                    properties = result["web_result"]["properties"]
                    ai_message["properties"] = properties
                    st.session_state.property_data = properties

                # Add message to history
                st.session_state.messages.append(ai_message)

                # Display assistant response
                with st.chat_message("assistant"):
                    st.markdown(ai_message["content"])

                    # Display chart if available
                    if ai_message.get("has_chart", False) and ai_message.get(
                        "chart_image"
                    ):
                        st.image(
                            ai_message["chart_image"],
                            caption="Real Estate Price Trend",
                            use_container_width=True,
                        )

                    # Display property data if available
                    if "properties" in ai_message and len(ai_message["properties"]) > 0:
                        with st.expander("View Property Listings", expanded=True):
                            render_property_listings(ai_message["properties"])

            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                logger.error(f"Error processing query: {error_details}")

                error_response = (
                    f"I encountered an error while processing your query: {str(e)}"
                )
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_response}
                )

                with st.chat_message("assistant"):
                    st.error(error_response)

    # Clear conversation button
    if st.button("Clear Conversation"):
        # Create a new thread ID
        st.session_state.thread_id = f"thread-{uuid.uuid4()}"
        st.session_state.messages = []
        st.session_state.property_data = None
        st.rerun()


# Execute main function
if __name__ == "__main__":
    main()
