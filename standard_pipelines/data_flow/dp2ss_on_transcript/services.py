from ..utils import BaseDataFlow
from .models import DP2SSOnTranscriptConfiguration
from functools import cached_property
import typing as t

from ...api.openai.services import OpenAIAPIManager
from ...api.openai.models import OpenAICredentials

from ...api.sharpspring.services import SharpSpringAPIManager
from ...api.sharpspring.models import SharpSpringCredentials

from ...api.dialpad.services import DialpadAPIManager
from ...api.dialpad.models import DialpadCredentials



class DP2SSOnTranscript(BaseDataFlow[DP2SSOnTranscriptConfiguration]):

    OPENAI_SUMMARY_MODEL = "gpt-4o"

    @classmethod
    def data_flow_name(cls) -> str:
        return "dp2ss_on_transcript"
    
    @cached_property
    def sharpspring_api_manager(self) -> SharpSpringAPIManager:
        credentials = SharpSpringCredentials.query.filter_by(client_id=self.client_id).first()
        if credentials is None:
            raise ValueError("No SharpSpring credentials found for client")
        sharpspring_config = {
            "account_id": credentials.account_id,
            "secret_key": credentials.secret_key
        }
        return SharpSpringAPIManager(sharpspring_config)

    @cached_property
    def dialpad_api_manager(self) -> DialpadAPIManager:
        credentials = DialpadCredentials.query.filter_by(client_id=self.client_id).first()
        if credentials is None:
            raise ValueError("No Dialpad credentials found for client")
        dialpad_config = {
            "api_key": credentials.dialpad_api_key
        }
        return DialpadAPIManager(dialpad_config)

    @cached_property
    def openai_api_manager(self) -> OpenAIAPIManager:
        credentials = OpenAICredentials.query.filter_by(client_id=self.client_id).first()
        if credentials is None:
            raise ValueError("No OpenAI credentials found for client")
        openai_config = {
            "api_key": credentials.openai_api_key
        }
        return OpenAIAPIManager(openai_config)
    
    
    def context_from_webhook_data(self, webhook_data: t.Any) -> t.Optional[dict]:
        pass

    def extract(self, context: t.Optional[dict] = None) -> dict:
        pass

    def transform(self, data: dict, context: t.Optional[dict] = None) -> dict:
        pass

    def load(self, data: dict, context: t.Optional[dict] = None) -> None:
        pass
