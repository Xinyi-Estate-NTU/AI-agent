import streamlit as st
import os
import pandas as pd
import asyncio
from data_agent import (
    chat_pipeline,
    get_default_model,
    get_available_models,
    get_conversation_memory,
)

# Import the web agent
from web_agent import process_web_query
import logging

#######################
### 1. COMMON PARTS ###
#######################

# Configure root logger once
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

# Prevent duplicate logs in imported modules
for logger_name in logging.root.manager.loggerDict:
    logging.getLogger(logger_name).propagate = True
    logging.getLogger(logger_name).handlers = []

logger = logging.getLogger(__name__)

# ------ 設定頁面基本資訊 ------
st.set_page_config(page_title="AI 房地產資料助理", page_icon="🏠", layout="wide")

# ------ 自訂 CSS 美化 UI ------
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
    </style>
    """,
    unsafe_allow_html=True,
)

# 通過API獲取配置
DEFAULT_MODEL = get_default_model()
MODELS = get_available_models()
CONVERSATION_MEMORY = get_conversation_memory()


# ------ 初始化 Session State ------
def initialize_session_state():
    """初始化Session State變數"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "memory" not in st.session_state:
        st.session_state.memory = CONVERSATION_MEMORY

    if "session_id" not in st.session_state:
        st.session_state.session_id = f"thread-{os.urandom(4).hex()}"

    if "selected_model" not in st.session_state:
        st.session_state.selected_model = DEFAULT_MODEL

    if "selected_agent" not in st.session_state:
        st.session_state.selected_agent = "資料分析助理"

    if "property_data" not in st.session_state:
        st.session_state.property_data = None


# 初始化
initialize_session_state()


# ------ 側邊欄 (Sidebar) 設計 ------
def render_sidebar():
    """渲染側邊欄"""
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=80)
        st.header("台灣房地產資料助理")
        st.markdown(
            "🏠 **AI 房地產資料助理** 可以分析台北市和新北市的房地產資料，幫助你做出更明智的決策。"
        )

        # Model selection
        selected_model = st.selectbox("選擇對話模型", MODELS)

        # Store the selected model in session state for persistence
        if (
            "selected_model" not in st.session_state
            or st.session_state.selected_model != selected_model
        ):
            st.session_state.selected_model = selected_model
            if "messages" in st.session_state and len(st.session_state.messages) > 0:
                st.info("模型已更改，重置對話以套用新模型。")

        # 代理選擇
        agent_options = ["資料分析助理", "房產搜尋助理"]
        selected_agent = st.radio("選擇代理類型", agent_options)
        if (
            "selected_agent" not in st.session_state
            or st.session_state.selected_agent != selected_agent
        ):
            st.session_state.selected_agent = selected_agent
            # 切換代理時清空房產數據
            if selected_agent == "資料分析助理":
                st.session_state.property_data = None

        st.markdown("💡 你可以詢問有關台灣房地產的問題，例如：")
        st.markdown("- 臺北市大安區近兩年三房兩廳的行情如何? (資料分析)")
        st.markdown(
            "- 目前預算只有3000萬，想要在臺北市買有電梯三房以上的房子，可以買在哪些地區？ (資料分析)"
        )
        st.markdown("- 我要找新北市板橋區不要四樓有游泳池的房子 (網頁搜尋)")


# 顯示對話歷史
def render_chat_history():
    """渲染對話歷史"""
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(message["content"])
            elif message["role"] == "assistant":
                with st.chat_message("assistant"):
                    st.markdown(message["content"])

                # 如果有趨勢圖表標記但沒有當前圖表數據
                if message.get("has_chart", False) and "chart_image" not in message:
                    st.info("此回應包含趨勢圖表。請重新提問以查看完整圖表。")


########################
### 2. DATA AGENT 部分 ###
########################


# 處理資料分析查詢
def handle_data_agent_query(user_question, model_name, memory):
    """處理資料分析助理的查詢"""
    logger.info(f"處理資料分析查詢: '{user_question}'")

    # 使用原來的數據分析代理
    result = chat_pipeline(
        question=user_question,
        model_name=model_name,
        memory=memory,
        get_chat_history=True,
        process_real_estate=True,
    )

    return result


