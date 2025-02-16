from flask import current_app
from standard_pipelines.api.services import BaseAPIManager
from dialpad import DialpadClient
from datetime import datetime


class DialpadAPIManager(BaseAPIManager):
    def __init__(self, api_config: dict) -> None:
        super().__init__(api_config)
        self.dialpad_client = DialpadClient(api_config["api_key"])

    @property
    def required_config(self) -> list[str]:
        return ["api_key"]

    #============ API Functions =============#
    def get_transcript(self, call_id: str):
        try:
            transcript = self.dialpad_client.transcript.get(call_id=call_id)
            lines = transcript.get("lines")
            if not lines:
                current_app.logger.error(f"No transcript found for call_id: {call_id}")
                return {"error": "No transcript found"}

            only_transcripts = [entry for entry in lines if entry['type'].lower() == 'transcript']
            formatted_transcript = self._format_transcript(only_transcripts)
            return formatted_transcript

        except Exception as e:
            current_app.logger.error(f"Error fetching transcripts: {e}")
            return {"error": str(e)}
    
    #============ Helper Functions =============#
    def _format_transcript(self, transcript_entries: list[dict]) -> str:
        formatted_lines = []
        for entry in transcript_entries:
            time_str = entry.get('time', '')
            try:
                time_obj = datetime.fromisoformat(time_str)
                timestamp = time_obj.strftime("[%H:%M:%S]")
            except ValueError:
                timestamp = "[Unknown Time]"

            speaker = entry.get('name', 'Unknown Speaker')
            content = entry.get('content', 'N/A')

            formatted_line = f"{timestamp} {speaker}: {content}"
            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)