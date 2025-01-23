from flask import Blueprint, Flask, current_app, render_template
from typing import TYPE_CHECKING

data_flow = Blueprint('data_flow', __name__)


def init_app(app: Flask):
    app.logger.debug(f'Initalizing blueprint {__name__}')