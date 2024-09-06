import asyncio
import json
import re

from langchain_community.chat_models import ChatLiteLLM
from langchain_openai import ChatOpenAI

from server.agents import BlackSpaceAI

class BlackSpaceAPI:
    def __init__(
        self,
        config_path: str,
        verbose: bool = True,
        model_name: str = "gpt-3.5-turbo",
        product_catalog: str = "",
        use_tools=True,
        conversation_history = []
    ):
        self.config_path = config_path
        self.verbose = verbose
        self.model_name = model_name
        self.llm = ChatLiteLLM(temperature=0.2, model=model_name)
        self.product_catalog = product_catalog
        self.conversation_history = conversation_history
        self.use_tools = use_tools
        self.sales_agent = self.initialize_agent()

    def initialize_agent(self):
        config = {"verbose": self.verbose}
        config.update(self.config_path)

        if self.use_tools:
            print("USING TOOLS")
            config.update(
                {
                    "use_tools": True,
                    "product_catalog": self.product_catalog,
                    "salesperson_name": "Sidhant Goswami"
                    if not self.config_path
                    else config.get("salesperson_name", "Sidhant Goswami"),
                }
            )

        sales_agent = BlackSpaceAI.from_llm(self.llm, **config)

        print(f"BlackSpaceAI use_tools: {sales_agent.use_tools}")
        sales_agent.seed_agent(self.conversation_history)
        return sales_agent

    async def do(self, human_input=None):

        if human_input is not None:
            self.sales_agent.human_step(human_input)

        ai_log = await self.sales_agent.astep(stream=False)
        await self.sales_agent.adetermine_conversation_stage()
        if self.verbose:
            print("=" * 10)
            print(f"AI LOG {ai_log}")
            
        if (
            self.sales_agent.conversation_history
            and "<END_OF_CALL>" in self.sales_agent.conversation_history[-1]
        ):
            print("Sales Agent determined it is time to end the conversation.")

            self.sales_agent.conversation_history[
                -1
            ] = self.sales_agent.conversation_history[-1].replace("<END_OF_CALL>", "")

        reply = (
            self.sales_agent.conversation_history[-1]
            if self.sales_agent.conversation_history
            else ""
        )

        if (
            self.use_tools and 
            "intermediate_steps" in ai_log and 
            len(ai_log["intermediate_steps"]) > 0
        ):
            
            try:
                res_str = ai_log["intermediate_steps"][0]
                print("RES STR: ", res_str)
                agent_action = res_str[0]
                tool, tool_input, log = (
                    agent_action.tool,
                    agent_action.tool_input,
                    agent_action.log,
                )
                actions = re.search(r"Action: (.*?)[\n]*Action Input: (.*)", log)
                action_input = actions.group(2)
                action_output =  res_str[1]
                if tool_input == action_input:
                    action_input=""
                    action_output = action_output.replace("<web_search>", "<a href='https://www.google.com/search?q=")
                    action_output = action_output.replace("</web_search>", "' target='_blank' rel='noopener noreferrer'>")
            except Exception as e:
                print("ERROR: ", e)
                tool, tool_input, action, action_input, action_output = (
                    "",
                    "",
                    "",
                    "",
                    "",
                )
        else:
            tool, tool_input, action, action_input, action_output = "", "", "", "", ""

        print(reply)

        payload = {
            "bot_name": reply.split(": ")[0],
            "response": ": ".join(reply.split(": ")[1:]).rstrip("<END_OF_TURN>"),
            "conversational_stage": self.sales_agent.current_conversation_stage,
            "tool": tool,
            "tool_input": tool_input,
            "action_output": action_output,
            "action_input": action_input,
            "model_name": self.model_name,
            "reply" : ": ".join(reply.split(": ")[1:])
        }
        return payload

    async def do_stream(self, conversation_history: [str], human_input=None):

        self.sales_agent.seed_agent(conversation_history)

        if human_input is not None:
            self.sales_agent.human_step(human_input)

        stream_gen = self.sales_agent.astep(stream=True)
        for model_response in stream_gen:
            for choice in model_response.choices:
                message = choice["delta"]["content"]
                if message is not None:
                    if "<END_OF_CALL>" in message:
                        print(
                            "Sales Agent determined it is time to end the conversation."
                        )
                        yield [
                            "BOT",
                            "In case you'll have any questions - just text me one more time!",
                        ]
                    yield message
                else:
                    continue
