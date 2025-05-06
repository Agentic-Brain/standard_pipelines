from flask_admin import AdminIndexView, expose
from flask_login import current_user
from flask import redirect, url_for, render_template
from sqlalchemy import func
from standard_pipelines.data_flow.models import Client, DataFlow, ClientDataFlowJoin

class SecureAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated or not current_user.has_role('admin'):
            return redirect(url_for('security.login'))
        
        # Get statistics for dashboard
        try:
            from standard_pipelines.extensions import db
            total_clients = db.session.query(func.count(Client.id)).scalar() or 0
            active_clients = db.session.query(func.count(Client.id)).filter(Client.is_active == True).scalar() or 0
            total_flows = db.session.query(func.count(DataFlow.id)).scalar() or 0
            active_mappings = db.session.query(func.count(ClientDataFlowJoin.id)).filter(ClientDataFlowJoin.is_active == True).scalar() or 0
            
            stats = {
                'total_clients': total_clients,
                'active_clients': active_clients,
                'total_flows': total_flows,
                'active_mappings': active_mappings
            }
        except Exception as e:
            # Log the error for debugging
            print(f"Error fetching stats: {e}")
            stats = {
                'total_clients': 0,
                'active_clients': 0,
                'total_flows': 0,
                'active_mappings': 0
            }
        
        # Use self.render to ensure all required admin context variables are included
        return self.render('admin/index.html', stats=stats)