from flask import Blueprint, Flask
from flask_admin import Admin
from flask_babel import Babel
from standard_pipelines.extensions import db
# TODO: Move flask_admin stuff to a new blueprint
from standard_pipelines.auth.models import User, Role
from standard_pipelines.admin_dash.model_views import (
    UserView, RestrictedView, ClientView, DataFlowView, ClientDataFlowView
)
from standard_pipelines.data_flow.models import Client, DataFlow, ClientDataFlowJoin
from standard_pipelines.admin_dash.admin_index import SecureAdminIndexView
from datetime import datetime

from typing import TYPE_CHECKING


admin_dash = Blueprint('admin_dash', __name__)
admin = None
babel = None

def init_app(app: Flask):
    app.logger.debug(f'Initalizing blueprint {__name__}')
    global admin, babel
    
    # Initialize Flask-Babel to fix the KeyError issue
    babel = Babel(app)
    
    # Initialize Flask-Admin
    admin = Admin(name='Standard Pipelines Admin', 
                  index_view=SecureAdminIndexView(), 
                  template_mode=None)
    admin.init_app(app)
    
    # Add context processor for templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    with app.app_context():
        # User management
        admin.add_view(UserView(User, db.session, endpoint='user', category="Users"))
        admin.add_view(RestrictedView(Role, db.session, endpoint='role', category="Users"))
        
        # Client management
        admin.add_view(ClientView(Client, db.session, endpoint='client', category="Clients"))
        
        # Data Flow management
        admin.add_view(DataFlowView(DataFlow, db.session, endpoint='dataflow', category="Data Flows"))
        admin.add_view(ClientDataFlowView(ClientDataFlowJoin, db.session, 
                                         endpoint='clientdataflowjoin',
                                         name="Client-Flow Mappings", 
                                         category="Data Flows"))


# from . import routes

