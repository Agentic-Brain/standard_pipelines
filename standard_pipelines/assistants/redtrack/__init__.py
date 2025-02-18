import click
from .redtrack import redtrack_bp
from .redtrack import start_bots
from .redtrack import config

def init_app(app):
    app.cli.add_command(redtrack.handle_command)