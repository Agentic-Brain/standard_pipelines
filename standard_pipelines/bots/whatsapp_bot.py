import asyncio
import atexit
from collections import deque
from datetime import datetime, UTC
import os
import random
import threading
import time
from typing import Callable, List
from twilio.rest import Client
from twilio.rest.api.v2010.account.message import MessageInstance
from twilio.rest.content.v1.content import ContentInstance, ContentList, ApprovalFetchList
from twilio.rest.content.v1.content.approval_fetch import ApprovalFetchContext, ApprovalFetchInstance
from twilio.rest.content.v1.content.approval_create import ApprovalCreateInstance, ApprovalCreateList

from standard_pipelines.assistants.redtrack.config import config

class WhatsappBot:
    """
    A simple wrapper around the Twilio Python client to send SMS and WhatsApp messages.
    """

    def __init__(self, account_sid: str, auth_token: str, twilio_phone_number: str, greeting_handler: Callable[[str], str], convo_start_handler: Callable[[str, str], None] = None, message_handler: Callable[[str, str, str], str] = None):
        
        """
        :param account_sid: Your Twilio Account SID
        :param auth_token: Your Twilio Auth Token
        :param twilio_phone_number: The Twilio phone number (in E.164 format) you want to send messages from.
                                   Example: '+12345678900'
        """

        self.random_id = random.randint(1, 100000000)

        print("starting Whatsapp bot:", self.random_id)

        self.greeting_handler: Callable[[str], str] = greeting_handler
        self.convo_start_handler: Callable[[str, str], None] = convo_start_handler
        self.message_handler: Callable[[str, str, str], str] = message_handler

        self.client : Client = Client(account_sid, auth_token)
        self.twilio_phone_number = twilio_phone_number
        
        self._stop_event = threading.Event()
        self.polling_thread = None

        self.start_polling()

        print("registering whatsapp with atexit")
        # Ensure the polling thread is stopped on exit.
        atexit.register(self.stop_polling)

    def stop_polling(self):
        if self.polling_thread is not None:
            print("Stopping polling thread...")
            self._stop_event.set()
            self.polling_thread.join(timeout=5)
            self.polling_thread = None
            print("Polling thread stopped.")

    def start_polling(self):
        # Only start polling in the reloader's main process.
        if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            print("Not starting polling because WERKZEUG_RUN_MAIN is not true")
            return
        
        self._stop_event.clear()

        # This deque will store the last 100 processed message SIDs.
        processed_message_sids = deque(maxlen=100)
        async def polling_loop():
            print(f"polling loop started")
            last_poll: datetime = datetime.now(UTC)
            while not self._stop_event.is_set():
                try:
                    poll_time: datetime = datetime.now(UTC)

                    print(f"[{self.random_id}] processed_message_ids:", processed_message_sids)

                    sms_events: List[MessageInstance] = [event for event in self.client.messages.list(
                        to=self.twilio_phone_number,
                        date_sent_after=last_poll
                    ) if event.sid not in processed_message_sids]

                    whatsapp_events: List[MessageInstance] = [event for event in self.client.messages.list(
                        to=f"whatsapp:{self.twilio_phone_number}",
                        date_sent_after=last_poll
                    ) if event.sid not in processed_message_sids]

                    new_events = sms_events + whatsapp_events
                    
                    last_poll = poll_time
                    if new_events:
                        print(f"[{self.random_id}] new_events: {len(new_events)} since {last_poll}")
                        for event in new_events:
                            if event.sid not in processed_message_sids:
                                processed_message_sids.append(event.sid)
                                try:
                                    await self.handle_event(event)
                                except Exception as e:
                                    print(f"Error handling event {event.sid}: {e}")
                                    import traceback
                                    print(traceback.format_exc())
                            
                    time.sleep(1)

                except Exception as e:
                    print("error:", e)
                    print(traceback.format_exc())

        async def run_polling_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            await polling_loop()

        self.polling_thread = threading.Thread(target=lambda: asyncio.run(run_polling_thread()), daemon=True)
        self.polling_thread.start()

    async def handle_event(self, event : MessageInstance):
        print(f"[{self.random_id}]", event.sid)        

        phone_number: str = event.from_
        username: str = self.name_map[phone_number] if phone_number in self.name_map else phone_number
        message_text: str = event.body
        conversation_id: str = event.from_

        print(event.from_, event.date_sent.strftime("%H:%M:%S"), f"<{username}> {message_text}")

        # if event and event.channel_post and event.channel_post.text:
        #     username = event.channel_post.sender_chat.username
        #     message_text = event.channel_post.text
        #     conversation_id = event.channel_post.sender_chat.id
        # elif event and event.message and event.message.text:
        #     print("from_user:", event.message.from_user)
        #     username = event.message.from_user.full_name
        #     message_text = event.message.text
        #     conversation_id = event.message.from_user.id

        if conversation_id:
            if message_text.startswith("/start"):
                username = message_text.replace("/start ", "")
                # await self.send_typing_signal(conversation_id)
                greeting = self.greeting_handler(username)
                self.convo_start_handler(conversation_id, greeting)
                response = greeting
            else:
                # await self.send_typing_signal(conversation_id)
                response = self.message_handler(conversation_id, username, message_text)
            self.send_message(conversation_id, response)
        else:
            print("[WARNING] no conversation id found")
            print(event)

    name_map : dict[str, str] = {}
    def start_chat(self, first_name: str, phone_number: str):
        self.name_map[phone_number] = first_name

        greeting = self.greeting_handler(first_name)
        self.convo_start_handler(first_name, greeting)
        whatsapp_response : MessageInstance = self.send_message(phone_number, greeting)

        if whatsapp_response.error_code:
            print("error:",whatsapp_response.error_code, whatsapp_response.error_message)
        # whatsapp_response : MessageInstance = self.send_templated_message(phone_number, config.WHATSAPP_GREETING_TEMPLATE, [first_name, config.LINK])

    def send_message(self, to: str, message: str):
        from_ = self.twilio_phone_number
        if to.startswith("whatsapp:") and not from_.startswith("whatsapp:"):
            from_ = "whatsapp:" + from_


        print(f"send_message(self, {to}, {message})")
        response : MessageInstance = self.client.messages.create(
            body=message,
            from_ = from_,  # Twilio WhatsApp sender
            to=to
        )

    def send_templated_message(self, to: str, name: str, variables: list[str]):
        template = self.find_template(name)
        if template is None:
            raise Exception(f"Template {name} not found")
        
        from_ = self.twilio_phone_number
        if to.startswith("whatsapp:") and not from_.startswith("whatsapp:"):
            from_ = "whatsapp:" + from_

        self.client.messages.create({
            "content_sid": template.sid,
            "content_variables": variables,
            "from": from_,
            "to": to
        })

    def find_templates(self, name: str):
        templates : List[ContentInstance] = self.client.content.contents.list()
        return [template for template in templates if template.friendly_name == name]

    def find_template(self, name: str):
        templates = self.find_templates(name)
        if len(templates) == 0:
            print(f"No templates found for {name}")
            return None
        elif len(templates) > 1:
            print(f"Multiple templates found for {name}, using the first one")

        return templates[0]

    def create_variable_dict(self, variables: list[str]):
        return {str(i+1): var for i, var in enumerate(variables)}

    def create_template(self, name: str, body: str, variables: list[str]):
        existing_templates : List[ContentInstance] = self.find_templates(name)
        for template in existing_templates:
            print(f"Deleting template: {template.sid}")
            template.delete()

        var_dict = self.create_variable_dict(variables)
        final_body = body
        for i, var in enumerate(variables):
            final_body = final_body.replace(f"{{{var}}}", f"{{{{{i+1}}}}}")

        payload = ContentInstance.ContentCreateRequest(payload=
            {
                "friendly_name": name,
                "language": "en",
                "variables": var_dict,
                "types": ContentList.Types(payload={
                    "twilio_text": ContentList.TwilioText(payload={
                        "body": final_body
                    })
                })
            }
        )

        template = self.client.content.contents.create(payload)
        approval_create : ApprovalCreateInstance = template.approval_create.create(ApprovalCreateList.ContentApprovalRequest({
            "name": name,
            "category": "UTILITY"
        }))
        
        pending_approval = True
        while pending_approval:
            approval_fetch : ApprovalFetchInstance = template.approval_fetch().fetch()
            response = approval_fetch.whatsapp;

            print(response)
            status : str = response.get('status')

            if status == "unsubmitted":
                pending_approval = False
                print("Template unsubmitted")
            elif status == 'rejected':
                pending_approval = False
                rejection_reason : str = response.get('rejection_reason')
                print("Template rejected:", rejection_reason)
            else:
                print("Unknown status:", status)
            
            if (pending_approval):
                time.sleep(10)

        return template.sid
