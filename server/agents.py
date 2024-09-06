from copy import deepcopy
from typing import Any, Callable, Dict, List, Union

from langchain.agents import (
    AgentExecutor,
    LLMSingleActionAgent,
    create_openai_tools_agent,
)
from langchain.chains import LLMChain, RetrievalQA
from langchain.chains.base import Chain
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.agents import (
    _convert_agent_action_to_messages,
    _convert_agent_observation_to_messages,
)
from langchain_core.language_models.llms import create_base_retry_decorator
from litellm import acompletion
from pydantic import Field

from server.chains import SalesConversationChain, StageAnalyzerChain
from server.custom_invoke import CustomAgentExecutor
from server.logger import time_logger
from server.parsers import SalesConvoOutputParser
from server.prompts import SALES_AGENT_TOOLS_PROMPT
from server.stages import CONVERSATION_STAGES
from server.templates import CustomPromptTemplateForTools
from server.tools import get_tools, setup_knowledge_base


def _create_retry_decorator(llm: Any) -> Callable[[Any], Any]:
    import openai

    errors = [
        openai.Timeout,
        openai.APIError,
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.APIStatusError,
    ]
    return create_base_retry_decorator(error_types=errors, max_retries=llm.max_retries)


class BlackSpaceAI(Chain):

    conversation_history: List[str] = []
    conversation_stage_id: str = "1"
    current_conversation_stage: str = CONVERSATION_STAGES.get("1")
    stage_analyzer_chain: StageAnalyzerChain = Field(...)
    sales_agent_executor: Union[CustomAgentExecutor, None] = Field(...)
    knowledge_base: Union[RetrievalQA, None] = Field(...)
    sales_conversation_utterance_chain: SalesConversationChain = Field(...)
    conversation_stage_dict: Dict = CONVERSATION_STAGES

    model_name: str = "gpt-3.5-turbo-0613"

    use_tools: bool = False
    salesperson_name: str = ""
    salesperson_role: str = ""
    company_name: str = ""
    company_business: str = ""
    company_values: str = ""
    conversation_purpose: str = ""
    conversation_type: str = ""

    def retrieve_conversation_stage(self, key):

        return self.conversation_stage_dict.get(key, "1")

    @property
    def input_keys(self) -> List[str]:

        return []

    @property
    def output_keys(self) -> List[str]:

        return []

    @time_logger
    def seed_agent(self, conversation_history):

        self.current_conversation_stage = self.retrieve_conversation_stage("1")
        self.conversation_history = conversation_history

    @time_logger
    def determine_conversation_stage(self):

        print(f"Conversation Stage ID before analysis: {self.conversation_stage_id}")
        print("Conversation history:")
        print(self.conversation_history)
        stage_analyzer_output = self.stage_analyzer_chain.invoke(
            input={
                "conversation_history": "\n".join(self.conversation_history).rstrip(
                    "\n"
                ),
                "conversation_stage_id": self.conversation_stage_id,
                "conversation_stages": "\n".join(
                    [
                        str(key) + ": " + str(value)
                        for key, value in CONVERSATION_STAGES.items()
                    ]
                ),
            },
            return_only_outputs=False,
        )
        print("Stage analyzer output")
        print(stage_analyzer_output)
        self.conversation_stage_id = stage_analyzer_output.get("text")

        self.current_conversation_stage = self.retrieve_conversation_stage(
            self.conversation_stage_id
        )

        print(f"Conversation Stage: {self.current_conversation_stage}")

    @time_logger
    async def adetermine_conversation_stage(self):

        print(f"Conversation Stage ID before analysis: {self.conversation_stage_id}")
        print("Conversation history:")
        print(self.conversation_history)
        stage_analyzer_output = await self.stage_analyzer_chain.ainvoke(
            input={
                "conversation_history": "\n".join(self.conversation_history).rstrip(
                    "\n"
                ),
                "conversation_stage_id": self.conversation_stage_id,
                "conversation_stages": "\n".join(
                    [
                        str(key) + ": " + str(value)
                        for key, value in CONVERSATION_STAGES.items()
                    ]
                ),
            },
            return_only_outputs=False,
        )
        print("Stage analyzer output")
        print(stage_analyzer_output)
        self.conversation_stage_id = stage_analyzer_output.get("text")

        self.current_conversation_stage = self.retrieve_conversation_stage(
            self.conversation_stage_id
        )

        print(f"Conversation Stage: {self.current_conversation_stage}")

    def human_step(self, human_input):

        human_input = "User: " + human_input + " <END_OF_TURN>"
        self.conversation_history.append(human_input)

    @time_logger
    def step(self, stream: bool = False):

        if not stream:
            return self._call(inputs={})
        else:
            return self._streaming_generator()

    @time_logger
    async def astep(self, stream: bool = False):

        if not stream:
            return await self.acall(inputs={})
        else:
            return await self._astreaming_generator()

    @time_logger
    async def acall(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    
        inputs = {
            "input": "",
            "conversation_stage": self.current_conversation_stage,
            "conversation_history": "\n".join(self.conversation_history),
            "salesperson_name": self.salesperson_name,
            "salesperson_role": self.salesperson_role,
            "company_name": self.company_name,
            "company_business": self.company_business,
            "company_values": self.company_values,
            "conversation_purpose": self.conversation_purpose,
            "conversation_type": self.conversation_type,
        }

        # Generate agent's utterance
        if self.use_tools:
            ai_message = await self.sales_agent_executor.ainvoke(inputs)
            output = ai_message["output"]
        else:
            ai_message = await self.sales_conversation_utterance_chain.ainvoke(
                inputs, return_intermediate_steps=True
            )
            output = ai_message["text"]

        # Add agent's response to conversation history
        agent_name = self.salesperson_name
        output = agent_name + ": " + output
        if "<END_OF_TURN>" not in output:
            output += " <END_OF_TURN>"
        self.conversation_history.append(output)

        if self.verbose:
            tool_status = "USE TOOLS INVOKE:" if self.use_tools else "WITHOUT TOOLS:"
            print(f"{tool_status}\n#\n#\n#\n#\n------------------")
            print(f"AI Message: {ai_message}")
            print()
            print(f"Output: {output.replace('<END_OF_TURN>', '')}")

        return ai_message

    @time_logger
    def _prep_messages(self):

        prompt = self.sales_conversation_utterance_chain.prep_prompts(
            [
                dict(
                    conversation_stage=self.current_conversation_stage,
                    conversation_history="\n".join(self.conversation_history),
                    salesperson_name=self.salesperson_name,
                    salesperson_role=self.salesperson_role,
                    company_name=self.company_name,
                    company_business=self.company_business,
                    company_values=self.company_values,
                    conversation_purpose=self.conversation_purpose,
                    conversation_type=self.conversation_type,
                )
            ]
        )

        inception_messages = prompt[0][0].to_messages()

        message_dict = {"role": "system", "content": inception_messages[0].content}

        if self.sales_conversation_utterance_chain.verbose:
            pass

        return [message_dict]

    @time_logger
    def _streaming_generator(self):

        messages = self._prep_messages()

        return self.sales_conversation_utterance_chain.llm.completion_with_retry(
            messages=messages,
            stop="<END_OF_TURN>",
            stream=True,
            model=self.model_name,
        )

    async def acompletion_with_retry(self, llm: Any, **kwargs: Any) -> Any:

        retry_decorator = _create_retry_decorator(llm)

        @retry_decorator
        async def _completion_with_retry(**kwargs: Any) -> Any:
            # Use OpenAI's async api https://github.com/openai/openai-python#async-api
            return await acompletion(**kwargs)

        return await _completion_with_retry(**kwargs)

    async def _astreaming_generator(self):

        messages = self._prep_messages()

        return await self.acompletion_with_retry(
            llm=self.sales_conversation_utterance_chain.llm,
            messages=messages,
            stop="<END_OF_TURN>",
            stream=True,
            model=self.model_name,
        )

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:

        inputs = {
            "input": "",
            "conversation_stage": self.current_conversation_stage,
            "conversation_history": "\n".join(self.conversation_history),
            "salesperson_name": self.salesperson_name,
            "salesperson_role": self.salesperson_role,
            "company_name": self.company_name,
            "company_business": self.company_business,
            "company_values": self.company_values,
            "conversation_purpose": self.conversation_purpose,
            "conversation_type": self.conversation_type,
        }


        if self.use_tools:
            ai_message = self.sales_agent_executor.invoke(inputs)
            output = ai_message["output"]
        else:
            ai_message = self.sales_conversation_utterance_chain.invoke(
                inputs, return_intermediate_steps=True
            )
            output = ai_message["text"]

        # Add agent's response to conversation history
        agent_name = self.salesperson_name
        output = agent_name + ": " + output
        if "<END_OF_TURN>" not in output:
            output += " <END_OF_TURN>"
        self.conversation_history.append(output)

        if self.verbose:
            tool_status = "USE TOOLS INVOKE:" if self.use_tools else "WITHOUT TOOLS:"
            print(f"{tool_status}\n#\n#\n#\n#\n------------------")
            print(f"AI Message: {ai_message}")
            print()
            print(f"Output: {output.replace('<END_OF_TURN>', '')}")

        return ai_message

    @classmethod
    @time_logger
    def from_llm(cls, llm: ChatLiteLLM, verbose: bool = False, **kwargs) -> "BlackSpaceAI":

        stage_analyzer_chain = StageAnalyzerChain.from_llm(llm, verbose=verbose)
        sales_conversation_utterance_chain = SalesConversationChain.from_llm(
            llm, verbose=verbose
        )

        # Handle custom prompts
        use_custom_prompt = kwargs.pop("use_custom_prompt", False)
        custom_prompt = kwargs.pop("custom_prompt", None)

        sales_conversation_utterance_chain = SalesConversationChain.from_llm(
            llm,
            verbose=verbose,
            use_custom_prompt=use_custom_prompt,
            custom_prompt=custom_prompt,
        )

        # Handle tools
        use_tools_value = kwargs.pop("use_tools", False)
        if isinstance(use_tools_value, str):
            if use_tools_value.lower() not in ["true", "false"]:
                raise ValueError("use_tools must be 'True', 'False', True, or False")
            use_tools = use_tools_value.lower() == "true"
        elif isinstance(use_tools_value, bool):
            use_tools = use_tools_value
        else:
            raise ValueError(
                "use_tools must be a boolean or a string ('True' or 'False')"
            )
        sales_agent_executor = None
        knowledge_base = None

        if use_tools:
            product_catalog = kwargs.pop("product_catalog", None)
            tools = get_tools(product_catalog)

            prompt = CustomPromptTemplateForTools(
                template=SALES_AGENT_TOOLS_PROMPT,
                tools_getter=lambda x: tools,
                input_variables=[
                    "input",
                    "intermediate_steps",
                    "salesperson_name",
                    "salesperson_role",
                    "company_name",
                    "company_business",
                    "company_values",
                    "conversation_purpose",
                    "conversation_type",
                    "conversation_history",
                ],
            )
            llm_chain = LLMChain(llm=llm, prompt=prompt, verbose=verbose)
            tool_names = [tool.name for tool in tools]
            output_parser = SalesConvoOutputParser(
                ai_prefix=kwargs.get("salesperson_name", ""), verbose=verbose
            )
            sales_agent_with_tools = LLMSingleActionAgent(
                llm_chain=llm_chain,
                output_parser=output_parser,
                stop=["\nObservation:"],
                allowed_tools=tool_names,
            )

            sales_agent_executor = CustomAgentExecutor.from_agent_and_tools(
                agent=sales_agent_with_tools,
                tools=tools,
                verbose=verbose,
                return_intermediate_steps=True,
            )

        return cls(
            stage_analyzer_chain=stage_analyzer_chain,
            sales_conversation_utterance_chain=sales_conversation_utterance_chain,
            sales_agent_executor=sales_agent_executor,
            knowledge_base=knowledge_base,
            model_name=llm.model,
            verbose=verbose,
            use_tools=use_tools,
            **kwargs,
        )
