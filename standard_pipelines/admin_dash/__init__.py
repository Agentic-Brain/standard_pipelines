from flask import Blueprint, Flask
from standard_pipelines.extensions import admin, db
# TODO: Move flask_admin stuff to a new blueprint
from standard_pipelines.auth.models import User, Role
from standard_pipelines.admin_dash.model_views import UserView, RestrictedView

from typing import TYPE_CHECKING


admin_dash = Blueprint('admin_dash', __name__)

def init_app(app: Flask):
    app.logger.debug(f'Initalizing blueprint {__name__}')
    admin.init_app(app)

    with app.app_context():
        admin.add_view(UserView(User, db.session))
        admin.add_view(RestrictedView(Role, db.session))
        # admin.add_view(RestrictedView(UserRole, app.db.session))
        # admin.add_view(ModelView())


# from . import routes

