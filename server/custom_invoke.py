# Corrected import statements
import inspect
from typing import Any, Dict, Optional

from langchain.agents import AgentExecutor
from langchain.callbacks.manager import CallbackManager
from langchain.chains.base import Chain
from langchain_core.load.dump import dumpd
from langchain_core.outputs import RunInfo
from langchain_core.runnables import RunnableConfig, ensure_config

class CustomAgentExecutor(AgentExecutor):
    def invoke(
        self,
        input: Dict[str, Any],
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        intermediate_steps = []

        config = ensure_config(config)
        callbacks = config.get("callbacks")
        tags = config.get("tags")
        metadata = config.get("metadata")
        run_name = config.get("run_name")
        include_run_info = kwargs.get("include_run_info", False)
        return_only_outputs = kwargs.get("return_only_outputs", False)

        inputs = self.prep_inputs(input)
        callback_manager = CallbackManager.configure(
            callbacks,
            self.callbacks,
            self.verbose,
            tags,
            self.tags,
            metadata,
            self.metadata,
        )

        new_arg_supported = inspect.signature(self._call).parameters.get("run_manager")
        run_manager = callback_manager.on_chain_start(
            dumpd(self),
            inputs,
            name=run_name,
        )

        intermediate_steps.append(
            {"event": "Chain Started", "details": "Inputs prepared"}
        )

        try:
            outputs = (
                self._call(inputs, run_manager=run_manager)
                if new_arg_supported
                else self._call(inputs)
            )

            intermediate_steps.append({"event": "Call Successful", "outputs": outputs})
        except BaseException as e:

            run_manager.on_chain_error(e)
            intermediate_steps.append({"event": "Error", "error": str(e)})
            raise e
        finally:
            run_manager.on_chain_end(outputs)

        final_outputs: Dict[str, Any] = self.prep_outputs(
            inputs, outputs, return_only_outputs
        )
        if include_run_info:
            final_outputs["run_info"] = RunInfo(run_id=run_manager.run_id)

        final_outputs["intermediate_steps"] = intermediate_steps

        return final_outputs


if __name__ == "__main__":
    agent = CustomAgentExecutor()
