from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from dialpad import DialpadClient



class DialpadAPIManager(BaseAPIManager):
    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.dialpad_client = DialpadClient(api_config["api_key"])

    @property
    def required_config(self) -> list[str]:
        return ["api_key"]

    def get_transcript(self, call_id: str):
        try:
            transcript = self.dialpad_client.transcript.get(call_id=call_id)
            lines = transcript.get("lines")
            if not lines:
                current_app.logger.error(f"No transcript found for call_id: {call_id}")
                return {"error": "No transcript found"}

            only_transcripts = [entry for entry in lines if entry['type'].lower() == 'transcript']
            return {"transcript": only_transcripts}

        except Exception as e:
            current_app.logger.error(f"Error fetching transcripts: {e}")
            return {"error": str(e)}
        