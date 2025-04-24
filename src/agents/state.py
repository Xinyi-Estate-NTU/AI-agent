# agents/state.py
from typing import List, Dict, Any, Optional, TypedDict, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class TimeRange(BaseModel):
    """Time range for data queries."""

    start_year: int = Field(..., description="Start year of the range")
    end_year: int = Field(..., description="End year of the range")
    description: str = Field(..., description="Human-readable description of the range")


class Classification(BaseModel):
    """Classification of the query by the router node."""

    query_type: Literal["data_analysis", "web_search", "both", "general"] = Field(
        ..., description="Type of query"
    )
    reasoning: str = Field(..., description="Reasoning behind the classification")
    city: Optional[str] = Field(None, description="City mentioned in the query")
    district: Optional[str] = Field(None, description="District mentioned in the query")
    time_range: Optional[TimeRange] = Field(
        None, description="Time range for data analysis"
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="Additional filters for data analysis"
    )


class ToolResult(BaseModel):
    """Result from a tool execution."""

    success: bool = Field(..., description="Whether the tool execution was successful")
    message: Optional[str] = Field(None, description="Message about the tool execution")
    result: str = Field(..., description="Human-readable result from the tool")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the result was generated"
    )


class Message(BaseModel):
    """Message in the conversation."""

    role: Literal["human", "assistant", "system", "tool"] = Field(
        ..., description="Role of the message sender"
    )
    content: str = Field(..., description="Content of the message")
    name: Optional[str] = Field(
        None, description="Name of the tool (for tool messages)"
    )
    tool_call_id: Optional[str] = Field(
        None, description="ID of the tool call (for tool messages)"
    )


# Define state type for the LangGraph
class AgentState(BaseModel):
    """State model for the LangGraph agent."""

    # Core state elements
    user_input: str
    tools_to_use: List[str] = Field(default_factory=list)
    final_response: Optional[str] = None

    # Router/classification state
    classification: Optional[Classification] = None
    query_type: Optional[str] = None

    # Tool results
    data_result: Optional[Dict[str, Any]] = None
    web_result: Optional[Dict[str, Any]] = None

    # For tracking execution
    error: Optional[str] = None
    has_chart: bool = Field(default=False)
    chart_image: Optional[str] = None
    dataframe: Optional[Any] = None

    # Thread management
    thread_id: Optional[str] = None
    model_name: Optional[str] = None
    timestamp: Optional[float] = None

    # For conversation history
    messages: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


# Define input and output schemas
class GraphInputSchema(BaseModel):
    """Schema for graph input."""

    user_input: str = Field(..., description="The user's input query")
    thread_id: Optional[str] = Field(
        None, description="Thread ID for conversation persistence"
    )
    model_name: Optional[str] = Field(None, description="Model to use for processing")


class GraphOutputSchema(BaseModel):
    """Schema for graph output."""

    final_response: str = Field(..., description="The final response to the user")
    has_chart: bool = Field(False, description="Whether the response includes a chart")
    chart_image: Optional[str] = Field(
        None, description="Base64-encoded chart image if available"
    )
    thread_id: str = Field(..., description="Thread ID for the conversation")
