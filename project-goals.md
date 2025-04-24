# AI Agent with LangGraph Integration

## Project Goals
I wanna build an AI agent with interface, that can based on the user query to use proper tools to find the answers and generate proper response

## LangGraph Integration Plan
I want to integrate LangGraph to this project with the following workflow:

1. As usual, maintain a Streamlit interface and LangSmith for monitoring, and use GROQ free models, while still leveraging some LangChain functionality if necessary, I have `.env` file to maintain all my environment variables, so you can just directly `load_dotenv`
   ```python
   MODELS = [
       "llama3-8b-8192",
       "llama3-70b-8192",
       "llama-3.1-8b-instant",
       "llama-3.3-70b-versatile",
   ]
   ```

2. First, understand user input to determine which tools to call, sometimes calling multiple tools based on the user query/input

3. Combine tool responses and user question to generate a comprehensive answer and display it on the Streamlit interface

```bash
src/
├── graph_app.py              # Streamlit interface
├── data/                     # Data files
│   ├── NTP_Sales.csv
│   └── TP_Sales.csv
├── agents/                   # Unified agent system
│   ├── __init__.py           # Package exports
│   ├── config.py             # Configuration (models, env vars)
│   ├── state.py              # State definitions for the graph
│   ├── graph.py              # Main LangGraph definition
│   ├── nodes/                # Graph nodes
│   │   ├── __init__.py
│   │   ├── router.py         # Determines which tools to use
│   │   ├── data_tools.py     # Data analysis tools
│   │   ├── web_tools.py      # Web scraping tools
│   │   └── response.py       # Final response generation
│   └── tools/                # Underlying tool implementations
│       ├── __init__.py
│       ├── data_loader.py    # Data loading utilities
│       ├── data_analysis.py  # Data analysis functions
│       ├── web_scraper.py    # Web scraping functionality
│       └── url_builder.py    # URL construction helpers
└── utils/                    # Shared utilities
    ├── __init__.py
    └── common.py             # Common helper functions
```

- graph_app.py: Streamlit interface that handles user interaction, displays responses, and provides the UI.
- agents/graph.py: Defines the LangGraph workflow with different states and transitions.
- agents/state.py: Defines the state structure used throughout the graph, maintaining information between nodes.
- agents/nodes/router.py: Determines which tools to use based on user input, acting as the decision-making component.
- agents/nodes/data_tools.py & web_tools.py: Wrapper nodes that interface with the actual tool implementations.
- agents/nodes/response.py: Generates the final response by combining tool outputs with the original query.
- agents/tools/: Contains the actual implementations of various tools like data analysis and web scraping.