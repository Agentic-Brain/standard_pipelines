from standard_pipelines.bots.telegram_bot import TelegramBot
from .redtrack import redtrack_config, greeting_handler, convo_start_handler, message_handler

if __name__ == '__main__':
    bot = TelegramBot(redtrack_config.TELEGRAM_TOKEN, greeting_handler, convo_start_handler, message_handler)
