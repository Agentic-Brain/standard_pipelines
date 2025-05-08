from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import current_user, login_required
from standard_pipelines.admin import admin, _registered_views
from sqlalchemy import func, inspect
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

def _get_safe_attributes(obj):
    """Get a dictionary of an object's attributes, excluding sensitive ones."""
    # Skip these attributes for security and to avoid circular references
    skip_attrs = {
        'password', 'tf_totp_secret', '_sa_instance_state', 
        'query', 'query_class', 'metadata'
    }
    
    # Only include direct attributes, not relationships or methods
    result = {}
    try:
        mapper = inspect(obj.__class__)
        column_names = [column.key for column in mapper.columns]
        
        for name in column_names:
            if name in skip_attrs:
                continue
            try:
                value = getattr(obj, name)
                # Skip callables, class attributes, and None values
                if not callable(value) and not name.startswith('__'):
                    # Convert values to string for safe display
                    if value is not None:
                        # Handle dates and other special types
                        if hasattr(value, 'isoformat'):  # For dates and times
                            result[name] = value.isoformat()
                        else:
                            result[name] = str(value)
            except:
                # Skip any attributes that can't be accessed
                pass
    except:
        # If anything goes wrong, return a minimal set of information
        if hasattr(obj, 'id'):
            result['id'] = str(getattr(obj, 'id'))
            
    return result

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
    
    # Get primary key column name
    mapper = inspect(view.model)
    pk_column = mapper.primary_key[0]
    pk_name = pk_column.key
    
    data = []
    for item in items:
        row = {}
        for column in column_names:
            row[column] = view.get_column_value(item, column)
        
        # Store the ID for use in links
        row['id'] = str(getattr(item, pk_name))
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
    
    # Create a form for the model
    form = view.get_form_instance()
    
    # Handle form submission
    if request.method == 'POST':
        form = view.get_form_instance(formdata=request.form)
        try:
            if form.validate():
                try:
                    # Create a new instance of the model
                    instance = view.model()
                    
                    # Update the instance with form data
                    view.populate_obj_from_form(form, instance)
                    
                    # Save to database
                    view.session.add(instance)
                    view.session.commit()
                    
                    flash(f"New {view.name} created successfully", "success")
                    return redirect(url_for('admin.list_model', model_name=model_name))
                except Exception as e:
                    view.session.rollback()
                    import traceback
                    current_app.logger.error(f"Error creating {view.name}: {str(e)}")
                    current_app.logger.error(traceback.format_exc())
                    flash(f"Error creating {view.name}: {str(e)}", "error")
            else:
                flash("Please correct the errors in the form.", "error")
        except Exception as e:
            import traceback
            current_app.logger.error(f"Form processing error: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            flash(f"Error processing form: {str(e)}", "error")
    
    # Render the create form
    return render_template(
        'admin/create.html',
        admin_view=view,
        form=form,
        model_name=model_name
    )

@admin.route('/edit/<model_name>/<id>', methods=['GET', 'POST'])
@admin_required
def edit_model(model_name, id):
    """Generic route to edit an instance of any registered model"""
    
    # Find the view for this model name
    view = next((v for v in _registered_views if v.endpoint == model_name), None)
    
    if not view or not view.can_edit:
        abort(404, f"Model {model_name} not found or cannot be edited")
    
    # Get the primary key column for the model
    mapper = inspect(view.model)
    pk_column = mapper.primary_key[0]
    
    # Convert ID to proper type if needed
    try:
        # For UUID columns, we need to handle them differently
        if hasattr(pk_column.type, 'python_type') and pk_column.type.python_type.__name__ == 'UUID':
            from uuid import UUID
            try:
                # Try to convert to UUID if needed
                id_value = UUID(id) if not isinstance(id, UUID) else id
            except ValueError:
                # If not a valid UUID string
                abort(404, f"Invalid UUID format for {view.name} ID")
        else:
            # For other types (like int), use the column's type for casting
            id_value = id
        
        # Get the primary key column
        pk_name = pk_column.key
        
        # Build a filter using the proper column and value
        filter_condition = getattr(view.model, pk_name) == id_value
        
        # Get the specific model instance
        instance = view.session.query(view.model).filter(filter_condition).first()
        
        if not instance:
            abort(404, f"{view.name} with ID {id} not found")
    
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in edit view for {view.name} with ID {id}: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        abort(404, f"Error retrieving {view.name}")
    
    # Create a form for the model
    form = view.get_form_instance(obj=instance)
    
    # Handle form submission
    if request.method == 'POST':
        form = view.get_form_instance(formdata=request.form)
        try:
            if form.validate():
                try:
                    # Update the instance with form data
                    view.populate_obj_from_form(form, instance)
                    
                    # Save changes
                    view.session.commit()
                    
                    flash(f"{view.name} updated successfully", "success")
                    return redirect(url_for('admin.list_model', model_name=model_name))
                except Exception as e:
                    view.session.rollback()
                    import traceback
                    current_app.logger.error(f"Error updating {view.name}: {str(e)}")
                    current_app.logger.error(traceback.format_exc())
                    flash(f"Error updating {view.name}: {str(e)}", "error")
            else:
                flash("Please correct the errors in the form.", "error")
        except Exception as e:
            import traceback
            current_app.logger.error(f"Form processing error: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            flash(f"Error processing form: {str(e)}", "error")
    
    # Render the edit form
    return render_template(
        'admin/edit.html',
        admin_view=view,
        form=form,
        instance=instance,
        model_name=model_name
    )

@admin.route('/delete/<model_name>/<id>', methods=['POST'])
@admin_required
def delete_model(model_name, id):
    """Generic route to delete an instance of any registered model"""
    
    # Find the view for this model name
    view = next((v for v in _registered_views if v.endpoint == model_name), None)
    
    if not view or not view.can_delete:
        abort(404, f"Model {model_name} not found or cannot be deleted")
    
    # Get the primary key column for the model
    mapper = inspect(view.model)
    pk_column = mapper.primary_key[0]
    
    # Convert ID to proper type if needed
    try:
        # For UUID columns, we need to handle them differently
        if hasattr(pk_column.type, 'python_type') and pk_column.type.python_type.__name__ == 'UUID':
            from uuid import UUID
            try:
                # Try to convert to UUID if needed
                id_value = UUID(id) if not isinstance(id, UUID) else id
            except ValueError:
                # If not a valid UUID string
                abort(404, f"Invalid UUID format for {view.name} ID")
        else:
            # For other types (like int), use the column's type for casting
            id_value = id
        
        # Get the primary key column
        pk_name = pk_column.key
        
        # Build a filter using the proper column and value
        filter_condition = getattr(view.model, pk_name) == id_value
        
        # Get the specific model instance
        instance = view.session.query(view.model).filter(filter_condition).first()
        
        if not instance:
            abort(404, f"{view.name} with ID {id} not found")
    
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in delete view for {view.name} with ID {id}: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        abort(404, f"Error retrieving {view.name}")
    
    try:
        # Delete the instance
        view.session.delete(instance)
        view.session.commit()
        
        flash(f"{view.name} deleted successfully", "success")
    except Exception as e:
        view.session.rollback()
        import traceback
        current_app.logger.error(f"Error deleting {view.name} with ID {id}: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        flash(f"Error deleting {view.name}: {str(e)}", "error")
        
    # Redirect back to the list view
    return redirect(url_for('admin.list_model', model_name=model_name))

@admin.route('/details/<model_name>/<id>')
@admin_required
def details_model(model_name, id):
    """Generic route to view details of an instance of any registered model"""
    
    # Find the view for this model name
    view = next((v for v in _registered_views if v.endpoint == model_name), None)
    
    if not view or not view.can_view_details:
        abort(404, f"Model {model_name} not found or cannot view details")
    
    # Get the primary key column for the model
    mapper = inspect(view.model)
    pk_column = mapper.primary_key[0]
    
    # Convert ID to proper type if needed
    try:
        # For UUID columns, we need to handle them differently
        if hasattr(pk_column.type, 'python_type') and pk_column.type.python_type.__name__ == 'UUID':
            from uuid import UUID
            try:
                # Try to convert to UUID if needed
                id_value = UUID(id) if not isinstance(id, UUID) else id
            except ValueError:
                # If not a valid UUID string
                abort(404, f"Invalid UUID format for {view.name} ID")
        else:
            # For other types (like int), use the column's type for casting
            id_value = id
        
        # Get the primary key column
        pk_name = pk_column.key
        
        # Build a filter using the proper column and value
        filter_condition = getattr(view.model, pk_name) == id_value
        
        # Get the specific model instance using the filter
        instance = view.session.query(view.model).filter(filter_condition).first()
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error fetching {view.name} with ID {id}: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        
        if current_app.debug:
            # In debug mode, show detailed error
            abort(500, f"Error retrieving {view.name}: {str(e)}")
        else:
            # In production, just show generic error
            abort(404, f"Error retrieving {view.name}")
    
    if not instance:
        abort(404, f"{view.name} with ID {id} not found")
    
    # Get all columns (not just the displayed list columns)
    mapper = inspect(view.model)
    all_columns = [column.key for column in mapper.columns]
    
    # Filter out any columns to be excluded from details view
    display_columns = [col for col in all_columns if col not in view.details_exclude_list]
    
    # Prepare data for the template
    column_labels = {col: view.get_column_label(col) for col in display_columns}
    
    # Get formatted values for all columns
    data = {}
    for column in display_columns:
        data[column] = view.get_column_value(instance, column)
    
    # Collect related objects (relationships)
    relationships = {}
    rel_data_objects = {}
    
    for relationship in mapper.relationships:
        rel_name = relationship.key
        rel_data = getattr(instance, rel_name)
        
        # Skip if None or empty
        if not rel_data:
            continue
            
        # Check if it's a collection
        if hasattr(rel_data, '__iter__') and not isinstance(rel_data, (str, bytes, bytearray)):
            # For collections like one-to-many relationships
            items = []
            related_objects = []
            
            for item in rel_data:
                # Add string representation
                if hasattr(item, '__str__'):
                    items.append(str(item))
                else:
                    # Fallback to using the primary key
                    items.append(f"ID: {getattr(item, 'id', 'Unknown')}")
                
                # Gather details for linking
                try:
                    item_class = item.__class__
                    item_name = item_class.__name__.lower()
                    item_id = getattr(item, 'id', None)
                    
                    if item_id is not None:
                        # Store model name and ID for linking
                        related_objects.append({
                            'model_name': item_name,
                            'id': item_id,
                            'attributes': _get_safe_attributes(item)
                        })
                    else:
                        related_objects.append(None)
                except:
                    related_objects.append(None)
                    
            relationships[rel_name] = items
            rel_data_objects[rel_name] = related_objects
        else:
            # For single objects like many-to-one relationships
            if hasattr(rel_data, '__str__'):
                relationships[rel_name] = str(rel_data)
            else:
                relationships[rel_name] = f"ID: {getattr(rel_data, 'id', 'Unknown')}"
                
            # Gather details for linking
            try:
                item_class = rel_data.__class__
                item_name = item_class.__name__.lower()
                item_id = getattr(rel_data, 'id', None)
                
                if item_id is not None:
                    # Store model name and ID for linking
                    rel_data_objects[rel_name] = {
                        'model_name': item_name,
                        'id': item_id,
                        'attributes': _get_safe_attributes(rel_data)
                    }
            except:
                pass
    
    return render_template(
        'admin/details.html',
        admin_view=view,
        instance=instance,
        data=data,
        column_labels=column_labels,
        display_columns=display_columns,
        relationships=relationships,
        rel_data_objects=rel_data_objects,  # Pass the detailed relationship data
        model_name=model_name
    )