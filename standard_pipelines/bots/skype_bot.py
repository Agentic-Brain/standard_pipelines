import asyncio
import atexit
import os
import time
from typing import Callable
from skpy import Skype, SkypeUtils, SkypeUser, SkypeConnection, SkypeEvent, SkypeMessageEvent, SkypeChatUpdateEvent, SkypeNewMessageEvent
import threading

class SkypeBot:
    def __init__(self, username: str, password: str, greeting_handler: Callable[[str], str], convo_start_handler: Callable[[str, str], None] = None, message_handler: Callable[[str, str, str], str] = None):
        """
        Initialize the Skype client with your Skype username and password.
        """
        self.greeting_handler : Callable[[str], str] = greeting_handler if greeting_handler else self.default_greeting_handler;
        self.convo_start_handler : Callable[[str, str], None] = convo_start_handler if convo_start_handler else self.default_convo_start_handler
        self.message_handler : Callable[[str, str, str], str] = message_handler if message_handler else self.default_message_handler
        print("initializing skype")
        self.skype = Skype(username, password)
        self.skype.setPresence(SkypeUtils.Status.Online)
        
        # Create a stop event and a placeholder for the polling thread.
        self._stop_event = threading.Event()
        self.polling_thread = None
        
        # Start polling if in the reloader's main process.
        self.start_polling()
        
        # Ensure the polling thread is stopped on exit.
        atexit.register(self.stop_polling)
        
    def start_chat(self, username: str):
        # https://search.skype.com/v2.0/search?searchString=devbot-2077@hotmail.com&requestId=Query5&locale=en-US&sessionId=e5e35812-1dc3-4278-a9cf-e362b45b8890
        users = self.skype.contacts.search(username)
        if len(users) > 0:
            user : SkypeUser = users[0]
            print()
            print(user)
            print()
            greeting = self.greeting_handler(user.name.first)
            print(greeting)
            print("inviting", user.name)
            print("inviting", user.id)
            response : SkypeConnection = user.invite(greeting)
            print(response)

            if not response.text:
                print("invite successful")
            else:
                print("invite failed")
                print(response.text)

            # chat = self.skype.chats.chat(user.id)
            # self.convo_start_handler(self, )
            # chat.sendMsg("Hello, this is a test message from the Skype API!")

    async def handle_event(self, event):
        username: str = None
        message_text: str = None
        conversation_id: str = None

        # if isinstance(event, SkypeMessageEvent):
        #     username = event.msgFrom
        #     message_text = event.msgContent
        #     # conversation_id = event.chatId
        #     print(event.msg)
        #     print(f"{conversation_id} {username} {message_text}")
        if isinstance(event, SkypeNewMessageEvent):
            username = event.msgFrom
            message_text = event.msgContent
            conversation_id = event.resource['threadtopic']
            print(event.msg)
        elif isinstance(event, SkypeChatUpdateEvent):
            # scue : SkypeChatUpdateEvent = event
            # print("SkypeChatUpdateEvent:", scue.raw)
            username = event.resource['imdisplayname']
            message_text = event.resource['content']
            conversation_id = event.resource['id']
        else:
            print("unknown event type:", type(event))
            return

        print(f"incoming message: [{conversation_id}] <{username}> {message_text}")

        if conversation_id:
            if message_text.startswith("/start"):
                unique_param = message_text.replace("/start ", "")
                # await self.send_typing_signal(conversation_id)
                response = self.convo_start_handler(conversation_id, username, unique_param)
            else:
                # await self.send_typing_signal(conversation_id)
                response = self.message_handler(conversation_id, username, message_text)
            await self.send_message(conversation_id, response)
        else:
            print("[WARNING] no conversation id found")
    
    def send_message(self, conversation_id: str, message: str):
        """
        Send a message to a given conversation (channel or one-on-one chat).
        
        :param conversation_id: The ID for the Skype conversation. 
                               For one-on-one, this is usually "live:<skype_username>".
                               For group chats, it is often a longer string like 
                               "19:<some_unique_id>@thread.skype".
        :param message: The text content of the message you want to send.
        """
        try:
            chat = self.skype.chats.chat(conversation_id)
            chat.sendMsg(message)
            print(f"Message sent to {conversation_id} successfully.")
        except Exception as e:
            print(f"Failed to send message: {e}")

    def start_polling(self):
        # Only start polling in the reloader's main process.
        if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            print("Not starting polling because WERKZEUG_RUN_MAIN is not true")
            return
        
        self._stop_event.clear()
        
        def polling_loop():
            while not self._stop_event.is_set():
                new_events = self.skype.getEvents()
                print(f"new_events: {len(new_events)}")
                for event in new_events:
                    print(event)
                    # Run the async handle_event in a new event loop.
                    asyncio.run(self.handle_event(event))
        
        self.polling_thread = threading.Thread(target=polling_loop, daemon=True)
        self.polling_thread.start()
        print("Polling thread started.")

    def stop_polling(self):
        if self.polling_thread is not None:
            print("Stopping polling thread...")
            self._stop_event.set()
            self.polling_thread.join(timeout=5)
            self.polling_thread = None
            print("Polling thread stopped.")
