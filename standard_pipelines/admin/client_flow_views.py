"""
Client Data Flow Management views for the admin dashboard.
This implements dynamic configuration management for data flows connected to clients.
"""

from flask import render_template, request, redirect, url_for, flash, current_app, Blueprint, jsonify
from flask_login import login_required, current_user
from sqlalchemy import inspect as sa_inspect
from .views import ModelView
from standard_pipelines.extensions import db
from standard_pipelines.data_flow.models import (
    Client, DataFlow, ClientDataFlowJoin, DataFlowConfiguration
)
from standard_pipelines.data_flow.utils import DataFlowRegistryMeta
import importlib
import inspect as py_inspect
import uuid
import json
from typing import Dict, Any, List, Type, Optional, Tuple

# Blueprint for client flow configuration management 
client_flow_blueprint = Blueprint('client_flow', __name__, url_prefix='/client-flow')

@client_flow_blueprint.route('/<client_id>/missing-tables')
@login_required
def missing_tables(client_id):
    """View missing database tables for data flow configurations."""
    if not current_user.has_role('admin'):
        flash("You don't have permission to access this page.", "error")
        return redirect(url_for('admin.index'))
    
    # Get the client
    client = Client.query.get_or_404(client_id)
    
    # Get all mappings for this client
    mappings = ClientDataFlowJoin.query.filter_by(client_id=client_id).all()
    
    # Track which tables are missing
    missing_tables = []
    
    for mapping in mappings:
        # Get the data flow
        data_flow = DataFlow.query.get(mapping.data_flow_id)
        if not data_flow:
            continue
        
        # Check if configuration class exists
        config_class = get_config_class_for_flow(data_flow.name)
        if config_class:
            try:
                # Try to get a count from the table
                # This will fail with an error if the table doesn't exist
                from sqlalchemy import func
                db.session.query(func.count(config_class.id)).limit(1).scalar()
                # If we get here, the table exists
            except Exception as e:
                # Table likely doesn't exist or can't be queried
                if 'relation' in str(e) and 'does not exist' in str(e):
                    missing_tables.append({
                        'name': config_class.__tablename__,
                        'flow_name': data_flow.name,
                        'model_name': config_class.__name__,
                        'error': str(e)
                    })
    
    return render_template(
        'admin/client_flows/missing_tables.html',
        client=client,
        missing_tables=missing_tables
    )

@client_flow_blueprint.route('/<client_id>')
@login_required
def client_flows(client_id):
    if not current_user.has_role('admin'):
        flash("You don't have permission to access this page.", "error")
        return redirect(url_for('admin.index'))
    
    # Get the client
    client = Client.query.get_or_404(client_id)
    
    # Get all mappings for this client
    mappings = ClientDataFlowJoin.query.filter_by(client_id=client_id).all()
    
    # Get all available data flows
    all_flows = DataFlow.query.all()
    
    # Track which tables are missing
    missing_tables = []
    
    # Create data structure for the page with flow info and configuration status
    flows_data = []
    for mapping in mappings:
        # Get the data flow
        data_flow = DataFlow.query.get(mapping.data_flow_id)
        if not data_flow:
            continue
        
        # Check if configuration exists
        config_class = get_config_class_for_flow(data_flow.name)
        config = None
        table_missing = False
        
        if config_class:
            try:
                # First, test if the table exists by running a very simple query
                try:
                    from sqlalchemy import func
                    # Use func.count() which is more reliable
                    db.session.query(func.count(config_class.id)).limit(1).scalar()
                    # If we get here, the table exists
                    table_exists = True
                except Exception as table_e:
                    # Check if the error is about a missing table
                    if 'relation' in str(table_e) and 'does not exist' in str(table_e):
                        table_missing = True
                        missing_tables.append({
                            'name': config_class.__tablename__,
                            'flow_name': data_flow.name,
                            'error': str(table_e)
                        })
                        # Don't try to query a table that doesn't exist
                        continue
                
                # If the table exists, try to get the configuration
                config = config_class.query.filter_by(
                    client_id=client_id,
                    registry_id=data_flow.id
                ).first()
            except Exception as e:
                # This can happen if there are other database issues
                current_app.logger.warning(f"Error retrieving configuration for flow {data_flow.name}: {str(e)}")
                # Don't mark as missing if it's not a table missing error
                if not table_missing and 'relation' in str(e) and 'does not exist' in str(e):
                    table_missing = True
                    missing_tables.append({
                        'name': config_class.__tablename__,
                        'flow_name': data_flow.name,
                        'error': str(e)
                    })
        
        flows_data.append({
            'mapping_id': str(mapping.id),
            'data_flow': data_flow,
            'is_active': mapping.is_active,
            'has_config': config is not None,
            'config': config,
            'config_class': config_class.__name__ if config_class else None,
            'has_config_class': config_class is not None,
            'table_missing': table_missing
        })
    
    # Get flows that aren't mapped to this client yet
    mapped_flow_ids = [mapping.data_flow_id for mapping in mappings]
    available_flows = [flow for flow in all_flows if flow.id not in mapped_flow_ids]
    
    # If there are missing tables, show the warning
    if missing_tables:
        flash(
            f"Some data flow configurations require database migrations. "
            f"{len(missing_tables)} table(s) need to be created.",
            "warning"
        )
    
    return render_template(
        'admin/client_flows/list.html',
        client=client,
        flows_data=flows_data,
        available_flows=available_flows,
        missing_tables=missing_tables
    )

