from ..services import BaseManualAPIManager
from requests.auth import AuthBase
from standard_pipelines.data_flow.exceptions import APIError
import typing as t
from abc import ABCMeta
from flask import current_app

class FirefliesAPIManager(BaseManualAPIManager, metaclass=ABCMeta):
    class FirefliesAuthenticator(AuthBase):
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        def __call__(self, r):
            r.headers["Authorization"] = f"Bearer {self.api_key}"
            return r
    
    def authenticator(self) -> AuthBase:
        return self.FirefliesAuthenticator(self.api_config["api_key"])

    @property
    def required_config(self) -> list[str]:
        return ["api_key"]

    def api_url(self, api_context: t.Optional[dict] = None) -> str:
        return "https://api.fireflies.ai/graphql"

    def https_payload(self, api_context: t.Optional[dict] = None) -> t.Optional[dict]:
        query_string = """
        query Transcript($transcriptId: String!) {
            transcript(id: $transcriptId) {
                id
                dateString
                privacy
                speakers {
                    id
                    name
                }
                sentences {
                    index
                    speaker_name
                    speaker_id
                    text
                    raw_text
                    start_time
                    end_time
                }
                title
                host_email
                organizer_email
                calendar_id
                date
                transcript_url
                duration
                meeting_attendees {
                    displayName
                    email
                    phoneNumber
                    name
                    location
                }
                cal_id
                calendar_type
                meeting_link
            }
        }
        """
        return {
            "query": query_string,
            "variables": {"transcriptId": api_context["transcript_id"]}
        }
    
    def https_headers(self, api_context: t.Optional[dict] = None) -> t.Optional[dict]:
        return {
            "Content-Type": "application/json",
        }

    def transcript(self, transcript_id: str) -> tuple[str, list[str], list[str]]:
        """
        Returns a tuple of a prettified transcript suitable for input into an
        AI prompt, a list of emails present in the transcript, and a list of
        names present in the transcript.
        """
        transcript_object = self.get_response({"transcript_id": transcript_id}).json()
        pretty_transcript = self._pretty_transcript_from_transcript_object(transcript_object)
        emails = self._emails_from_transcript_object(transcript_object)
        names = self._names_from_transcript_object(transcript_object)
        return pretty_transcript, emails, names

    def _emails_from_transcript_object(self, transcript: dict) -> list[str]:
        transcript_data = transcript.get("data", {}).get("transcript", {})
        meeting_attendees = transcript_data.get("meeting_attendees")
        return meeting_attendees if meeting_attendees else []

    def _names_from_transcript_object(self, transcript: dict) -> list[str]:
        transcript_data = transcript.get("data", {}).get("transcript", {})
        try:
            return [speaker.get("name", "") for speaker in transcript_data.get("speakers", [])]
        except Exception as e:
            current_app.logger.error(f"Error getting names from transcript object: {e}")
            return ["Unknown Speaker"]

    def _pretty_transcript_from_transcript_object(self, transcript: dict) -> str:
        if "errors" in transcript:
            warning_msg = f"GraphQL Errors: {transcript['errors']}"
            current_app.logger.warning(warning_msg)
        
        transcript_data = transcript.get("data", {}).get("transcript", {})
        if not transcript_data:
            warning_msg = "No transcript data found."
            current_app.logger.warning(warning_msg)
        sentences = transcript_data.get('sentences', [])
        if not sentences:
            warning_msg = "No sentences found."
            current_app.logger.warning(warning_msg)

        formatted_lines = []
        for sentence in sentences:
            minutes = int(sentence.get("start_time", 0)) // 60
            seconds = int(sentence.get("start_time", 0)) % 60
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            speaker = sentence.get("speaker_name", "Unknown Speaker")
            text = sentence.get("raw_text", "")
            formatted_line = f"{timestamp} {speaker}: {text}"
            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)