# 顯示資料分析結果
def render_data_agent_result(result):
    """渲染資料分析助理的結果"""
    if result["success"]:
        answer = result["result"]

        # 儲存到對話歷史
        message_data = {"role": "assistant", "content": answer}

        # 處理圖表
        has_chart = result.get("has_chart", False)

        chart_data = None
        if has_chart and "chart_image" in result:
            chart_data = result["chart_image"]
            message_data["chart_image"] = chart_data

        # 添加圖表標記
        message_data["has_chart"] = has_chart

        # 處理數據表格
        dataframe = result.get("dataframe")
        if dataframe is not None:
            message_data["dataframe"] = dataframe

        st.session_state.messages.append(message_data)

        # 顯示助理回應
        logger.info(f"assistant-message: {answer}")
        with st.chat_message("assistant"):
            st.markdown(answer)

        # 如果有圖表，使用st.image顯示它
        if has_chart and chart_data is not None:
            try:
                st.image(
                    chart_data,
                    caption=f"{result.get('trend_direction', '房價')}趨勢圖",
                    use_container_width=True,
                )
            except Exception as img_error:
                logger.error(f"顯示圖表時出錯: {img_error}")
                st.error(f"無法顯示趨勢圖: {str(img_error)}")

        # 如果有數據表格，顯示它
        if dataframe is not None and not dataframe.empty:
            st.dataframe(dataframe, use_container_width=True)
    else:
        answer = result["result"] if "result" in result else "抱歉，查詢處理失敗。"
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)


########################
### 3. WEB AGENT 部分 ###
########################


# 處理網頁搜尋查詢
async def handle_web_agent_query(user_question, model_name):
    """處理網頁搜尋代理的查詢"""
    logger.info(f"處理網頁搜尋查詢: '{user_question}'")

    # 使用新的網頁搜尋代理
    web_result = await process_web_query(user_question, model_name, scrape_results=True)

    return web_result


# 顯示網頁搜尋結果
def render_web_agent_result(web_result, memory, user_question):
    """渲染網頁搜尋代理的結果"""
    if web_result["success"]:
        # 保存爬取到的房產數據到session state
        if "data" in web_result and web_result["data"]:
            st.session_state.property_data = web_result["data"]
        else:
            st.session_state.property_data = None

        # 準備回應
        explanation = web_result.get("explanation", "")
        properties_count = len(web_result["data"]) if web_result.get("data") else 0

        if properties_count > 0:
            answer = f"已為您搜尋房產信息，找到 {properties_count} 筆符合條件的房產：\n\n{explanation}"
        else:
            answer = f"已為您搜尋房產信息：\n\n{explanation}\n\n但沒有找到完全符合條件的房產。"

        result = {
            "success": True,
            "result": answer,
        }

        # 記錄到記憶體
        if memory is not None:
            memory.chat_memory.add_user_message(user_question)
            memory.chat_memory.add_ai_message(result["result"])

        # 將回應添加到對話歷史
        st.session_state.messages.append({"role": "assistant", "content": answer})

        # 顯示助理回應
        with st.chat_message("assistant"):
            st.markdown(answer)

        # 顯示房產列表
        render_property_listings()

        # 刷新頁面以確保所有內容正確顯示
        st.rerun()
    else:
        error_msg = f"抱歉，無法解析您的搜尋請求：{web_result.get('error', '未知錯誤')}"
        # 清空房產數據
        st.session_state.property_data = None

        # 將錯誤回應添加到對話歷史
        st.session_state.messages.append({"role": "assistant", "content": error_msg})

        # 顯示錯誤回應
        with st.chat_message("assistant"):
            st.markdown(error_msg)


