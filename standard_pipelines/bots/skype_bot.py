import time
from typing import Callable
from skpy import Skype, SkypeUtils
import threading

class SkypeBot:
    def __init__(self, username: str, password: str, greeting_handler: Callable[[str], str], convo_start_handler: Callable[[str, str], None] = None, message_handler: Callable[[str, str, str], str] = None):
        """
        Initialize the Skype client with your Skype username and password.
        """
        self.greeting_handler : Callable[[str], str] = greeting_handler if greeting_handler else self.default_greeting_handler;
        self.convo_start_handler : Callable[[str, str], None] = convo_start_handler if convo_start_handler else self.default_convo_start_handler
        self.message_handler : Callable[[str, str, str], str] = message_handler if message_handler else self.default_message_handler
        self.skype = Skype(username, password)
        self.skype.setPresence(SkypeUtils.Status.Online)
        self.start_polling()
        
    def start_chat(self, username: str):
        # https://search.skype.com/v2.0/search?searchString=devbot-2077@hotmail.com&requestId=Query5&locale=en-US&sessionId=e5e35812-1dc3-4278-a9cf-e362b45b8890
        users = self.skype.contacts.search(username)
        if len(users) > 0:
            user = users[0]
            print(user)
            greeting = self.greeting_handler(self, user.name)
            print(greeting)
            user.invite(greeting)

            # chat = self.skype.chats.chat(user.id)
            # self.convo_start_handler(self, )
            # chat.sendMsg("Hello, this is a test message from the Skype API!")

    async def handle_event(self, event):
        print(event.to_json())

        username: str = None
        message_text: str = None
        conversation_id: str = None

        if event and event.channel_post and event.channel_post.text:
            username = event.channel_post.sender_chat.username
            message_text = event.channel_post.text
            conversation_id = event.channel_post.sender_chat.id
        elif event and event.message and event.message.text:
            print("from_user:", event.message.from_user)
            username = event.message.from_user.full_name
            message_text = event.message.text
            conversation_id = event.message.from_user.id

        if conversation_id:
            if message_text.startswith("/start"):
                unique_param = message_text.replace("/start ", "")
                # await self.send_typing_signal(conversation_id)
                response = self.convo_start_handler(self, conversation_id, username, unique_param)
            else:
                # await self.send_typing_signal(conversation_id)
                response = self.message_handler(self, conversation_id, username, message_text)
            await self.send_message(conversation_id, response)
        else:
            print("[WARNING] no conversation id found")
            print(event.to_json())
    
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
        def polling_loop():
            while True:
                new_events = self.skype.getEvents()
                for event in new_events:
                    print(event)
                    self.handle_event(event)
                time.sleep(1)
        polling_thread = threading.Thread(target=polling_loop, daemon=True)
        polling_thread.start()