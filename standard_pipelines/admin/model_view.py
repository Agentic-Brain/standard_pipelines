from flask import render_template, request, redirect, url_for, flash, abort
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.sql import sqltypes
from sqlalchemy.inspection import inspect as sa_inspect
from standard_pipelines.extensions import db
from typing import List, Dict, Any, Optional, Type, Set, Callable
import json
from functools import wraps
from flask_login import current_user
import datetime

class ModelView:
    """Base view for SQLAlchemy models"""
    
    def __init__(self, model: Type[DeclarativeMeta], session=None, 
                 name=None, category=None, endpoint=None,
                 column_list=None, column_exclude_list=None,
                 column_labels=None, column_descriptions=None,
                 can_create=True, can_edit=True, can_delete=True,
                 can_view_details=True, can_export=False):
        
        self.model = model
        self.session = session or db.session
        self.name = name or self._get_model_name()
        self.category = category
        self.endpoint = endpoint or self._get_endpoint()
        
        # Column specifications
        self.column_list = column_list
        self.column_exclude_list = column_exclude_list or []
        self.column_labels = column_labels or {}
        self.column_descriptions = column_descriptions or {}
        
        # Permissions
        self.can_create = can_create
        self.can_edit = can_edit
        self.can_delete = can_delete
        self.can_view_details = can_view_details
        self.can_export = can_export
        
        # Default formatters for different types
        self.type_formatters = {
            bool: lambda value: 'Yes' if value else 'No',
            datetime.datetime: lambda value: value.strftime('%Y-%m-%d %H:%M:%S') if value else '',
            datetime.date: lambda value: value.strftime('%Y-%m-%d') if value else '',
        }
        
        # Custom column formatters
        self.column_formatters = {}
    
    def _get_model_name(self) -> str:
        """Get a user-friendly name for the model"""
        name = self.model.__name__
        # Convert CamelCase to Title Case with spaces
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)
    
    def _get_endpoint(self) -> str:
        """Get a URL-friendly endpoint for the model"""
        return self.model.__name__.lower()
    
    def register_with_blueprint(self, blueprint):
        """Register this view's routes with the blueprint"""
        
        # List view
        blueprint.add_url_rule(
            f'/model/{self.endpoint}/',
            endpoint=f'{self.endpoint}.index',
            view_func=self.is_accessible_decorator(self.index_view),
            methods=['GET']
        )
        
        # Create view
        if self.can_create:
            blueprint.add_url_rule(
                f'/model/{self.endpoint}/new',
                endpoint=f'{self.endpoint}.create',
                view_func=self.is_accessible_decorator(self.create_view),
                methods=['GET', 'POST']
            )
        
        # Edit view
        if self.can_edit:
            blueprint.add_url_rule(
                f'/model/{self.endpoint}/edit/<int:id>',
                endpoint=f'{self.endpoint}.edit',
                view_func=self.is_accessible_decorator(self.edit_view),
                methods=['GET', 'POST']
            )
        
        # Delete view
        if self.can_delete:
            blueprint.add_url_rule(
                f'/model/{self.endpoint}/delete/<int:id>',
                endpoint=f'{self.endpoint}.delete',
                view_func=self.is_accessible_decorator(self.delete_view),
                methods=['POST']
            )
        
        # Details view
        if self.can_view_details:
            blueprint.add_url_rule(
                f'/model/{self.endpoint}/details/<int:id>',
                endpoint=f'{self.endpoint}.details',
                view_func=self.is_accessible_decorator(self.details_view),
                methods=['GET']
            )
    
    def is_accessible(self):
        """
        Override this method to implement custom access control.
        Return True if the user can access this view, False otherwise.
        """
        return current_user.is_authenticated and current_user.has_role('admin')
    
    def is_accessible_decorator(self, func):
        """Decorator to check if the view is accessible"""
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if not self.is_accessible():
                return self.inaccessible_callback()
            return func(*args, **kwargs)
        return decorated_view
    
    def inaccessible_callback(self):
        """Called when a user tries to access a view they don't have access to"""
        return redirect(url_for('security.login'))
    
    def get_column_names(self) -> List[str]:
        """Get the list of column names to display"""
        if self.column_list:
            return self.column_list
        
        # Get all column names from the model
        mapper = sa_inspect(self.model)
        columns = [column.key for column in mapper.columns]
        
        # Filter out excluded columns
        return [col for col in columns if col not in self.column_exclude_list]
    
    def get_column_label(self, column_name: str) -> str:
        """Get a user-friendly label for a column"""
        # Check if a custom label is defined
        if column_name in self.column_labels:
            return self.column_labels[column_name]
        
        # Convert snake_case to Title Case
        return column_name.replace('_', ' ').title()
    
    def get_column_description(self, column_name: str) -> str:
        """Get the description for a column"""
        return self.column_descriptions.get(column_name, '')
    
    def get_column_value(self, model_instance: Any, column_name: str) -> Any:
        """Get the formatted value of a column for a model instance"""
        # Check if there's a custom formatter for this column
        if column_name in self.column_formatters:
            return self.column_formatters[column_name](self, model_instance, column_name)
        
        # Get the raw value
        value = getattr(model_instance, column_name)
        
        # Apply type formatters if applicable
        value_type = type(value)
        if value_type in self.type_formatters:
            return self.type_formatters[value_type](value)
        
        # Handle relationship values
        if hasattr(value, '__iter__') and not isinstance(value, (str, bytes, bytearray)):
            return ', '.join(str(item) for item in value)
        
        return value
    
    def index_view(self):
        """List view for the model"""
        # Get all instances of the model
        query = self.session.query(self.model)
        items = query.all()
        
        # Prepare data for the template
        column_names = self.get_column_names()
        column_labels = {col: self.get_column_label(col) for col in column_names}
        
        data = []
        for item in items:
            row = {}
            for column in column_names:
                row[column] = self.get_column_value(item, column)
            row['id'] = getattr(item, 'id')  # Assume primary key is named 'id'
            data.append(row)
        
        return render_template(
            'admin/model/list.html',
            admin_view=self,
            list_columns=column_names,
            column_labels=column_labels,
            data=data
        )
    
    def create_view(self):
        """Create view for the model"""
        # Placeholder for form handling
        return "Create view not yet implemented"
    
    def edit_view(self, id):
        """Edit view for the model"""
        # Placeholder for form handling
        return f"Edit view for ID {id} not yet implemented"
    
    def delete_view(self, id):
        """Delete view for the model"""
        # Placeholder for deletion handling
        return f"Delete view for ID {id} not yet implemented"
    
    def details_view(self, id):
        """Details view for the model"""
        # Placeholder for showing details
        return f"Details view for ID {id} not yet implemented"