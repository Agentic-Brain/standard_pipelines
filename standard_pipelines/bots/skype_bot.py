import asyncio
import atexit
import os
import re
import time
import traceback
from types import TracebackType
from typing import Callable

import requests
from skpy import Skype, SkypeUtils, SkypeUser, SkypeConnection, SkypeEvent, SkypeMessageEvent, SkypeChatUpdateEvent, SkypeNewMessageEvent, SkypeSingleChat, SkypeTypingEvent
from skpy.core import SkypeRateLimitException, SkypeApiException
import threading

class SkypeBot:
    def __init__(self, username: str, password: str, greeting_handler: Callable[[str], str], convo_start_handler: Callable[[str, str], None] = None, message_handler: Callable[[str, str, str], str] = None):
        """
        Initialize the Skype client with your Skype username and password.
        """
        self.username : str = username
        self.password : str = password
        self.greeting_handler : Callable[[str], str] = greeting_handler if greeting_handler else self.default_greeting_handler;
        self.convo_start_handler : Callable[[str, str], None] = convo_start_handler if convo_start_handler else self.default_convo_start_handler
        self.message_handler : Callable[[str, str, str], str] = message_handler if message_handler else self.default_message_handler
        self.initialize()

    def initialize(self):
        print("initializing skype")
        self.skype : Skype = Skype(self.username, self.password)
        self.skype.setPresence(SkypeUtils.Status.Online)
        
        # Create a stop event and a placeholder for the polling thread.
        self._stop_event = threading.Event()
        self.polling_thread = None
        
        # Start polling if in the reloader's main process.
        self.start_polling()
        
        # Ensure the polling thread is stopped on exit.
        atexit.register(self.stop_polling)
        
    def start_chat(self, email: str):
        # https://search.skype.com/v2.0/search?searchString=devbot-2077@hotmail.com&requestId=Query5&locale=en-US&sessionId=e5e35812-1dc3-4278-a9cf-e362b45b8890
        user : SkypeUser = None
        while user is None:
            try:
                users = self.skype.contacts.search(email)
                if len(users) > 0:
                    user : SkypeUser = users[0]
                else:
                    print("no user found")
                    break

            except SkypeRateLimitException:
                print("rate limited, waiting...")
                time.sleep(30)
            except SkypeApiException as e:
                print("api error:", e)
                time.sleep(15)

        if user is None:
            raise Exception("no user found:", email)

        convo_id : str = user.chat.id

        

        # conn : SkypeConnection = self.skype.conn
        
        print()
        print(user)
        print()
        greeting = self.greeting_handler(user.name.first)
        self.convo_start_handler(convo_id, greeting)
        print(greeting)
        print("inviting", user.id)
        
        print("contactIds=", self.skype.contacts.contactIds)
        # if user.id not in self.skype.contacts.contactIds:
        #     print("user not in contacts")
        #     response : requests.Response = user.invite(greeting)
        
        #     print(response.text)

        #     if response.status_code == 200:
        #         print("invite successful")
        #     else:
        #         print("invite failed")
        # else:
        user.chat.sendMsg(greeting)

        # chat = self.skype.chats.chat(user.id)
        # self.convo_start_handler(self, )
        # chat.sendMsg("Hello, this is a test message from the Skype API!")

    def extract_conversation_id(self, conversation_link : str):
        """
        Extracts and returns the conversation ID from the given conversation link URL.
        The conversation ID is assumed to be the substring immediately after '/conversations/'.

        Parameters:
            conversation_link (str): The URL containing the conversation link.

        Returns:
            str: The extracted conversation ID, or None if not found.
        """
        # The regex pattern looks for '/conversations/' followed by one or more characters that are not a slash.
        pattern = r"/conversations/([^/]+)"
        match = re.search(pattern, conversation_link)
        if match:
            return match.group(1)
        return None
    
    def extract_user_id(self, from_link : str):
        """
        Extracts and returns the conversation ID from the given conversation link URL.
        The conversation ID is assumed to be the substring immediately after '/conversations/'.

        Parameters:
            conversation_link (str): The URL containing the conversation link.

        Returns:
            str: The extracted conversation ID, or None if not found.
        """
        # The regex pattern looks for '/conversations/' followed by one or more characters that are not a slash.
        pattern = r"/contacts/([^/]+)"
        match = re.search(pattern, from_link)
        if match:
            full_tag = match.group(1)
            # Split the tag on the first colon.
            parts = full_tag.split(":", 1)
            if len(parts) > 1:
                # Return everything after the first colon.
                return parts[1]
            # Fallback: if no colon is found, return the full tag.
            return full_tag
        return None
    
    async def handle_event(self, event : SkypeEvent):

        if isinstance(event, SkypeTypingEvent):
            return

        username: str = None
        message_text: str = None
        conversation_id: str = None

        print("handle_event:",event)

        # if isinstance(event, SkypeMessageEvent):
        #     username = event.msgFrom
        #     message_text = event.msgContent
        #     # conversation_id = event.chatId
        #     print(event.msg)
        #     print(f"{conversation_id} {username} {message_text}")
        if isinstance(event, SkypeNewMessageEvent):
            print("SkypeNewMessageEvent:", event.raw)
            username = self.extract_user_id(event.resource['from'])
            message_text = event.msgContent
            conversation_id = self.extract_conversation_id(event.resource['conversationLink'])
            print(event.msg)
        # elif isinstance(event, SkypeChatUpdateEvent):
        #     # scue : SkypeChatUpdateEvent = event
        #     # print("SkypeChatUpdateEvent:", scue.raw)
        #     username = event.resource['imdisplayname']
        #     message_text = event.resource['content']
        #     conversation_id = event.resource['id']
        else:
            print("unknown event type:", type(event))
            return

        conn : SkypeConnection = self.skype.conn
        print("conn.user:", conn.user)
        if conn.user is None:
            conn.getUser()
        my_username = conn.user.get("username")
        print("my_username:", my_username)
        print("msg_username:", username)

        if username == my_username:
            print("ignoring message from self")
            return

        print(f"incoming message: [{conversation_id}] <{username}> {message_text}")

        if (message_text.startswith("!restart")):
            print("restarting skype bot")
            self.restart()
            return

        if conversation_id:
            chat : SkypeSingleChat = self.skype.chats.chat(conversation_id)
            chat.setTyping(True)
            response = self.message_handler(conversation_id, username, message_text)
            self.send_message(conversation_id, response)
        else:
            print("[WARNING] no conversation id found")
        
    def extract_conversation_id(self, conversation_link):
        """
        Extracts and returns the conversation ID from the given conversation link URL.
        The conversation ID is assumed to be the substring immediately after '/conversations/'.

        Parameters:
            conversation_link (str): The URL containing the conversation link.

        Returns:
            str: The extracted conversation ID, or None if not found.
        """
        # The regex pattern looks for '/conversations/' followed by one or more characters that are not a slash.
        pattern = r"/conversations/([^/]+)"
        match = re.search(pattern, conversation_link)
        if match:
            return match.group(1)
        return None

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
            print(f"Failed to send message: {e.with_traceback()}")

    def restart(self):
        self.stop_polling()
        self.initialize()

    def start_polling(self):
        # Only start polling in the reloader's main process.
        if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            print("Not starting polling because WERKZEUG_RUN_MAIN is not true")
            return
        
        self._stop_event.clear()
        
        def polling_loop():
            while not self._stop_event.is_set():
                try:
                    new_events = self.skype.getEvents()
                    print(f"new_events: {len(new_events)}")
                    for event in new_events:
                        # print(event)
                        # Run the async handle_event in a new event loop.
                        asyncio.run(self.handle_event(event))
                
                except Exception as e:
                    print("error:", e)
                    print(traceback.format_exc())
        
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
