from standard_pipelines.api.services import BaseAPIManager
from standard_pipelines.data_flow.exceptions import APIError


from typing import Union, List
from openai import OpenAI, OpenAIError
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.fine_tuning import FineTuningJob
from openai.types.create_embedding_response import CreateEmbeddingResponse


from abc import ABCMeta


class OpenAIAPIManager(BaseAPIManager, metaclass=ABCMeta):

    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.api_client = OpenAI(api_key=self.api_config["api_key"])

    @property
    def required_config(self) -> list[str]:
        return ["api_key"]

    def chat(self, prompt: str, model: str) -> ChatCompletion:
        if prompt is None or model is None:
            raise ValueError("Prompt and model cannot be None.")
        if not prompt.strip() or not model.strip():
            raise ValueError("Prompt and model cannot be empty strings.")
        try:
            return self.api_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
        except OpenAIError as e:
            error_msg = f"Error during OpenAI API call: {str(e)}"
            raise APIError(error_msg) from e

    def create_fine_tuning_job(self, training_file: str, model: str) -> FineTuningJob:
        """Create a fine-tuning job."""
        try:
            return self.api_client.fine_tuning.jobs.create(
                training_file=training_file,
                model=model
            )
        except OpenAIError as e:
            error_msg = f"Error creating fine-tuning job: {str(e)}"
            raise APIError(error_msg) from e

    def list_fine_tuning_jobs(self, limit: int = 10) -> List[FineTuningJob]:
        """List fine-tuning jobs.
        
        Returns:
            List[FineTuningJob]: A list of fine-tuning jobs
        """
        try:
            return list(self.api_client.fine_tuning.jobs.list(limit=limit))
        except OpenAIError as e:
            error_msg = f"Error listing fine-tuning jobs: {str(e)}"
            raise APIError(error_msg) from e

    def get_fine_tuning_job(self, job_id: str) -> FineTuningJob:
        """Get fine-tuning job details."""
        try:
            return self.api_client.fine_tuning.jobs.retrieve(job_id)
        except OpenAIError as e:
            error_msg = f"Error retrieving fine-tuning job: {str(e)}"
            raise APIError(error_msg) from e

    def cancel_fine_tuning_job(self, job_id: str) -> FineTuningJob:
        """Cancel a fine-tuning job."""
        try:
            return self.api_client.fine_tuning.jobs.cancel(job_id)
        except OpenAIError as e:
            error_msg = f"Error canceling fine-tuning job: {str(e)}"
            raise APIError(error_msg) from e

    def create_embedding(self, input: Union[str, List[str]], model: str = "text-embedding-ada-002") -> CreateEmbeddingResponse:
        """Create embeddings for input text."""
        try:
            return self.api_client.embeddings.create(
                input=input,
                model=model
            )
        except OpenAIError as e:
            error_msg = f"Error creating embedding: {str(e)}"
            raise APIError(error_msg) from e