# 顯示房產列表
def render_property_listings():
    """渲染房產列表"""
    if (
        st.session_state.property_data is not None
        and len(st.session_state.property_data) > 0
    ):
        st.header(f"找到 {len(st.session_state.property_data)} 筆房產資訊")

        # 遍歷房產數據並顯示
        for property_item in st.session_state.property_data:
            with st.container():
                # 創建一個卡片樣式的容器
                with st.expander(
                    property_item.get("property_name", "未知"), expanded=True
                ):
                    # 使用兩列佈局 - 圖片和資訊
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        # 處理圖片URL
                        image_url = property_item.get("image_url", "")
                        if image_url:
                            st.image(image_url, use_container_width=True)

                    with col2:
                        # 顯示主要信息
                        if property_item.get("community_name"):
                            st.markdown(
                                f"**社區**: {property_item.get('community_name')}"
                            )

                        st.markdown(
                            f"**位置**: {property_item.get('location', '未知地點')}"
                        )

                        # 價格信息
                        price_html = f"**價格**: <span style='color:#e63946; font-weight:bold; font-size:1.2em;'>{property_item.get('current_price', '')} {property_item.get('price_unit', '萬')}</span>"
                        if property_item.get("original_price"):
                            price_html += f" <small><s>{property_item.get('original_price', '')}</s></small>"
                        st.markdown(price_html, unsafe_allow_html=True)

                        if property_item.get("discount_percentage"):
                            st.markdown(
                                f"**降價**: {property_item.get('discount_percentage')}"
                            )

                        # 基本信息
                        st.markdown(f"**格局**: {property_item.get('layout', '未知')}")
                        st.markdown(f"**坪數**: {property_item.get('total_size', '')}")
                        st.markdown(f"**樓層**: {property_item.get('floor', '')}")
                        st.markdown(
                            f"**屋齡**: {property_item.get('property_age', '')} | **類型**: {property_item.get('property_type', '')}"
                        )

                    # 底部顯示特徵標籤和關注人數
                    st.markdown("---")

                    # 處理特徵去重複
                    features_list = []
                    if property_item.get("features"):
                        features_list = [
                            f.get("feature", "")
                            for f in property_item.get("features", [])
                            if f.get("feature")
                        ]
                        # 移除重複的特徵
                        features_list = list(dict.fromkeys(features_list))

                    # 使用單獨的列顯示特徵
                    if features_list:
                        feature_cols = st.columns(min(3, len(features_list)))
                        for i, feature in enumerate(features_list[:3]):
                            feature_cols[i].markdown(f"🏷️ {feature}")

                    # 顯示關注人數
                    st.markdown(
                        f"👀 已有 **{property_item.get('interest_count', '0')}** 人關注"
                    )


################################
### MAIN APPLICATION WORKFLOW ###
################################


def main():
    # 渲染側邊欄
    render_sidebar()

    # 主界面標題
    st.title("🏠 台灣房地產資料助理")
    st.markdown("**請在下方輸入您的房地產相關問題，我們將為您提供專業的分析與解答。**")

    # 顯示當前選擇的代理
    st.info(f"當前使用: {st.session_state.selected_agent}")

    # 顯示房產列表 (如果有)
    if st.session_state.selected_agent == "房產搜尋助理":
        render_property_listings()

    # 顯示聊天歷史
    render_chat_history()

    # 使用者輸入
    user_question = st.chat_input("💬 請輸入您的房地產問題...")

    # 處理使用者輸入
    if user_question:
        # 顯示使用者訊息
        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        # 處理AI回應
        with st.spinner("AI分析中，請稍候..."):
            try:
                # 獲取選擇的模型和記憶體
                model_name = st.session_state.selected_model
                memory = st.session_state.memory
                logger.info(f"使用模型: {model_name}")

                # 根據選擇的代理類型處理查詢
                if st.session_state.selected_agent == "資料分析助理":
                    # 處理資料分析查詢
                    result = handle_data_agent_query(user_question, model_name, memory)
                    # 顯示資料分析結果
                    render_data_agent_result(result)
                else:
                    # 處理異步操作
                    try:
                        # 檢查當前線程是否有事件循環
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        # 如果沒有事件循環，則創建一個新的
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    # 處理網頁搜尋查詢
                    web_result = asyncio.run(
                        handle_web_agent_query(user_question, model_name)
                    )
                    # 顯示網頁搜尋結果
                    render_web_agent_result(web_result, memory, user_question)

            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                answer = f"處理問題時發生錯誤: {str(e)}"
                logger.error(f"處理查詢時出錯: {error_details}")
                st.error(f"發生錯誤: {str(e)}")

                # 儲存錯誤回應
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )
                with st.chat_message("assistant"):
                    st.markdown(answer)

    # 清空對話按鈕
    if st.button("清空對話"):
        st.session_state.messages = []
        st.session_state.memory = CONVERSATION_MEMORY
        st.session_state.session_id = f"thread-{os.urandom(4).hex()}"
        st.session_state.property_data = None
        st.rerun()


# 執行主函數
if __name__ == "__main__":
    main()
