from typing import Any, List, Sequence
from langchain.schema.messages import BaseMessage
from langchain.memory import ConversationBufferMemory
from langchain.schema.messages import HumanMessage, AIMessage, SystemMessage, FunctionMessage, ChatMessage
from pydantic.v1 import Field
import time
from custom_components.logger import setup_logger



def get_buffer_string(
    messages: Sequence[BaseMessage], human_prefix: str = "Human", ai_prefix: str = "AI", n: int = 2
) -> str:
    """Convert sequence of Messages to strings and concatenate them into one string.

    Args:
        messages: Messages to be converted to strings.
        human_prefix: The prefix to prepend to contents of HumanMessages.
        ai_prefix: THe prefix to prepend to contents of AIMessages.
        n: the number of last pair of AI and human messages

    Returns:
        A single string concatenation of all input messages.

    Example:
        .. code-block:: python

            from langchain_core import AIMessage, HumanMessage

            messages = [
                HumanMessage(content="Hi, how are you?"),
                AIMessage(content="Good, how are you?"),
            ]
            get_buffer_string(messages)
            # -> "Human: Hi, how are you?\nAI: Good, how are you?"
    """
    string_messages = []
    for m in messages[-n*2:]:
        if isinstance(m, HumanMessage):
            role = human_prefix
        elif isinstance(m, AIMessage):
            role = ai_prefix
        elif isinstance(m, SystemMessage):
            role = "System"
        elif isinstance(m, FunctionMessage):
            role = "Function"
        elif isinstance(m, ChatMessage):
            role = m.role
        else:
            raise ValueError(f"Got unsupported message type: {m}")
        message = f"{role}: {m.content}"
        if isinstance(m, AIMessage) and "function_call" in m.additional_kwargs:
            message += f"{m.additional_kwargs['function_call']}"
        string_messages.append(message)

    return "\n".join(string_messages)


class CustomBufferMemory(ConversationBufferMemory):
    """Buffer for storing conversation memory."""

    llm: str = Field(default='zephyr')
    username: str = Field(default='username_est')
    prompt_id: str = Field(default='promptid_test')
    human_prefix: str = "User" if llm == "zephyr" else "Human"
    ai_prefix: str = "Assistant" if llm == "zephyr" else "AI"
    debug: bool = Field(default=False)
    chat_history_n: int = Field(default=2)

    @property
    def buffer(self) -> Any:
        """String buffer of memory."""
        return self.buffer_as_messages if self.return_messages else self.buffer_as_str

    @property
    def buffer_as_str(self) -> str:
        """Exposes the buffer as a string in case return_messages is True."""

        self.parse_history()
        buffer_as_string = get_buffer_string(
            self.chat_memory.messages,
            human_prefix=self.human_prefix,
            ai_prefix=self.ai_prefix,
            n=self.chat_history_n
        )

        return buffer_as_string
    @property
    def buffer_as_messages(self) -> List[BaseMessage]:
        """Exposes the buffer as a list of messages in case return_messages is False."""

        self.parse_history()

        return self.chat_memory.messages

    def parse_history(self):
        """
        Modify chat_memory.messages to self.llm format and add timestamp,
        username and prompt_id to the additional_kwargs of the messages
        """

        additional_kwargs = {
            "timestamp": time.time(),
            "username": self.username, "prompt_id": self.prompt_id}

        all_messages=self.chat_memory.messages.copy()
        self.chat_memory.clear()
        for message in all_messages:
            if not message.additional_kwargs:
                message.additional_kwargs=additional_kwargs
            if self.llm == "llama2":
                if message.type == "human":
                    if "[/INST]" not in message.content:
                        message.content = f"{message.content} [/INST]"
                elif message.type == "ai":
                    if "</s><s>[INST]" not in message.content:
                        message.content = f"{message.content} </s><s>[INST]"
            self.chat_memory.add_message(message)