@client_flow_blueprint.route('/<client_id>/add', methods=['POST'])
@login_required
def add_flow(client_id):
    """Add a data flow to a client."""
    if not current_user.has_role('admin'):
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    flow_id = request.form.get('flow_id')
    if not flow_id:
        flash("Flow ID is required", "error")
        return redirect(url_for('client_flow.client_flows', client_id=client_id))
    
    # Check if client and flow exist
    client = Client.query.get_or_404(client_id)
    flow = DataFlow.query.get_or_404(flow_id)
    
    # Check if mapping already exists
    existing = ClientDataFlowJoin.query.filter_by(
        client_id=client_id, 
        data_flow_id=flow_id
    ).first()
    
    if existing:
        flash(f"'{flow.name}' is already mapped to this client", "warning")
    else:
        # Create the mapping
        mapping = ClientDataFlowJoin(
            client_id=client_id,
            data_flow_id=flow_id,
            is_active=True
        )
        db.session.add(mapping)
        db.session.commit()
        flash(f"'{flow.name}' added successfully", "success")
    
    return redirect(url_for('client_flow.client_flows', client_id=client_id))

@client_flow_blueprint.route('/<client_id>/toggle/<mapping_id>', methods=['POST'])
@login_required
def toggle_active(client_id, mapping_id):
    """Toggle active status of a client-flow mapping."""
    if not current_user.has_role('admin'):
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    mapping = ClientDataFlowJoin.query.get_or_404(mapping_id)
    
    # Toggle the active status
    mapping.is_active = not mapping.is_active
    db.session.commit()
    
    status = "activated" if mapping.is_active else "deactivated"
    flow_name = DataFlow.query.get(mapping.data_flow_id).name
    flash(f"'{flow_name}' {status} successfully", "success")
    
    return redirect(url_for('client_flow.client_flows', client_id=client_id))

@client_flow_blueprint.route('/<client_id>/remove/<mapping_id>', methods=['POST'])
@login_required
def remove_flow(client_id, mapping_id):
    """Remove a data flow from a client."""
    if not current_user.has_role('admin'):
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    mapping = ClientDataFlowJoin.query.get_or_404(mapping_id)
    flow_name = DataFlow.query.get(mapping.data_flow_id).name
    
    # Also delete any configuration for this mapping
    flow = DataFlow.query.get(mapping.data_flow_id)
    config_class = get_config_class_for_flow(flow.name)
    if config_class:
        try:
            # First check if the table exists
            try:
                from sqlalchemy import func
                db.session.query(func.count(config_class.id)).limit(1).scalar()
                # Table exists, proceed to delete any configuration
                config = config_class.query.filter_by(
                    client_id=client_id,
                    registry_id=flow.id
                ).first()
                if config:
                    db.session.delete(config)
            except Exception as table_e:
                if 'relation' in str(table_e) and 'does not exist' in str(table_e):
                    # Table doesn't exist, nothing to delete
                    current_app.logger.warning(f"Table for {config_class.__name__} does not exist, skipping configuration deletion")
                else:
                    # Some other error occurred
                    raise table_e
        except Exception as e:
            # Handle other errors
            current_app.logger.warning(f"Error handling configuration for flow {flow.name} during removal: {str(e)}")
            # Roll back the session to ensure a clean state
            db.session.rollback()
    
    # Delete the mapping
    db.session.delete(mapping)
    db.session.commit()
    
    flash(f"'{flow_name}' removed from client", "success")
    return redirect(url_for('client_flow.client_flows', client_id=client_id))

