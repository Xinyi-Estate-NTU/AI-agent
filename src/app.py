import streamlit as st
import os
import pandas as pd
from AI_agent import RealEstateQueryProcessor, chat_pipeline, CONVERSATION_MEMORY, DEFAULT_MODEL, MODELS, logger
import logging
logger = logging.getLogger(__name__)
# ------ 設定頁面基本資訊 ------
st.set_page_config(
    page_title="AI 房地產資料助理",
    page_icon="🏠",
    layout="wide"
)

# ------ 自訂 CSS 美化 UI ------
st.markdown(
    """
    <style>
    .chat-container {
        max-width: 800px;
        margin: auto;
    }
    .user-message {
        background-color: #DCF8C6; /* WhatsApp 綠色 */
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
        text-align: right;
    }
    .assistant-message {
        background-color: #EDEDED; /* Messenger 灰色 */
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
        text-align: left;
    }
    .source-box {
        font-size: 12px;
        color: #555;
        margin-top: 5px;
        padding: 5px;
        border-left: 3px solid #4CAF50;
    }
    .data-table {
        margin-top: 10px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ------ 側邊欄 (Sidebar) 設計 ------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=80)
    st.header("台灣房地產資料助理")
    st.markdown("🏠 **AI 房地產資料助理** 可以分析台北市和新北市的房地產資料，幫助你做出更明智的決策。")
    
    # Model selection
    selected_model = st.selectbox("選擇對話模型", MODELS)
    
    # Store the selected model in session state for persistence
    if "selected_model" not in st.session_state or st.session_state.selected_model != selected_model:
        st.session_state.selected_model = selected_model
        # Use st.rerun() instead of experimental_rerun
        if "messages" in st.session_state and len(st.session_state.messages) > 0:
            st.info("模型已更改，重置對話以套用新模型。")
    
    st.markdown("📩 聯絡我們: support@example.com")
    st.markdown("💡 你可以詢問有關台灣房地產的問題，例如：")
    st.markdown("- 台北市大安區的平均房價")
    st.markdown("- 新北市哪個區域的房價最高")
    st.markdown("- 2020年信義區的房價趨勢")

# ------ 初始化 Session State ------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "memory" not in st.session_state:
    # 使用query_analyzer.py裡的ConversationBufferMemory
    st.session_state.memory = CONVERSATION_MEMORY

if "session_id" not in st.session_state:
    st.session_state.session_id = f"thread-{os.urandom(4).hex()}"

if "processor" not in st.session_state:
    # 初始化查詢處理器
    st.session_state.processor = RealEstateQueryProcessor(DEFAULT_MODEL)

# ------ 主畫面 UI ------
st.title("🏠 台灣房地產資料助理")
st.markdown("**請在下方輸入您的房地產相關問題，我們將為您提供專業的分析與解答。**")

# ------ 聊天框 (Chat Display) ------
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        logger.info(f"message: {message}")
        if message["role"] == "user":
            st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
        elif message["role"] == "assistant":
            st.markdown(f'<div class="assistant-message">{message["content"]}</div>', unsafe_allow_html=True)
            
            # 注意：歷史消息中不會包含實際圖表數據，只有標記
            # 顯示"查看原圖表"提示
            if message.get("has_chart", False):
                st.info("此回應包含趨勢圖表。請重新提問以查看完整圖表。")
            
            # 如果有數據表格，顯示它
            if "dataframe" in message:
                if isinstance(message["dataframe"], pd.DataFrame) and not message["dataframe"].empty:
                    st.dataframe(message["dataframe"], use_container_width=True)

# ------ 使用者輸入 (Chat Input) ------
user_question = st.chat_input("💬 請輸入您的房地產問題...")

# ------ 處理使用者輸入 ------
if user_question:
    # 顯示使用者訊息
    st.session_state.messages.append({"role": "user", "content": user_question})
    st.markdown(f'<div class="user-message">{user_question}</div>', unsafe_allow_html=True)
    
    # 處理AI回應
    with st.spinner("AI分析中，請稍候..."):
        try:
            # 使用processor直接處理
            processor = st.session_state.processor
            
            # 更新處理器的模型
            if processor.model_name != st.session_state.selected_model:
                processor = RealEstateQueryProcessor(st.session_state.selected_model)
                st.session_state.processor = processor
                logger.info(f"更新模型: {st.session_state.selected_model}")
            
            # 處理查詢
            result = processor.process_query(user_question)
            
            # 添加日誌，記錄結果中是否包含解析的參數
            if result.get("query_params"):
                logger.info(f"查詢參數解析結果: {result.get('query_params')}")
            
            # 檢查處理結果
            if result["success"]:
                answer = result["result"]
                dataframe = result.get("dataframe")
                
                print(f"[DEBUG-APP] 查詢成功，result keys: {list(result.keys())}")
                
                # 儲存到對話歷史
                message_data = {
                    "role": "assistant",
                    "content": answer
                }
                
                # 如果有數據表格，也保存
                if dataframe is not None:
                    message_data["dataframe"] = dataframe
                    print(f"[DEBUG-APP] 包含數據表格，行數: {len(dataframe)}")
                
                # 處理圖表
                has_chart = result.get("has_chart", False)
                print(f"[DEBUG-APP] has_chart: {has_chart}")
                
                chart_data = None
                if has_chart and "chart_image" in result:
                    chart_data = result["chart_image"]
                    print(f"[DEBUG-APP] 包含圖表數據, 類型: {type(chart_data)}")
                    if hasattr(chart_data, 'getvalue'):
                        print(f"[DEBUG-APP] 圖表數據大小: {len(chart_data.getvalue())} 字節")
                
                # 添加圖表標記
                message_data["has_chart"] = has_chart
                
                st.session_state.messages.append(message_data)
                
                # 顯示助理回應
                st.markdown(f'<div class="assistant-message">{answer}</div>', unsafe_allow_html=True)
                
                # 如果有圖表，使用st.image顯示它
                if has_chart and chart_data is not None:
                    print(f"[DEBUG-APP] 嘗試顯示圖表")
                    try:
                        # 直接使用BytesIO對象
                        st.image(chart_data, caption=f"{result.get('trend_direction', '房價')}趨勢圖", use_container_width=True)
                        print(f"[DEBUG-APP] 圖表顯示完成")
                    except Exception as img_error:
                        print(f"[ERROR] 顯示圖表時出錯: {img_error}")
                        import traceback
                        print(f"[DEBUG-APP-ERROR] 顯示圖表錯誤堆疊: {traceback.format_exc()}")
                        st.error(f"無法顯示趨勢圖: {str(img_error)}")
                else:
                    print(f"[DEBUG-APP] 沒有圖表數據可顯示: has_chart={has_chart}, chart_data存在={chart_data is not None}")
                
                # 如果有數據表格，顯示它
                if dataframe is not None and not dataframe.empty:
                    print(f"[DEBUG-APP] 顯示數據表格")
                    st.dataframe(dataframe, use_container_width=True)
            else:
                answer = "抱歉，查詢處理失敗。"
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            answer = f"處理問題時發生錯誤: {str(e)}"
            st.error(f"詳細錯誤: {error_details}")
            
            # 儲存錯誤回應
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

# Add clear conversation button
if st.button("清空對話"):
    st.session_state.messages = []
    st.session_state.memory = CONVERSATION_MEMORY
    st.session_state.session_id = f"thread-{os.urandom(4).hex()}"
    st.session_state.processor = RealEstateQueryProcessor(st.session_state.selected_model)
    st.rerun()

# Show conversation stats
num_messages = len(st.session_state.messages)