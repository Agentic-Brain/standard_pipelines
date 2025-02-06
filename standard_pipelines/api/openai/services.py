from standard_pipelines.api.services import BaseAPIManager
from standard_pipelines.data_flow.exceptions import APIError


from openai import OpenAI, OpenAIError
from openai.types.chat.chat_completion import ChatCompletion


from abc import ABCMeta


class OpenAIAPIManager(BaseAPIManager, metaclass=ABCMeta):

    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.api_client = OpenAI(api_key=self.api_config["api_key"])

    @property
    def required_config(self) -> list[str]:
        return ["api_key"]

    def chat(self, prompt: str, model: str) -> ChatCompletion:
        if not prompt or not model:
            raise ValueError("Prompt and model are required.")
        try:
            return self.api_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
        except OpenAIError as e:
            error_msg = f"Error during OpenAI API call."
            raise APIError(error_msg) from e