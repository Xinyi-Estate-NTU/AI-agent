# agents/graph.py
from typing import Dict, Any, List, Optional, Annotated
import uuid
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint import Checkpoint
from langgraph.errors import ToolExecutionError
from langgraph.graph.message import ToolMessage, AIMessage, HumanMessage
from langgraph.pregel import Pregel
from langgraph import entrypoint, task

from .state import AgentState, GraphInputSchema, GraphOutputSchema
from .config import DEFAULT_MODEL, MODELS, MAX_RETRIES, get_model
from .nodes.router import router
from .nodes.data_tools import data_analysis_node, parse_query_parameters
from .nodes.web_tools import web_search_node
from .nodes.response import generate_response

# Load environment variables
load_dotenv()


@entrypoint
def process_query(
    query: str,
    thread_id: Optional[str] = None,
    model_name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process a user query through the LangGraph.

    Args:
        query: The user's query text
        thread_id: Optional thread ID for persistence (generated if not provided)
        model_name: Optional model name to use
        config: Additional configuration parameters

    Returns:
        Dict containing the response and metadata
    """
    # Generate a thread ID if not provided
    thread_id = thread_id or f"thread-{uuid.uuid4()}"

    # Configure the checkpointer for persistence
    checkpointer = MemorySaver(thread_id)

    # Prepare the initial state
    initial_state = AgentState(
        user_input=query,
        thread_id=thread_id,
        model_name=model_name or DEFAULT_MODEL,
        timestamp=float(time.time()),
        messages=[{"role": "human", "content": query}],
    )

    # Invoke the main workflow
    try:
        result = workflow(initial_state, checkpointer=checkpointer)

        # Return result with thread ID for persistence
        return {
            "response": result.get(
                "final_response", "Sorry, I couldn't process your query."
            ),
            "thread_id": thread_id,
            "has_chart": result.get("has_chart", False),
            "chart_image": (
                result.get("chart_image") if result.get("has_chart", False) else None
            ),
            "success": True,
        }
    except Exception as e:
        import logging

        logging.error(f"Error processing query: {str(e)}")

        return {
            "response": f"I encountered an error while processing your query. Please try again or rephrase your question.",
            "thread_id": thread_id,
            "has_chart": False,
            "chart_image": None,
            "success": False,
            "error": str(e),
        }


@task
def workflow(
    state: AgentState, checkpointer: Optional[Checkpoint] = None
) -> AgentState:
    """
    The main workflow that orchestrates the processing of a query.

    Args:
        state: The initial state
        checkpointer: Optional checkpoint manager for persistence

    Returns:
        The final state after processing
    """
    # Setup the model
    model = get_model(state.get("model_name", DEFAULT_MODEL))

    # Create the tool node for handling tool calls
    tools_node = ToolNode(tools=[data_analysis_node, web_search_node], llm=model)

    # First, determine the required tools
    state = router(state)

    # Parse query parameters if needed
    if "data_analysis" in state.get("tools_to_use", []):
        state = parse_query_parameters(state)

    # Process with the appropriate tools
    if state.get("tools_to_use"):
        # Update the messages to include tool instructions
        tools_message = f"I need to use the following tools to answer your query: {', '.join(state['tools_to_use'])}"
        state["messages"].append({"role": "assistant", "content": tools_message})

        # Execute data analysis if needed
        if "data_analysis" in state.get("tools_to_use", []):
            try:
                state = data_analysis_node(state)
            except Exception as e:
                state["error"] = f"Error in data analysis: {str(e)}"

        # Execute web search if needed
        if "web_search" in state.get("tools_to_use", []):
            try:
                state = web_search_node(state)
            except Exception as e:
                state["error"] = f"Error in web search: {str(e)}"

    # Generate the final response
    state = generate_response(state)

    # Return the final state
    return state


@entrypoint
def get_thread_history(thread_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve the history of a conversation thread.

    Args:
        thread_id: The thread ID to retrieve history for

    Returns:
        List of state snapshots representing the conversation history
    """
    # Create memory saver for the thread
    memory = MemorySaver(thread_id)

    # Retrieve all checkpoints
    checkpoints = memory.list_checkpoints()

    # Get state for each checkpoint
    history = []
    for checkpoint in checkpoints:
        try:
            state = memory.get_state(checkpoint)
            history.append(
                {
                    "checkpoint_id": checkpoint,
                    "user_input": state.get("user_input", ""),
                    "final_response": state.get("final_response", ""),
                    "has_chart": state.get("has_chart", False),
                }
            )
        except Exception:
            # Skip any checkpoints that can't be loaded
            continue

    return history
