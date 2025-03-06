from requests import Response
from standard_pipelines.api.services import BaseManualAPIManager
from flask import current_app
from requests.auth import AuthBase
from abc import ABCMeta
from typing import Optional

from standard_pipelines.data_flow.exceptions import APIError

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

    def api_url(self, api_context: Optional[dict] = None) -> str:
        return "https://api.fireflies.ai/graphql"

    def https_payload(self, api_context: Optional[dict] = None) -> Optional[dict]:
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
            "variables": {"transcriptId": api_context["transcript_id"]} # type: ignore
        }

    def https_headers(self, api_context: Optional[dict] = None) -> Optional[dict]:
        return {
            "Content-Type": "application/json",
        }

    def transcript(self, transcript_id: str) -> tuple[str, list[str], list[str], str]:
        """
        Returns a tuple of a prettified transcript suitable for input into an
        AI prompt, a list of emails present in the transcript, a list of
        names present in the transcript, and the organizer's email.
        """
        response : Response = self.get_response({"transcript_id": transcript_id})
        current_app.logger.debug(f"get_transcript: {response.status_code}")
        
        transcript_object = response.json()

        current_app.logger.debug(f"Transcript object: {transcript_object}")
        pretty_transcript = self._pretty_transcript_from_transcript_object(transcript_object)
        emails = self._emails_from_transcript_object(transcript_object)
        names = self._names_from_transcript_object(transcript_object)
        organizer_email = self._organizer_email_from_transcript_object(transcript_object)
        return pretty_transcript, emails, names, organizer_email

    def _emails_from_transcript_object(self, transcript: dict) -> list[str]:
        transcript_data: dict = transcript.get("data", {}).get("transcript", {})
        meeting_attendees: list[dict] = transcript_data.get("meeting_attendees", [])
        if not meeting_attendees:
            warning_msg = (
                "No meeting attendees found in transcript object. Emails will "
                "not be extracted."
            )
            current_app.logger.warning(warning_msg)
            return []
        
        return [attendee.get("email", "") for attendee in meeting_attendees]

    def _names_from_transcript_object(self, transcript: dict) -> list[str]:
        transcript_data: dict = transcript.get("data", {}).get("transcript", {})
        meeting_attendees: list[dict] = transcript_data.get("meeting_attendees", [])
        if not meeting_attendees:
            warning_msg = (
                "No meeting attendees found in transcript object. Names will "
                "not be extracted."
            )
            current_app.logger.warning(warning_msg)
            return []

        return [attendee.get("displayName", attendee.get("name", "")) for attendee in meeting_attendees]


    def _organizer_email_from_transcript_object(self, transcript: dict) -> str:
        transcript_data: dict = transcript.get("data", {}).get("transcript", {})
        if "organizer_email" in transcript_data:
            return transcript_data.get("organizer_email", "")
        else:
            error_msg = "Organizer email not found in transcript object."
            current_app.logger.warning(error_msg)
            return ""
    
    def _date_from_transcript_object(self, transcript: dict) -> str:
        transcript_data: dict = transcript.get("data", {}).get("transcript", {})
        if "date" in transcript_data:
            return transcript_data.get("date", "")
        else:
            error_msg = "Date not found in transcript object."
            current_app.logger.warning(error_msg)
            return ""

    def _meeting_name_from_transcript_object(self, transcript: dict) -> str:
        transcript_data: dict = transcript.get("data", {}).get("transcript", {})
        if "title" in transcript_data:
            return transcript_data.get("title", "")
        else:
            error_msg = "Meeting name not found in transcript object."
            current_app.logger.warning(error_msg)
            return ""

    def _pretty_transcript_from_transcript_object(self, transcript: dict) -> str:

        organizer_email = self._organizer_email_from_transcript_object(transcript)
        attendees = self._emails_from_transcript_object(transcript)
        date = self._date_from_transcript_object(transcript)
        meeting_name = self._meeting_name_from_transcript_object(transcript)

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
        formatted_lines.append(f"Organizer: {organizer_email}")
        formatted_lines.append(f"Attendees: {attendees}")
        formatted_lines.append(f"Date: {date}")
        formatted_lines.append(f"Meeting Name: {meeting_name}")
        for sentence in sentences:
            minutes = int(sentence.get("start_time", 0)) // 60
            seconds = int(sentence.get("start_time", 0)) % 60
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            speaker = sentence.get("speaker_name", "Unknown Speaker")
            text = sentence.get("raw_text", "")
            formatted_line = f"{timestamp} {speaker}: {text}"
            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)