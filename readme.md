# Announcement
- the code is all in here, for any question, open an github issue.
# 主要組件

- **app.py**: 主要的 Streamlit 應用程序入口點，處理用戶界面和交互邏輯
- **AI_agent/**: 包含所有 AI 代理和數據處理的核心模塊
  - **api.py**: 提供統一的對外接口，包括聊天處理和房地產查詢功能
  - **config.py**: 系統配置，包括模型設置、緩存配置和地理數據常量
  - **data_loader.py**: 處理數據加載，包含智能緩存機制以提高性能
  - **data_analysis.py**: 數據分析和圖表生成功能
  - **query_processor.py**: 處理用戶問題，將自然語言查詢轉換為結構化數據操作
  - **utils.py**: 輔助功能和工具函數
- **data/**: 包含房地產交易數據，如台北市和新北市的房價數據

## 組件關係

```bash
app.py (Streamlit 界面)
|
|--> AI_agent/api.py (統一 API 接口)
|
|--> AI_agent/query_processor.py (查詢處理)
| |
| |--> AI_agent/data_analysis.py (數據分析)
| |
| |--> AI_agent/data_loader.py (數據加載與緩存)
| |
| |--> data/ (原始數據)
|
|--> AI_agent/config.py (系統配置)
```

## 所需套件

```bash
pip install streamlit pandas langchain langchain-groq langchain-experimental matplotlib python-dotenv langsmith docx2txt PyPDF2 psutil
```

## 環境設置

```bash
cp .env.example .env
```

## API 設置指南

### Groq API
1. 訪問 Groq Cloud 並創建帳戶
2. 在儀表板中，找到並生成 API 密鑰
3. 將生成的 API 密鑰複製到 .env 文件中的 `GROQ_API_KEY=` 後面

### LangSmith API
1. 訪問 LangSmith 並創建帳戶
2. 進入設置頁面，獲取 API 密鑰
3. 創建一個新項目或使用現有項目
4. 將 API 密鑰複製到 .env 文件中的 `LANGSMITH_API_KEY=` 後面
5. 將項目名稱複製到 `LANGSMITH_PROJECT=` 後面

## 啟動應用

```bash
cd src
streamlit run app.py
```