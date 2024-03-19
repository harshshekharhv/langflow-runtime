from langchain.agents import AgentExecutor, create_structured_chat_agent
#from langchain_wrapper import SeldonCore
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langflow import CustomComponent
from langchain.tools import BaseTool

from custom_components.custom_langchain_components.dpn_bucket_tool import sys_msg, human_msg, ListDpnBucketContentTool, SqlTool
from langchain.llms import BaseLLM
import langchain.hub as hub
from typing import Union, Optional, List
from langflow.field_typing import BaseLanguageModel, BaseMemory, Chain
# special tokens used by llama 2 chat

class CustomAgentComponent(CustomComponent):
    display_name: str = "DPN Agent Initializer"
    description: str = "Create any custom component you want!"

    def build_config(self):
        return {
                "llm": { "required": True },
                "memory": {
                        "display_name": "Memory",
                        "info": "Memory to load context from. If none is provided, a ConversationBufferMemory will be used.",
                },
                "tools": {
                        "required": True,
                        "info": "Tools to be used by the agent."
                }
            }


    def build(self, 
          llm: BaseLLM,
          tools: List[BaseTool],
          memory: Optional[BaseMemory] = None,
        ) -> Union[AgentExecutor, None] :
        
        # tools = [ListDpnBucketContentTool(), SqlTool()]
        
        prompt = hub.pull("coty/react-chat-json-v1")
        print(f"Prompt:\n {prompt}\n")

        prompt.messages[0].prompt.template = sys_msg
        prompt.messages[1].prompt.template = human_msg
        # conversational_memory = ConversationBufferWindowMemory(
        #         memory_key='history',
        #         k=5,
        #         return_messages=True,
        #         # input_key="input"
        # )

        agent = create_structured_chat_agent(llm, tools, prompt=prompt)

        executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True, memory=memory)
        executor.input_keys.append('chat_history')
        return executor