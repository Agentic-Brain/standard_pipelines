from flask import Blueprint

bp = Blueprint("dialpad", __name__)

def init_app(app):
    from standard_pipelines.api.dialpad import routes
    app.register_blueprint(bp, url_prefix="/api/dialpad")
