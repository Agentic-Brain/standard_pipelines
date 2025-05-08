from flask import render_template, request, redirect, url_for, flash, abort
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.sql import sqltypes
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import class_mapper, RelationshipProperty
from standard_pipelines.extensions import db
from typing import List, Dict, Any, Optional, Type, Set, Callable, Tuple
import json
from functools import wraps
from flask_login import current_user
import datetime
from wtforms import Form, StringField, TextAreaField, BooleanField, SelectField, DateTimeField, IntegerField, FloatField, FieldList, FormField, HiddenField, FileField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Optional as OptionalValidator, Length
from uuid import UUID

class ModelView:
    """Base view for SQLAlchemy models"""
    
    def __init__(self, model: Type[DeclarativeMeta], session=None, 
                 name=None, category=None, endpoint=None,
                 column_list=None, column_exclude_list=None,
                 form_excluded_columns=None, readonly_columns=None,
                 details_exclude_list=None,
                 column_labels=None, column_descriptions=None,
                 column_formatters=None, type_formatters=None,
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
        self.form_excluded_columns = form_excluded_columns or ['password', 'tf_totp_secret']  # Default security-sensitive fields
        self.readonly_columns = readonly_columns or ['created_at', 'modified_at', 'last_login_at', 'current_login_at', 'login_count']
        self.details_exclude_list = details_exclude_list or ['password', 'tf_totp_secret']
        self.column_labels = column_labels or {}
        self.column_descriptions = column_descriptions or {}
        
        # Permissions
        self.can_create = can_create
        self.can_edit = can_edit
        self.can_delete = can_delete
        self.can_view_details = can_view_details
        self.can_export = can_export
        
        # Default formatters for different types
        default_type_formatters = {
            bool: lambda value: 'Yes' if value else 'No',
            datetime.datetime: lambda value: value.strftime('%Y-%m-%d %H:%M:%S') if value else '',
            datetime.date: lambda value: value.strftime('%Y-%m-%d') if value else '',
            str: lambda value: self._format_long_text(value) if value and len(value) > 100 else value
        }
        self.type_formatters = type_formatters or default_type_formatters
        
        # Custom column formatters
        self.column_formatters = column_formatters or {}
    
    def _format_long_text(self, value):
        """Format long text to display better in the UI."""
        if not value:
            return value
        # Prevent XSS by converting < and > to entities
        value = value.replace('<', '&lt;').replace('>', '&gt;')
        # Add a class for styling long text fields
        return f'<div class="text-wrap">{value}</div>'
        
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
        """
        Register this view with the blueprint.
        We no longer need to add explicit routes since we use a centralized route handler.
        """
        # We keep this method for compatibility, but it's now empty
        pass
    
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
        mapper = inspect(self.model)
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
    
    def get_form(self):
        """Create a WTForms form class for this model."""
        # Cache the form to avoid recreating it for each request
        if hasattr(self, '_form_class'):
            return self._form_class
        
        # Create a new form class for this model
        class ModelForm(Form):
            pass
        
        # Get all columns from the model
        mapper = inspect(self.model)
        columns = []
        
        # First, add regular columns
        for column in mapper.columns:
            column_name = column.key
            
            # Skip columns that should be excluded from forms
            if column_name in self.form_excluded_columns:
                continue
                
            if column.primary_key:
                # Add ID field as hidden
                setattr(ModelForm, column_name, HiddenField())
                continue
            
            # Skip foreign keys if they have a corresponding relationship
            is_relationship_fk = False
            for relationship in mapper.relationships:
                for fk in relationship.local_columns:
                    if column_name == fk.name:
                        is_relationship_fk = True
                        break
                if is_relationship_fk:
                    break
                    
            if is_relationship_fk:
                continue
                
            # Create form field based on column type
            # If this is a read-only column, pass render_kw to disable it
            render_kw = None
            if column_name in self.readonly_columns:
                render_kw = {'readonly': True, 'disabled': True}
                
            field = self._create_field_for_column(column, render_kw=render_kw)
            if field:
                setattr(ModelForm, column_name, field)
                columns.append(column_name)
                
        # Now, add relationship fields
        for relationship in mapper.relationships:
            # Only handle many-to-one and one-to-one relationships for now
            if not relationship.uselist:  # one-to-one or many-to-one
                remote_model = relationship.mapper.class_
                relationship_name = relationship.key
                
                # Get key for field
                if relationship.key.endswith('_id'):
                    field_name = relationship.key
                else:
                    field_name = relationship.key + '_id'
                
                # Skip if in excluded columns
                if field_name in self.form_excluded_columns:
                    continue
                    
                # Get choices for the relationship
                try:
                    choices = [(str(item.id), str(item)) for item in self.session.query(remote_model).all()]
                    choices.insert(0, ('', '--- Select ---'))
                    
                    # Create render_kw for read-only fields
                    render_kw = None
                    if field_name in self.readonly_columns or relationship_name in self.readonly_columns:
                        render_kw = {'readonly': True, 'disabled': True}
                    
                    # Add the field with appropriate render_kw
                    field = SelectField(
                        choices=choices, 
                        validators=[OptionalValidator()],
                        render_kw=render_kw
                    )
                    
                    setattr(ModelForm, field_name, field)
                    columns.append(field_name)
                except:
                    # Skip relationships that can't be loaded
                    pass
                
        # Store the form class and column list
        self._form_class = ModelForm
        self._form_columns = columns
        
        return ModelForm
    
    def _create_field_for_column(self, column, render_kw=None):
        """Create a form field for a database column based on its type."""
        validators = []
        if not column.nullable and not column.default and not column.server_default:
            validators.append(DataRequired())
        else:
            validators.append(OptionalValidator())
            
        # Get column type
        column_type = column.type
        
        # String types
        if isinstance(column_type, sqltypes.String):
            if column.name == 'email':
                validators.append(Email())
            
            if column_type.length:
                validators.append(Length(max=column_type.length))
                
            if column_type.length and column_type.length > 100:
                return TextAreaField(validators=validators, render_kw=render_kw)
            return StringField(validators=validators, render_kw=render_kw)
            
        # Boolean type
        elif isinstance(column_type, sqltypes.Boolean):
            return BooleanField(render_kw=render_kw)
            
        # Integer type
        elif isinstance(column_type, sqltypes.Integer):
            return IntegerField(validators=validators, render_kw=render_kw)
            
        # Float/Decimal type
        elif isinstance(column_type, (sqltypes.Float, sqltypes.Numeric)):
            return FloatField(validators=validators, render_kw=render_kw)
            
        # Date/Time types
        elif isinstance(column_type, sqltypes.DateTime):
            return DateTimeField(format='%Y-%m-%d %H:%M:%S', validators=validators, render_kw=render_kw)
            
        # Enum types
        elif isinstance(column_type, sqltypes.Enum):
            choices = [(v, v) for v in column_type.enums]
            return SelectField(choices=choices, validators=validators, render_kw=render_kw)
            
        # UUID type
        elif hasattr(column_type, 'python_type') and column_type.python_type.__name__ == 'UUID':
            return StringField(validators=validators, render_kw=render_kw)
            
        # Default to string field for any other type
        return StringField(validators=validators, render_kw=render_kw)
    
    def get_form_instance(self, obj=None, **kwargs):
        """Get an instance of the form, optionally populated with data from obj."""
        form_class = self.get_form()
        if obj is not None:
            # Create a form with data from the object
            form = form_class(obj=obj, **kwargs)
            
            # For readonly fields, we need to explicitly set their data
            # because WTForms doesn't populate disabled fields by default
            for name in self.readonly_columns:
                if hasattr(form, name) and hasattr(obj, name):
                    field = getattr(form, name)
                    value = getattr(obj, name)
                    field.data = value
                    
            return form
            
        return form_class(**kwargs)
    
    def populate_obj_from_form(self, form, obj):
        """Update an object with data from the form."""
        for name in self._form_columns:
            # Skip fields not present in the form
            if not hasattr(form, name):
                continue
                
            # Skip read-only fields to prevent modifications
            if name in self.readonly_columns:
                continue
                
            field = getattr(form, name)
            # Skip fields without data
            if not hasattr(field, 'data'):
                continue
                
            # Get the column for this field
            try:
                column = inspect(self.model).columns.get(name)
            except:
                column = None
            
            # Convert data to the correct type if necessary
            value = field.data
            
            # Handle special column types
            if column is not None and hasattr(column.type, 'python_type'):
                # UUID conversion
                if column.type.python_type.__name__ == 'UUID' and value and not isinstance(value, UUID):
                    try:
                        value = UUID(value)
                    except ValueError:
                        # Skip invalid UUID values
                        continue
            
            # Check if the attribute exists on the object before setting it
            if hasattr(obj, name):
                setattr(obj, name, value)
            else:
                # Log that we're skipping an attribute that doesn't exist
                print(f"Warning: Attribute '{name}' not found on {obj.__class__.__name__}")
        
        return obj