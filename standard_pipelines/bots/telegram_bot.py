import asyncio
from typing import Callable
from telegram import Update
import telegram
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, ChatMemberHandler, MessageHandler, filters
import threading

class TelegramBot:
    def __init__(self, token: str, greeting_handler: Callable[[str], str], convo_start_handler: Callable[[str, str], None] = None, message_handler: Callable[[str, str, str], str] = None) -> None:
        self.greeting_handler: Callable[[str], str] = greeting_handler if greeting_handler else self.default_greeting_handler
        self.convo_start_handler: Callable[[str, str], None] = convo_start_handler if convo_start_handler else self.default_convo_start_handler
        self.message_handler: Callable[[str, str, str], str] = message_handler if message_handler else self.default_message_handler
        self.app : Application = ApplicationBuilder().token(token).build()
        self.app.add_handler(MessageHandler(filters.TEXT, self.handle_event))
        self.app.add_handler(ChatMemberHandler(self.handle_member))
        # asyncio.run(self.__start_async())
        # self.app.run_polling(drop_pending_updates=True, close_loop=False, )
        # self.__start_bot()

    def start(self):
        self.app.run_polling(drop_pending_updates=True, close_loop=False)
    


    async def __start_async(self):
        # Start the bot in the background
        bot_task = asyncio.create_task(self.__start_bot())
        # Do other async work concurrently
        await asyncio.sleep(1)
        print("Main async code continues working!")
        # When you're ready to shut down, cancel the bot or call app.stop()

    def __start_bot(self):
        # self.app.run_polling(drop_pending_updates=True)

        def run_polling_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.app.run_polling(drop_pending_updates=True, close_loop=False)
        polling_thread = threading.Thread(target=run_polling_thread)
        polling_thread.start()

        # polling_thread = threading.Thread(target=self.app.run_polling, kwargs={'drop_pending_updates': True})
        # polling_thread.start()

        # await self.app.initialize()
        # if self.app.post_init:
        #     await self.app.post_init(self.app)
        # # Start polling (this is the coroutine that run_polling awaits)
        # await self.app.updater.start_polling()
        # await self.app.start()
        # # The bot is now running without blocking your main async code
        
    async def send_typing_signal(self, chat_id: str):
        await self.app.bot.send_chat_action(chat_id=chat_id, action=telegram.constants.ChatAction.TYPING)

    async def handle_event(self, event: Update, context: ContextTypes.DEFAULT_TYPE):
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
                await self.send_typing_signal(conversation_id)
                response = self.greeting_handler(username)
                print("greeting:", response)
                self.convo_start_handler(conversation_id, response)
            else:
                await self.send_typing_signal(conversation_id)
                response = self.message_handler(conversation_id, username, message_text)
            await self.send_message(conversation_id, response)
        else:
            print("[WARNING] no conversation id found")
            print(event.to_json())

    def default_greeting_handler(self, username: str) -> str:
        return f"Hello, {username}! How can I help you today?"

    def default_message_handler(self, conversation_id: str, username: str, message_text: str) -> str:
        """A simple default message handler that echoes the message."""
        return f"You said: {message_text}"
    
    def default_convo_start_handler(self, conversation_id: str, message_text: str) -> None:
        print(f"Starting conversation with {conversation_id}: {message_text}")

    async def handle_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(update)
        if update.my_chat_member.new_chat_member.status == "member":
            await self.send_message(update.my_chat_member.chat.id, "Welcome to the group "+update.my_chat_member.new_chat_member.user.username+"!")
        else:
            await self.send_message(update.my_chat_member.chat.id, "You are not a member of this group.")

    async def send_message(self, chat_id: str, message: str):
        await self.app.bot.send_message(chat_id=chat_id, text=message)