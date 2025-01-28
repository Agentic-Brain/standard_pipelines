from flask import Blueprint, Flask, render_template, Response
from typing import TYPE_CHECKING

main = Blueprint('main', __name__)

def init_app(app: Flask):
    app.logger.debug(f'Initalizing blueprint {__name__}')


@main.route('/')
def index():
    return render_template('base.html')

@main.route('/healthcheck')
def healthcheck():
    return Response(status=200)

from . import routes