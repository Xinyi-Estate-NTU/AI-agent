# AI_agent/api.py
"""公共API接口。"""

from typing import Dict, Any, Optional
from langsmith import traceable
from langchain.schema import HumanMessage, AIMessage, SystemMessage, FunctionMessage
from .config import DEFAULT_MODEL, DEFAULT_LLM, CONVERSATION_MEMORY, logger
from .query_processor import RealEstateQueryProcessor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

@traceable(name="chatGPT")
def chat_pipeline(question, get_chat_history=False, langsmith_extra=None, memory=None, llm=None):
    """使用最新的LangChain API進行聊天管道處理"""
    # 使用提供的LLM或預設
    model = llm if llm is not None else DEFAULT_LLM
    
    # 建立聊天提示
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一個有用的助手，必須使用繁體中文回答問題。"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])
    
    # 處理聊天歷史
    chat_history = []
    if get_chat_history and memory is not None and hasattr(memory, 'chat_memory'):
        chat_history = memory.chat_memory.messages
    
    # 處理回應
    try:
        # 建立訊息內容
        result = chat_prompt.invoke({
            "chat_history": chat_history,
            "question": question
        })
        
        # 獲取LLM回應
        response = model.invoke(result)
        
        # 更新記憶體
        if memory is not None:
            memory.chat_memory.add_user_message(question)
            memory.chat_memory.add_ai_message(response.content)
        
        # 建立回應格式
        messages = []
        for msg in chat_history:
            if isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                messages.append({"role": "system", "content": msg.content})
            elif hasattr(msg, 'role') and hasattr(msg, 'content'):
                messages.append({"role": msg.role, "content": msg.content})
        
        messages.append({"role": "user", "content": question})
        messages.append({"role": "assistant", "content": response.content})
        
        return {"messages": messages}
    except Exception as e:
        logger.error(f"聊天管道錯誤: {e}")
        return {"messages": [{"role": "assistant", "content": f"處理您的問題時發生錯誤: {str(e)}"}], "error": str(e)}

@traceable(name="dataPandasQuery")
def query_sales_data(question, model_name=None):
    """使用pandas dataframe agent查詢房地產銷售資料。"""
    processor = RealEstateQueryProcessor(model_name or DEFAULT_MODEL)
    result = processor.process_query(question)
    
    if result["success"]:
        return {
            "answer": result["result"],
            "raw_response": result
        }
    else:
        return {
            "answer": result["message"],
            "error": result.get("error", "未知錯誤")
        }

def process_real_estate_query(text: str, model_name: Optional[str] = None) -> Dict[str, Any]:
    """處理房地產查詢的函數接口。"""
    processor = RealEstateQueryProcessor(model_name or DEFAULT_MODEL)
    return processor.process_query(text)