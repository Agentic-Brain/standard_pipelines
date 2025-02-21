import json
from pathlib import Path

SYSTEM_PROMPT = Path(__file__).parent.joinpath("system_prompt.txt").read_text(encoding="utf-8")
GREETING = Path(__file__).parent.joinpath("greeting.txt").read_text(encoding="utf-8")
SCHEDULE_CALL_MESSAGE = Path(__file__).parent.joinpath("schedule_call.txt").read_text(encoding="utf-8")
FUNCTIONS : list[dict] = json.loads(Path(__file__).parent.joinpath("functions.json").read_text(encoding="utf-8"))
FUNCTIONS = [{"type": "function", "function": func} for func in FUNCTIONS]
LINK = "https://redtrack.io/request-demo/"

SECRETS = json.loads(Path(__file__).parent.joinpath("secrets.production.json").read_text(encoding="utf-8"))

OPENAI_API_KEY = SECRETS['OPENAI_API_KEY']
TELEGRAM_TOKEN = SECRETS['TELEGRAM_TOKEN']

SKYPE_USERNAME = SECRETS['SKYPE_USERNAME']
SKYPE_PASSWORD = SECRETS['SKYPE_PASSWORD']

TWILIO_ACCOUNT_SID = SECRETS['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = SECRETS['TWILIO_AUTH_TOKEN']
TWILIO_PHONE_NUMBER = SECRETS['TWILIO_PHONE_NUMBER']

WHATSAPP_GREETING_TEMPLATE = "redtrack_greeting_dynamic"

VECTOR_STORE = {
    "id" : None if 'VECTOR_STORE_ID' not in SECRETS else SECRETS['VECTOR_STORE_ID'],
    "name" : "RedTrack Knowledge Base"
}

ASSISTANT = {
    "id" : None if 'ASSISTANT_ID' not in SECRETS else SECRETS['ASSISTANT_ID'],
    "name" : "Redtrack Inbound Lead Outreach Tool",
    "model" : "gpt-4o-mini",
    "system_prompt" : SYSTEM_PROMPT,
    "tools" : FUNCTIONS + [{"type": "file_search"}],
    "tool_resources" : {
        "file_search" : {
            "vector_store_ids" : [] if VECTOR_STORE["id"] is None else [VECTOR_STORE["id"]]
        }
    },
}