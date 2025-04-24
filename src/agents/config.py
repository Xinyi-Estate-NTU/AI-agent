# agents/config.py
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# LLM Models configuration
MODELS = [
    "llama3-8b-8192",
    "llama3-70b-8192",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
]
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", MODELS[0])

# Graph configuration
MAX_RETRIES = 3
DEFAULT_TEMPERATURE = 0
CONVERSATION_MEMORY_KEY = "chat_history"

# Taiwan-specific constants
CURRENT_YEAR = 2025
TAIPEI_DISTRICTS = [
    "大安區",
    "信義區",
    "中正區",
    "松山區",
    "大同區",
    "萬華區",
    "文山區",
    "南港區",
    "內湖區",
    "士林區",
    "北投區",
]
NEW_TAIPEI_DISTRICTS = [
    "板橋區",
    "三重區",
    "中和區",
    "永和區",
    "新莊區",
    "新店區",
    "土城區",
    "蘆洲區",
    "汐止區",
    "樹林區",
    "淡水區",
    "三峽區",
    "鶯歌區",
    "林口區",
    "五股區",
    "泰山區",
    "瑞芳區",
    "八里區",
    "深坑區",
    "石碇區",
    "三芝區",
    "金山區",
    "萬里區",
    "平溪區",
    "雙溪區",
    "貢寮區",
    "坪林區",
    "石門區",
    "烏來區",
]

# Data loading configuration
CACHE_EXPIRY_SECONDS = 3600  # 1 hour cache expiry
DATA_PATHS = {"台北市": "data/TP_Sales.csv", "新北市": "data/NTP_Sales.csv"}

# Web API configuration
SINYI_BASE_URL = "https://www.sinyi.com.tw/buy/list"
WEB_TIMEOUT = 10  # seconds


def get_model(model_name: Optional[str] = None, temperature: Optional[float] = None):
    """
    Get a LangChain LLM instance with the specified model and temperature.

    Args:
        model_name: Name of the model to use (from MODELS list)
        temperature: Temperature for generation (0 to 1)

    Returns:
        ChatGroq instance
    """
    # Validate model name
    model = model_name if model_name in MODELS else DEFAULT_MODEL
    temp = temperature if temperature is not None else DEFAULT_TEMPERATURE

    logger.info(f"Creating LLM with model={model}, temperature={temp}")

    # Create and return the LLM
    return ChatGroq(model_name=model, temperature=temp)


def create_memory():
    """
    Create a conversation memory instance.

    Returns:
        ConversationBufferMemory instance
    """
    return ConversationBufferMemory(
        memory_key=CONVERSATION_MEMORY_KEY, return_messages=True
    )


def get_api_key(service_name: str) -> Optional[str]:
    """
    Get API key for a specific service from environment variables.

    Args:
        service_name: Name of the service to get API key for

    Returns:
        API key if available, None otherwise
    """
    key_name = f"{service_name.upper()}_API_KEY"
    api_key = os.getenv(key_name)

    if not api_key:
        logger.warning(f"No API key found for {service_name}")

    return api_key
