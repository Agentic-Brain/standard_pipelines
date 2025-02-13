from standard_pipelines.api.services import BaseManualAPIManager
from flask import current_app
from requests.auth import AuthBase
from abc import ABCMeta
from typing import Optional
from datetime import datetime

class DialpadAPIManager(BaseManualAPIManager, metaclass=ABCMeta):
    class DialpadAuthenticator(AuthBase):
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        def __call__(self, r):
            r.headers["Authorization"] = f"Bearer {self.api_key}"
            return r

    def authenticator(self) -> AuthBase:
        return self.DialpadAuthenticator(self.api_config["api_key"])

    @property
    def required_config(self) -> list[str]:
        return ["api_key"]

    def api_url(self, api_context: Optional[dict] = None) -> str:
        call_id = api_context.get("call_id") if api_context else None
        if not call_id:
            raise ValueError("call_id is required")
        return f"https://dialpad.com/api/v2/transcripts/{call_id}"

    def https_headers(self, api_context: Optional[dict] = None) -> Optional[dict]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def transcript(self, call_id: str) -> tuple[str, list[str], list[str]]:
        """
        Returns a tuple of:
        - prettified transcript suitable for input into an AI prompt
        - list of user IDs present in the transcript
        - list of names present in the transcript
        """
        transcript_object = self.get_response({"call_id": call_id}).json()
        pretty_transcript = self._pretty_transcript_from_transcript_object(transcript_object)
        user_ids = self._user_ids_from_transcript_object(transcript_object)
        names = self._names_from_transcript_object(transcript_object)
        return pretty_transcript, user_ids, names

    def _user_ids_from_transcript_object(self, transcript: dict) -> list[str]:
        return list(set(
            line.get("user_id", "") 
            for line in transcript.get("lines", [])
            if line.get("user_id")
        ))

    def _names_from_transcript_object(self, transcript: dict) -> list[str]:
        return list(set(
            line.get("name", "Unknown Speaker")
            for line in transcript.get("lines", [])
        ))

    def _pretty_transcript_from_transcript_object(self, transcript: dict) -> str:
        lines = transcript.get("lines", [])
        formatted_lines = []
        
        for line in lines:
            if line.get("type") != "transcript":
                continue
                
            time_str = line.get("time", "")
            try:
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                timestamp = dt.strftime("[%H:%M:%S]")
            except:
                timestamp = "[00:00:00]"
                
            name = line.get("name", "Unknown Speaker")
            content = line.get("content", "")
            formatted_line = f"{timestamp} {name}: {content}"
            formatted_lines.append(formatted_line)
            
        return "\n".join(formatted_lines)
