"""
pip install -U langchain langgraph langchain-openai

Export your key first, e.g.:
  export OPENAI_API_KEY="..."
"""

from __future__ import annotations
from dataclasses import dataclass
import os
import json
from typing import Iterable, Optional, Sequence

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.messages import HumanMessage, ToolMessage, BaseMessage

import local_tools
from utils import DotDict, ConfigLoader


@dataclass
class TokenUsage:
    model: str
    stream_mode: str = "values"
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    events_seen: int = 0

    def update_usage(self, message: BaseMessage) -> None:
        """updates the token usage based on the message."""
        if hasattr(message, "usage_metadata"):
            usage = message.usage_metadata
            self.input_tokens += usage.get("input_tokens", 0)
            self.output_tokens += usage.get("output_tokens", 0)
            self.total_tokens += usage.get("total_tokens", 0)
        if hasattr(message, "response_metadata"):
            usage = message.response_metadata.get("token_usage", {})
            self.input_tokens += usage.get("prompt_tokens", 0)
            self.output_tokens += usage.get("completion_tokens", 0)
            self.total_tokens += usage.get("total_tokens", 0)

    def save(self, filepath: str) -> None:
        """saves the token usage to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.__dict__, f, indent=4)

    def reset(self) -> None:
        """resets the token usage."""
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.events_seen = 0


class Agent:
    def __init__(self, agent_config: DotDict):
        self.config = agent_config
        self.tools = [getattr(local_tools, tool.name)
                      for tool in self.config.local_tools
                      if tool.enabled]
        self.system_prompt = self.set_system_prompt()
        print("System Prompt:", self.system_prompt)
        self.llm = ChatOpenAI(**self.config.model.to_dict())
        self.agent = self._build_agent()
        self.token_usage = TokenUsage(self.config.model.name)

    def _build_agent(self) -> None:
        return create_agent(
            name=self.config.agent_name,
            model=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt,
            debug=self.config.debug,
        )

    def set_system_prompt(self) -> SystemMessage:
        """Builds the system prompt for the agent."""
        # the order is important for caching purposes:
        # 1. base system prompt, 2. skill, 3. content
        with open(self.config.system_prompt_file_path, "r") as f:
            system_prompt_text = f.read()
        
        system_prompt_parts = [system_prompt_text]
        if self.config.skill:
            skill_text = f"\n# Agent Specialty\n\n{self.config.skill}"
            system_prompt_parts.append(skill_text)
        if self.config.content:
            content_text = f"\n# Patient Data\n\n{self.config.content}"
            system_prompt_parts.append(content_text)
        
        combined_prompt = "".join(system_prompt_parts)
        return SystemMessage(content=combined_prompt)

    def _stream(self, content: str, session_id: str, stream_mode: str,
                metadata: dict=None) -> Iterable[dict]:
        """Streams the agent execution."""
        runnable_config = {"configurable": {"thread_id": session_id}}
        user_message = HumanMessage(content=content)
        if metadata:
            user_message.additional_kwargs = metadata
        inputs = {"messages": [user_message]}
        return self.agent.stream(
            inputs, stream_mode=stream_mode, config=runnable_config)
    
    def stream_local(self, content: str, session_id: str,
                     stream_mode: str="values",
                     metadata: dict=None, chat: bool=False,
                     first_response_file_path: Optional[str]=None) -> None:
        """Streams the agent interaction locally."""
        self.token_usage.stream_mode = stream_mode
        stream = self._stream(
            content, session_id, stream_mode=stream_mode, metadata=metadata)
        response_values = self._print_stream(stream)
        if first_response_file_path:
            with open(first_response_file_path, 'w') as f:
                f.write(response_values[-1])
        while chat:
            q = input("User: ")
            if q == "exit":
                return
            stream = self._stream(
                q, session_id, stream_mode=stream_mode, metadata=metadata)
            self._print_stream(stream)

    def _print_stream(self, stream: Iterable[dict]) -> Sequence[str]:
        """Prints the streamed responses."""
        response_values = []
        for response in stream:
            if response is None:
                continue
            
            # update the number of events seen
            self.token_usage.events_seen += 1
            
            # final_state = response
            if len(response.get("messages", [])) > 0:
                message = response["messages"][-1]
                
                # updatr token usage
                self.token_usage.update_usage(message)
                
                # print message content
                if isinstance(message, HumanMessage):
                    print("\nHuman: ", end="", flush=True)
                    response_values.append(message.content)
                elif isinstance(message, AIMessage):
                    print("\nAI: ", end="", flush=True)
                    response_values.append(message.content)
                elif isinstance(message, ToolMessage):
                    tool_name = getattr(message, 'name', 'Unknown')
                    print(f"\n[Tool: {tool_name}] ", end="", flush=True)
                    response_values.append(f"[Tool: {tool_name}]")
                
                if isinstance(message.content, str):
                    print(message.content, end="", flush=True)
                elif isinstance(message.content, list):
                    for item in message.content:
                        if isinstance(item, dict) and "text" in item:
                            print(item["text"], end="", flush=True)
                        else:
                            print(item, end="", flush=True)
                elif isinstance(message.content, dict):
                    if message.content.get("type") == "function_call":
                        print(f"Function Call: {message.content.get('name')}", end="", flush=True)
                        
        print()  # New line after the response
        return response_values


def run_agent(agent: Agent, session_id: str,
              stream_mode: str="values",
              user_query: str=None, metadata: dict=None) -> None:
    """Runs the agent with the given session ID and optional user query."""
    user_message = "start your analysis." if user_query is None else user_query
    agent.stream_local(
        content=user_message,
        session_id=session_id,
        stream_mode=stream_mode,
        metadata=metadata,
        first_response_file_path=None)
    return agent.token_usage


def prepare_agent(skill_name: str, skill_path: str,
                  agent_config: DotDict,
                  data_xml: str=None) -> Agent:
    """prepares the agent with the given skill and data."""
    agent_config.skill = load_skill(skill_name, skill_path)
    agent_config.content = data_xml
    return Agent(agent_config)


def load_skill(skill_name: str, skill_path: str) -> str:
    """Loads the skill from the skill file."""
    skill_filepath = os.path.join(skill_path, f"{skill_name}.md")
    with open(skill_filepath, 'r') as f:
        skill = f.read()
    return skill


if __name__ == "__main__":
    # get a file path to agent_config.yaml:
    AGENT_CONFIG_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "agent_config.yaml" 
    )
    config_loader = ConfigLoader(AGENT_CONFIG_PATH)
    agent = Agent(config_loader.dotdict)
    agent.stream_local(
        content="Hello, how can you assist me today?",
        session_id="local_session_1",
        first_response_file_path=None)