@client_flow_blueprint.route('/<client_id>/configure/<flow_id>', methods=['GET', 'POST'])
@login_required
def configure_flow(client_id, flow_id):
    """Configure a data flow for a client."""
    if not current_user.has_role('admin'):
        flash("You don't have permission to access this page.", "error")
        return redirect(url_for('admin.index'))
    
    # Get the client and flow
    client = Client.query.get_or_404(client_id)
    flow = DataFlow.query.get_or_404(flow_id)
    
    # Get the configuration class for this flow
    config_class = get_config_class_for_flow(flow.name)
    if not config_class:
        flash(f"No configuration available for '{flow.name}'", "error")
        return redirect(url_for('client_flow.client_flows', client_id=client_id))
    
    # Get existing configuration or create new one
    config = None
    table_exists = False
    try:
        # First check if the table exists
        try:
            from sqlalchemy import func
            db.session.query(func.count(config_class.id)).limit(1).scalar()
            table_exists = True
        except Exception as table_e:
            if 'relation' in str(table_e) and 'does not exist' in str(table_e):
                # Table doesn't exist
                flash(f"The database table for this configuration ({config_class.__tablename__}) does not exist. You need to create it with a migration.", "warning")
                return redirect(url_for('client_flow.missing_tables', client_id=client_id))
            else:
                # Some other error
                raise table_e
                
        # If table exists, proceed to get configuration
        config = config_class.query.filter_by(
            client_id=client_id,
            registry_id=flow_id
        ).first()
    except Exception as e:
        # This can happen if there are other database issues
        current_app.logger.warning(f"Error retrieving configuration for flow {flow.name}: {str(e)}")
        # Roll back the session to ensure a clean state
        db.session.rollback()
        flash(f"Error retrieving configuration: {str(e)}", "error")
        return redirect(url_for('client_flow.client_flows', client_id=client_id))
    
    if request.method == 'POST':
        # Process form submission
        try:
            # Create or update configuration
            if not config:
                config = config_class(
                    client_id=client_id,
                    registry_id=flow_id
                )
                db.session.add(config)
            
            # Update configuration from form data
            update_config_from_form(config, request.form)
            
            db.session.commit()
            flash(f"Configuration saved successfully", "success")
            return redirect(url_for('client_flow.client_flows', client_id=client_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving configuration: {str(e)}")
            flash(f"Error saving configuration: {str(e)}", "error")
    
    # Get configuration fields and their types/values
    config_fields = get_config_field_info(config_class, config)
    
    return render_template(
        'admin/client_flows/configure.html',
        client=client,
        flow=flow,
        config=config,
        config_fields=config_fields
    )

def get_config_class_for_flow(flow_name: str) -> Optional[Type[DataFlowConfiguration]]:
    """Get the configuration class for a specific data flow."""
    # First check if the flow exists in the registry
    if flow_name not in DataFlowRegistryMeta.DATA_FLOW_REGISTRY:
        return None
    
    # Get the flow class from the registry
    flow_class = DataFlowRegistryMeta.DATA_FLOW_REGISTRY[flow_name]
    
    # Import the module path, assuming naming convention
    module_path = f"standard_pipelines.data_flow.{flow_name.lower()}.models"
    
    try:
        # Try to import the module
        module = importlib.import_module(module_path)
        
        # Look for configuration classes that extend DataFlowConfiguration
        for name, obj in py_inspect.getmembers(module):
            if (py_inspect.isclass(obj) and 
                issubclass(obj, DataFlowConfiguration) and 
                obj != DataFlowConfiguration):
                
                # We'll skip table existence check - it's causing too many issues
                # and is better handled directly in the try/except when querying
                return obj
        
    except (ImportError, AttributeError) as e:
        current_app.logger.error(f"Error importing configuration for {flow_name}: {str(e)}")
    
    return None

def get_config_field_info(config_class: Type[DataFlowConfiguration], config_instance=None) -> List[Dict[str, Any]]:
    """Get configuration field information for a data flow."""
    # Get the mapper for the configuration class
    mapper = sa_inspect(config_class)
    
    # We'll exclude these fields as they're internal
    excluded_fields = ['id', 'client_id', 'registry_id', 'created_at', 
                      'modified_at', 'is_default', 'registry']
    
    fields = []
    for column in mapper.columns:
        if column.key in excluded_fields:
            continue
        
        # Get the value if instance is provided
        value = getattr(config_instance, column.key) if config_instance else None
        
        field_info = {
            'name': column.key,
            'label': column.key.replace('_', ' ').title(),
            'type': column.type.__class__.__name__,
            'nullable': column.nullable,
            'value': value,
            'default': column.default.arg if column.default else None,
            'description': getattr(column, 'description', '')
        }
        
        # Special handling for certain field types
        if field_info['type'] == 'JSON' or field_info['type'] == 'JSONB':
            field_info['value_json'] = json.dumps(value) if value else '{}'
        
        fields.append(field_info)
    
    return fields

def update_config_from_form(config, form_data):
    """Update configuration instance from form data."""
    mapper = sa_inspect(config.__class__)
    
    # We'll exclude these fields as they're internal
    excluded_fields = ['id', 'client_id', 'registry_id', 'created_at', 
                      'modified_at', 'is_default', 'registry']
    
    for column in mapper.columns:
        if column.key in excluded_fields:
            continue
        
        if column.key in form_data:
            value = form_data[column.key]
            
            # Convert empty string to None for nullable fields
            if value == '' and column.nullable:
                value = None
            
            # Type conversions based on column type
            column_type = column.type.__class__.__name__
            
            if column_type == 'Integer' and value is not None:
                value = int(value)
            elif column_type == 'Numeric' and value is not None:
                value = float(value)
            elif column_type == 'Boolean' and value is not None:
                value = value.lower() in ('true', 'yes', 'y', '1', 'on')
            elif (column_type == 'JSON' or column_type == 'JSONB') and value is not None:
                # If value starts with { or [, it's likely a JSON string
                if value.strip().startswith('{') or value.strip().startswith('['):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        # If JSON parsing fails, keep as string
                        pass
            
            setattr(config, column.key, value)