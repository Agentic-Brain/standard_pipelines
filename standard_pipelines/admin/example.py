"""
Example usage of the CustomAdmin implementation.

This file demonstrates how to register models with the CustomAdmin system.
"""

from standard_pipelines.admin import register_view
from standard_pipelines.admin.views import ModelView
from standard_pipelines.data_flow.models import Client, DataFlow, ClientDataFlowJoin
from standard_pipelines.auth.models import User, Role
from standard_pipelines.extensions import db

def register_admin_models():
    """Register models with the custom admin interface."""
    
    # User Management
    user_view = ModelView(
        User, 
        db.session,
        name="Users",
        category="User Management",
        endpoint="custom_users",
        column_list=['email', 'active', 'confirmed_at', 'roles'],
        column_exclude_list=['password', 'last_login_at', 'last_login_ip',
                           'current_login_at', 'current_login_ip', 'login_count'],
        column_labels={
            'email': 'Email Address',
            'active': 'Is Active',
            'confirmed_at': 'Confirmed',
            'roles': 'User Roles'
        },
        column_formatters={
            'roles': lambda view, model, name: ', '.join([role.name for role in model.roles])
        }
    )
    register_view(user_view)
    
    role_view = ModelView(
        Role, 
        db.session,
        name="Roles",
        category="User Management",
        endpoint="custom_roles"
    )
    register_view(role_view)
    
    # Client Management
    client_view = ModelView(
        Client,
        db.session,
        name="Clients",
        category="Client Management",
        endpoint="custom_clients",
        column_list=['name', 'description', 'is_active', 'created_at'],
        column_labels={
            'name': 'Client Name',
            'description': 'Description',
            'is_active': 'Active Status',
            'created_at': 'Created Date'
        },
        column_descriptions={
            'name': 'Name of the client',
            'description': 'Additional information about the client',
            'is_active': 'Whether the client is currently active'
        }
    )
    register_view(client_view)
    
    # Data Flow Management
    flow_view = ModelView(
        DataFlow,
        db.session,
        name="Data Flows",
        category="Data Flow Management",
        endpoint="custom_flows",
        column_list=['name', 'description', 'version', 'created_at'],
        column_labels={
            'name': 'Flow Name',
            'description': 'Description',
            'version': 'Version',
            'created_at': 'Created Date'
        }
    )
    register_view(flow_view)
    
    mapping_view = ModelView(
        ClientDataFlowJoin,
        db.session,
        name="Client-Flow Mappings",
        category="Data Flow Management",
        endpoint="custom_mappings",
        column_list=['client_id', 'data_flow_id', 'is_active', 'created_at'],
        column_formatters={
            'client_id': lambda view, model, name: model.client.name if model.client else '',
            'data_flow_id': lambda view, model, name: model.data_flow.name if model.data_flow else ''
        }
    )
    register_view(mapping_view)