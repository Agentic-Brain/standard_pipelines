import json
from pathlib import Path

SYSTEM_PROMPT = Path(__file__).parent.joinpath("system_prompt.txt").read_text(encoding="utf-8")
GREETING = Path(__file__).parent.joinpath("greeting.txt").read_text(encoding="utf-8")
SCHEDULE_CALL_MESSAGE = Path(__file__).parent.joinpath("schedule_call.txt").read_text(encoding="utf-8")
FUNCTIONS : list[dict] = json.loads(Path(__file__).parent.joinpath("functions.json").read_text(encoding="utf-8"))
FUNCTIONS = [{"type": "function", "function": func} for func in FUNCTIONS]
LINK = "https://redtrack.io/request-demo/"

OPENAI_API_KEY = "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"
TELEGRAM_TOKEN = "7844583271:AAHwhb8x0b_5gpLfPvR3pJf6gZvuwBb4BwI"

SKYPE_USERNAME = "devbot-2077@hotmail.com"
SKYPE_PASSWORD = "ZdQgj41k3cZHZv"

TWILIO_ACCOUNT_SID = "ACa01bb06bb020eaacdfb886ee3252c69b"
TWILIO_AUTH_TOKEN = "1e0f035291b23520796cf6906720c5dc"
TWILIO_PHONE_NUMBER = "+14155238886"
# TWILIO_PHONE_NUMBER = "+18882802486"

VECTOR_STORE = {
    "id" : "vs_67ad4870761881918ee49d874b3c03e0",
    "name" : "RedTrack Knowledge Base"
}

ASSISTANT = {
    "id" : "asst_TT69GyMnGA8Oy9YfnuXfiUW7",
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