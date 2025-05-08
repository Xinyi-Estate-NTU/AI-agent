# Xinyi Estate Project

A comprehensive real estate analysis and web scraping system that combines data analysis with web intelligence.

## Project Structure

### Core Components

- **app.py**: Main Streamlit application entry point, handling user interface and interaction logic

### Data Agent (`data_agent/`)
Core data processing and analysis system for real estate data:

#### Data Analysis (`data_analysis.py`)
Advanced real estate data analysis and visualization:
- `RealEstateAnalyzer` class with key methods:
  - `calculate_average_price()`: Computes average property prices with detailed statistics
  - `generate_price_trend_chart()`: Creates price trend visualizations with multiple chart types
  - `find_districts_within_budget()`: Identifies affordable districts based on budget constraints
  - `filter_data_by_attributes()`: Advanced data filtering with multiple criteria
  - `execute_pandas_agent_query()`: Natural language query processing using Pandas Agent

#### Data Loading (`data_loader.py`)
Intelligent data management with caching:
- `DataLoader` class with features:
  - Smart caching system with configurable expiry
  - Memory usage optimization
  - Support for Taipei and New Taipei city data
  - Automatic data merging and processing
  - Cache status monitoring and management

#### Query Processing (`query_processor.py`)
Natural language query handling:
- `RealEstateQueryProcessor` class:
  - `process_query()`: Main query processing pipeline
  - `handle_average_price_query()`: Price analysis queries
  - `handle_plot_query()`: Data visualization requests
  - `handle_area_search_query()`: District search based on criteria
- `LLMService` class for LLM integration

#### Utilities (`utils.py`)
Supporting functions and tools:
- Query type identification
- Natural language to structured data conversion
- Message format conversion
- Query parameter parsing
- District and city validation

### Web Agent (`web_agent/`)
Web scraping and content processing system:

- **api.py**: Web scraping API interface
  - `process_web_query()`: Async web query processing
  - Model management functions
- **config.py**: Web scraping configuration and settings
- **processor.py**: Web content processing and analysis
- **scraper.py**: Web scraping implementation
- **url_builder.py**: Smart URL construction for real estate websites
- **utils.py**: Web-related utility functions

### Data Directory (`data/`)
Contains real estate transaction data:
- Raw data files for Taipei (TP) and New Taipei (NTP) cities
- Pre-construction sales, rentals, and sales data
- Processed data files
- Supporting documentation (921_law.md)

## System Architecture

```bash
app.py (Streamlit Interface)
|
|--> data_agent/ (Data Processing & Analysis)
|   |--> data_analysis.py (Analysis Engine)
|   |   |--> RealEstateAnalyzer
|   |   |   |--> Price Analysis
|   |   |   |--> Trend Visualization
|   |   |   |--> District Search
|   |   |
|   |--> data_loader.py (Data Management)
|   |   |--> DataLoader
|   |   |   |--> Smart Caching
|   |   |   |--> Memory Optimization
|   |   |
|   |--> query_processor.py (Query Engine)
|   |   |--> RealEstateQueryProcessor
|   |   |   |--> Query Processing
|   |   |   |--> LLM Integration
|   |   |
|   |--> utils.py (Support Tools)
|   |   |--> Query Parsing
|   |   |--> Data Validation
|   |   |--> Format Conversion
|
|--> web_agent/ (Web Intelligence)
|   |--> api.py (Web API)
|   |   |--> process_web_query()
|   |--> scraper.py (Web Scraping)
|   |--> processor.py (Content Processing)
|   |--> url_builder.py (URL Management)
```

## Application Structure (`app.py`)

### Main Components
- **User Interface**
  - Streamlit-based interactive interface
  - Sidebar for model and agent selection
  - Chat-style interaction
  - Property listing visualization

### Agent Selection
- **Data Analysis Agent**: For real estate data analysis
  - Price trend analysis
  - District comparisons
  - Budget-based recommendations
  
- **Web Search Agent**: For real-time property listings
  - Property search and filtering
  - Real-time web scraping
  - Structured data presentation

### Key Features
- **Chat Interface**
  - Message history management
  - Interactive chat input
  - Support for both text and visualizations
  - Memory management for conversation context

- **Property Display**
  - Card-based property listings
  - Image and detail presentation
  - Feature tag visualization
  - Price and discount highlighting

- **Session Management**
  - Model selection persistence
  - Agent type switching
  - Conversation history
  - Property data caching

## URL Structure Rules

### Base Format
```bash
https://www.sinyi.com.tw/buy/list/[parameters]/[city]/[district]/[sort]/[page]
```

### Parameter Types
1. **Price Range**
   - `200-up-price`: Above 2 million
   - `200-down-price`: Below 2 million
   - `200-400-price`: Between 2-4 million

2. **Property Type**
   - `apartment-dalou-type`: Apartment + Building
   - `flat`: Studio
   - `townhouse-villa`: Villa/House
   - `office`: Office

3. **Area (Ping)**
   - `20-up-area`: Above 20 ping
   - `20-down-area`: Below 20 ping
   - `20-40-area`: 20-40 ping

4. **Location Codes**
   - Taipei City Districts:
     - `100`: Zhongzheng
     - `103`: Datong
     - `106`: Da'an
     [etc.]
   - New Taipei City Districts:
     - `220`: Banqiao
     - `231`: Xindian
     - `234`: Yonghe
     [etc.]

5. **Special Features**
   - Parking: 
     - `plane-auto-mix-mechanical-firstfloor-tower-other-yesparking`
     - `noparking`
   - Floor Exclusion: `4f-exclude`
   - Amenity Tags:
     - `4`: Balcony
     - `9`: Swimming Pool
     - `8`: Gym
     - `17`: Near MRT
     - `19`: Near Park
     - `16`: Near School

### Example URLs
```
# Complex Search
/buy/list/200-up-price/apartment-dalou-type/yesparking/10-up-area/2-up-year/1-2-room/4f-exclude/16-19-9-8-tags/捷運-keyword/1-up-floor/NewTaipei-city/231-zip/default-desc/1

# Simple Search
/buy/list/apartment-dalou-type/4f-exclude/19-9-8-tags/捷運-keyword/1-up-floor/NewTaipei-city/231-zip/default-desc/1
```

## LLM Integration

### Query Processing
- Natural language understanding for property searches
- Parameter extraction from user queries
- Structured data conversion
- Multi-parameter search support

### Response Generation
- Context-aware responses
- Property listing summaries
- Search explanation generation
- Error handling and fallback mechanisms

## Key Features

### Data Agent
- **Advanced Data Analysis**
  - Comprehensive price analysis with detailed statistics
  - Multiple visualization types (trend, bar charts)
  - District-based price comparisons
  - Budget-based area recommendations

- **Intelligent Data Management**
  - Smart caching system with configurable expiry
  - Memory usage optimization
  - Automatic data merging and processing
  - Cache status monitoring

- **Natural Language Processing**
  - Complex query understanding
  - Multiple query types support
  - Structured data extraction
  - LLM integration for query parsing

- **Performance Optimization**
  - Efficient data loading and caching
  - Memory usage monitoring
  - Query result caching
  - Batch processing support

### Web Agent
- Asynchronous web scraping
- Smart URL construction for real estate websites
- Content processing and analysis
- Integration with LLM for query understanding
- Error handling and logging

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