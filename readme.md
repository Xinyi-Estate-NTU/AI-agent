# Xinyi Estate Project

## Project Structure

- **app.py**: Main Streamlit application entry point, handling user interface and interaction logic
- **data_agent/**: Core data processing and analysis modules
  - **api.py**: Unified API interface for data operations
  - **config.py**: System configuration including model settings and data constants
  - **data_analysis.py**: Data analysis and visualization functions
  - **data_loader.py**: Data loading with intelligent caching mechanism
  - **query_processor.py**: Natural language query processing
  - **utils.py**: Utility functions and helpers
- **web_agent/**: Web scraping and processing modules
  - **api.py**: Web scraping API interface
  - **config.py**: Web scraping configuration
  - **processor.py**: Web content processing
  - **scraper.py**: Web scraping implementation
  - **url_builder.py**: URL construction utilities
  - **utils.py**: Web-related utility functions
- **data/**: Real estate transaction data
  - Raw data files for Taipei (TP) and New Taipei (NTP) cities
  - Pre-construction sales, rentals, and sales data
  - Processed data files
  - Supporting documentation (921_law.md)

## Component Relationships

```bash
app.py (Streamlit Interface)
|
|--> data_agent/ (Data Processing)
|   |--> api.py
|   |--> query_processor.py
|   |--> data_analysis.py
|   |--> data_loader.py
|   |--> data/ (Raw & Processed Data)
|
|--> web_agent/ (Web Scraping)
|   |--> api.py
|   |--> scraper.py
|   |--> processor.py
|
|--> agents/ (Additional Agents)
    |--> graph.py
```

## Required Packages

```bash
pip install streamlit pandas langchain langchain-groq langchain-experimental matplotlib python-dotenv langsmith docx2txt PyPDF2 psutil
```

## Environment Setup

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Configure API Keys:
   - **Groq API**:
     1. Visit Groq Cloud and create an account
     2. Generate API key from dashboard
     3. Add to .env: `GROQ_API_KEY=your_key_here`
   
   - **LangSmith API**:
     1. Create LangSmith account
     2. Get API key from settings
     3. Create or select project
     4. Add to .env:
        ```
        LANGSMITH_API_KEY=your_key_here
        LANGSMITH_PROJECT=your_project_name
        ```

## Running the Application

```bash
streamlit run src/app.py
```

## Support

For any questions or issues, please open a GitHub issue.