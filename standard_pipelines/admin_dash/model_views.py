from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for

from wtforms import SelectMultipleField
from wtforms.widgets import ListWidget, CheckboxInput

class RestrictedView(ModelView):
    # TODO: Ensure that only admins have access to this
    def is_accessible(self):
        return (current_user.is_active and
                current_user.is_authenticated and
                current_user.has_role('admin')
                )
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('security.login'))

class UserView(RestrictedView):
    can_delete = True
    can_edit = True
    can_view_details = True
    can_export = True

    column_exclude_list = ['password',
                                      'last_login_at',
                                      'last_login_ip',
                                      'current_login_at',
                                      'current_login_ip',
                                      'login_count']

    column_list = ('email',
                                                   'roles',
                                                   'is_confirmed',
                                                   'active')

    form_args = dict(
        roles=dict(
            widget=ListWidget(prefix_label=False),
            option_widget=CheckboxInput(),
        )
    )


    column_searchable_list = ['email', 'confirmed_at']

    column_display_all_relations = True
    column_labels = dict(user_roles='Roles')
    

    def _roles_formatter(view, context, model, name):
        return ', '.join([role.name for role in model.roles])
    
    def _is_confirmed_formatter(self, context, model, name):
        return model.confirmed_at is not None

    column_formatters = {
        'roles': _roles_formatter,
        'is_confirmed': _is_confirmed_formatter
    }
    
    column_type_formatters = {
        bool: lambda view, value: 'Yes' if value else 'No'
    }

class UserRoleView(RestrictedView):
    can_delete = True
    can_edit = True
    can_view_details = True
    can_export = True

    column_list = ('user_id',
                                                   'role_id',
                                                   'created_at')
    
class ClientView(RestrictedView):
    can_delete = True
    can_edit = True
    can_view_details = True
    can_export = True
    
    column_list = ('name', 'description', 'is_active', 'created_at')
    column_searchable_list = ['name', 'description']
    column_sortable_list = ['name', 'created_at', 'is_active']
    column_filters = ['is_active']
    
    column_labels = {
        'name': 'Client Name',
        'description': 'Description',
        'is_active': 'Active Status',
        'created_at': 'Created Date'
    }
    
    column_descriptions = {
        'name': 'Name of the client',
        'description': 'Additional information about the client',
        'is_active': 'Whether the client is currently active'
    }
    
    column_formatters = {
        'is_active': lambda v, c, m, p: 'Yes' if m.is_active else 'No',
    }
    
class DataFlowView(RestrictedView):
    can_delete = True
    can_edit = True
    can_view_details = True
    can_export = True
    
    column_list = ('name', 'description', 'version', 'created_at')
    column_searchable_list = ['name', 'description']
    column_sortable_list = ['name', 'version', 'created_at']
    
    column_labels = {
        'name': 'Flow Name',
        'description': 'Description',
        'version': 'Version',
        'created_at': 'Created Date'
    }
    
    column_descriptions = {
        'name': 'Name of the data flow',
        'description': 'Description of what this flow does',
        'version': 'Current version of the flow'
    }
    
class ClientDataFlowView(RestrictedView):
    can_delete = True
    can_edit = True
    can_view_details = True
    can_export = True
    
    column_list = ('client_id', 'data_flow_id', 'is_active', 'created_at')
    column_sortable_list = ['is_active', 'created_at']
    column_filters = ['is_active']
    
    column_formatters = {
        'is_active': lambda v, c, m, p: 'Yes' if m.is_active else 'No',
    }
