from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ChatMemberHandler, MessageHandler, filters
import code

class TelegramMessenger:
    def __init__(self, token: str):
        self.app = ApplicationBuilder().token(token).build()
        self.app.add_handler(MessageHandler(filters.TEXT, self.handle_event))
        self.app.add_handler(ChatMemberHandler(self.handle_member))
        self.app.run_polling()

    async def handle_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(update)
        if update and update.channel_post and update.channel_post.text:
            await self.send_message(update.channel_post.sender_chat.id, "You said: "+update.channel_post.text)
        else:
            await self.send_message(update.channel_post.sender_chat.id, "You didn't say anything.")


    async def handle_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(update)
        if update.my_chat_member.new_chat_member.status == "member":
            await self.send_message(update.my_chat_member.chat.id, "Welcome to the group "+update.my_chat_member.new_chat_member.user.username+"!")
        else:
            await self.send_message(update.my_chat_member.chat.id, "You are not a member of this group.")



    async def send_message(self, chat_id: str, message: str):
        await self.app.bot.send_message(chat_id=chat_id, text=message)

        # self.bot.send_message(chat_id=chat_id, text=message)

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

if __name__ == "__main__":
    token = "7844583271:AAHwhb8x0b_5gpLfPvR3pJf6gZvuwBb4BwI"
    messenger = TelegramMessenger(token)
    # messenger.send_message(chat_id="1234567890", message="Hello, world!")

    # app = ApplicationBuilder().token("YOUR TOKEN HERE").build()

    # app.add_handler(CommandHandler("hello", hello))

    # app.run_polling()