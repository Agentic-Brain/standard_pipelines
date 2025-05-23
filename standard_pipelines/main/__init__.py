from flask import Blueprint, Flask, render_template, Response, redirect, url_for
from typing import TYPE_CHECKING

main = Blueprint('main', __name__)

def init_app(app: Flask):
    app.logger.debug(f'Initalizing blueprint {__name__}')


@main.route('/')
def index():
    return redirect(url_for('auth.oauth_index'))

@main.route('/healthcheck')
def healthcheck():
    return Response(status=200)

from . import routes
from . import credentials_routes