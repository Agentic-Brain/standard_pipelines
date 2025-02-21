import click
from .redtrack import redtrack_bp
from .redtrack import start_bots
from .redtrack import config as redtrack_config
from .redtrack import greeting_handler, convo_start_handler, message_handler

def init_app(app):
    app.cli.add_command(redtrack.handle_command)