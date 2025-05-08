from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user, login_required
from standard_pipelines.admin import admin, _registered_views
from sqlalchemy import func
from standard_pipelines.extensions import db
from standard_pipelines.data_flow.models import Client, DataFlow, ClientDataFlowJoin
from functools import wraps

# Custom decorator to restrict access to admin users
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_role('admin'):
            return redirect(url_for('security.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/')
@admin_required
def index():
    """Main admin dashboard page"""
    
    # Get statistics for dashboard
    try:
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
    
    return render_template('admin/index.html', stats=stats)

@admin.route('/list/<model_name>')
@admin_required
def list_model(model_name):
    """Generic route to list any registered model"""
    
    # Find the view for this model name
    view = next((v for v in _registered_views if v.endpoint == model_name), None)
    
    if not view:
        abort(404, f"Model {model_name} not found")
    
    # Get all instances of the model
    query = view.session.query(view.model)
    items = query.all()
    
    # Prepare data for the template
    column_names = view.get_column_names()
    column_labels = {col: view.get_column_label(col) for col in column_names}
    
    data = []
    for item in items:
        row = {}
        for column in column_names:
            row[column] = view.get_column_value(item, column)
        row['id'] = getattr(item, 'id')  # Assume primary key is named 'id'
        data.append(row)
    
    return render_template(
        'admin/list.html',
        admin_view=view,
        list_columns=column_names,
        column_labels=column_labels,
        data=data
    )

@admin.route('/create/<model_name>', methods=['GET', 'POST'])
@admin_required
def create_model(model_name):
    """Generic route to create a new instance of any registered model"""
    
    # Find the view for this model name
    view = next((v for v in _registered_views if v.endpoint == model_name), None)
    
    if not view or not view.can_create:
        abort(404, f"Model {model_name} not found or cannot be created")
    
    # Just a placeholder for now
    return "Create view not yet implemented"

@admin.route('/edit/<model_name>/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_model(model_name, id):
    """Generic route to edit an instance of any registered model"""
    
    # Find the view for this model name
    view = next((v for v in _registered_views if v.endpoint == model_name), None)
    
    if not view or not view.can_edit:
        abort(404, f"Model {model_name} not found or cannot be edited")
    
    # Just a placeholder for now
    return f"Edit view for {model_name} ID {id} not yet implemented"

@admin.route('/delete/<model_name>/<int:id>', methods=['POST'])
@admin_required
def delete_model(model_name, id):
    """Generic route to delete an instance of any registered model"""
    
    # Find the view for this model name
    view = next((v for v in _registered_views if v.endpoint == model_name), None)
    
    if not view or not view.can_delete:
        abort(404, f"Model {model_name} not found or cannot be deleted")
    
    # Just a placeholder for now
    return f"Delete view for {model_name} ID {id} not yet implemented"

@admin.route('/details/<model_name>/<int:id>')
@admin_required
def details_model(model_name, id):
    """Generic route to view details of an instance of any registered model"""
    
    # Find the view for this model name
    view = next((v for v in _registered_views if v.endpoint == model_name), None)
    
    if not view or not view.can_view_details:
        abort(404, f"Model {model_name} not found or cannot view details")
    
    # Just a placeholder for now
    return f"Details view for {model_name} ID {id} not yet implemented"