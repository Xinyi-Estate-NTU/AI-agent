# AI_agent/api.py
"""公共API接口。"""

from typing import Dict, Any, Optional
import pandas as pd
from langsmith import traceable
from langchain.schema import HumanMessage, AIMessage, SystemMessage, FunctionMessage
from .config import DEFAULT_MODEL, DEFAULT_LLM, CONVERSATION_MEMORY, MODELS, logger
from .query_processor import RealEstateQueryProcessor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


@traceable(name="chatGPT")
def chat_pipeline(
    question: str,
    model_name: Optional[str] = None,
    get_chat_history: bool = True,
    memory=None,
    process_real_estate: bool = True,
):
    """
    統一的聊天管道處理函數。

    如果process_real_estate=True，會使用RealEstateQueryProcessor處理房地產相關查詢。
    否則僅使用基本的LLM對話。
    """
    # 使用提供的model_name或預設
    model_name = model_name or DEFAULT_MODEL
    llm = DEFAULT_LLM
    memory = memory or CONVERSATION_MEMORY

    # 處理聊天歷史
    chat_history = []
    if get_chat_history and memory is not None and hasattr(memory, "chat_memory"):
        chat_history = memory.chat_memory.messages

    # 如果是房地產查詢，使用專門的處理器
    if process_real_estate:
        processor = RealEstateQueryProcessor(model_name)
        query_result = processor.process_query(question)

        # 更新記憶體
        if memory is not None:
            memory.chat_memory.add_user_message(question)
            if query_result["success"]:
                memory.chat_memory.add_ai_message(query_result["result"])
            else:
                memory.chat_memory.add_ai_message("抱歉，查詢處理失敗。")

        # 轉換為標準消息格式
        messages = _format_chat_history(chat_history)
        messages.append({"role": "user", "content": question})

        if query_result["success"]:
            answer = query_result["result"]
            messages.append({"role": "assistant", "content": answer})

            # 構建完整結果
            result = {
                "messages": messages,
                "success": True,
                "result": answer,
            }

            # 添加數據框(如果存在)
            if "dataframe" in query_result and query_result["dataframe"] is not None:
                result["dataframe"] = query_result["dataframe"]

            # 添加圖表相關信息(如果存在)
            if "has_chart" in query_result:
                result["has_chart"] = query_result["has_chart"]
                if "chart_image" in query_result:
                    result["chart_image"] = query_result["chart_image"]
                if "trend_direction" in query_result:
                    result["trend_direction"] = query_result["trend_direction"]

            # 添加其他可能的查詢參數
            if "query_params" in query_result:
                result["query_params"] = query_result["query_params"]

            return result
        else:
            error_msg = query_result.get("message", "抱歉，查詢處理失敗。")
            messages.append({"role": "assistant", "content": error_msg})
            return {
                "messages": messages,
                "success": False,
                "result": error_msg,
                "error": query_result.get("error", "未知錯誤"),
            }

    # 一般對話處理
    else:
        # 建立聊天提示
        chat_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "你是一個有用的助手，必須使用繁體中文回答問題。"),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )

        try:
            # 建立訊息內容
            prompt_result = chat_prompt.invoke(
                {"chat_history": chat_history, "question": question}
            )

            # 獲取LLM回應
            response = llm.invoke(prompt_result)

            # 更新記憶體
            if memory is not None:
                memory.chat_memory.add_user_message(question)
                memory.chat_memory.add_ai_message(response.content)

            # 建立回應格式
            messages = _format_chat_history(chat_history)
            messages.append({"role": "user", "content": question})
            messages.append({"role": "assistant", "content": response.content})

            return {
                "messages": messages,
                "success": True,
                "result": response.content,
            }
        except Exception as e:
            logger.error(f"聊天管道錯誤: {e}")
            error_msg = f"處理您的問題時發生錯誤: {str(e)}"
            return {
                "messages": [{"role": "assistant", "content": error_msg}],
                "success": False,
                "result": error_msg,
                "error": str(e),
            }


def _format_chat_history(chat_history):
    """將LangChain消息格式轉換為標準字典格式"""
    messages = []
    for msg in chat_history:
        if isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            messages.append({"role": "assistant", "content": msg.content})
        elif isinstance(msg, SystemMessage):
            messages.append({"role": "system", "content": msg.content})
        elif hasattr(msg, "role") and hasattr(msg, "content"):
            messages.append({"role": msg.role, "content": msg.content})
    return messages


@traceable(name="dataPandasQuery")
def query_sales_data(question, model_name=None):
    """使用pandas dataframe agent查詢房地產銷售資料。"""
    processor = RealEstateQueryProcessor(model_name or DEFAULT_MODEL)
    result = processor.process_query(question)

    if result["success"]:
        return {"answer": result["result"], "raw_response": result}
    else:
        return {"answer": result["message"], "error": result.get("error", "未知錯誤")}


def process_real_estate_query(
    text: str, model_name: Optional[str] = None
) -> Dict[str, Any]:
    """處理房地產查詢的函數接口。"""
    processor = RealEstateQueryProcessor(model_name or DEFAULT_MODEL)
    return processor.process_query(text)


def get_default_model() -> str:
    """獲取默認模型名稱。"""
    return DEFAULT_MODEL


def get_available_models() -> list:
    """獲取所有可用模型列表。"""
    return MODELS


def get_conversation_memory():
    """獲取對話記憶體實例。"""
    return CONVERSATION_MEMORY
