from flask import current_app, request, jsonify, render_template, redirect, url_for
from flask_security.views import register
from flask_security.utils import config_value, get_message, hash_password
from flask_security.decorators import anonymous_user_required
from werkzeug.datastructures import MultiDict
from standard_pipelines.auth.forms import CustomRegisterForm
import uuid

@anonymous_user_required
def register_view():
    """Custom registration view that handles client_id."""
    if request.is_json:
        form_data = MultiDict(request.get_json())
    else:
        form_data = request.form

    security = current_app.extensions['security']
    form = CustomRegisterForm(form_data)
    form.client_id.data = form_data.get('client_id')

    if form.validate_on_submit():
        # Validate client_id exists
        from standard_pipelines.auth.models import Client
        client = Client.query.get(form.client_id.data)
        if not client:
            if request.is_json:
                return jsonify({"error": "Invalid client_id"}), 400
            form.client_id.errors.append("Invalid client ID")
            return render_template(
                config_value('REGISTER_USER_TEMPLATE'),
                register_user_form=form,
                **get_message('REGISTER')
            )

        try:
            # Create the user with required fields
            user = security._datastore.create_user(
                email=form.email.data,
                password=hash_password(form.password.data),
                active=True,
                fs_uniquifier=str(uuid.uuid4()),
                client_id=form.client_id.data
            )
            security._datastore.commit()
        except Exception as e:
            current_app.logger.error(f"Failed to create user: {str(e)}")
            security._datastore.rollback()
            if request.is_json:
                return jsonify({"error": f"Could not register user: {str(e)}"}), 400
            form.email.errors.append("Could not register user")
            return render_template(
                config_value('REGISTER_USER_TEMPLATE'),
                register_user_form=form,
                **get_message('REGISTER')
            )

        if request.is_json:
            return jsonify({"message": "User registered successfully"})
        
        return redirect(url_for('security.login'))

    if request.is_json:
        return jsonify({"errors": form.errors})

    return render_template(
        config_value('REGISTER_USER_TEMPLATE'),
        register_user_form=form,
        **get_message('REGISTER')
    )
