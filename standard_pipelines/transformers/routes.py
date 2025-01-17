from flask import current_app
from standard_pipelines.transformers import transformers

@transformers.route('/transformers')
def index():
    return {"message": "Transformers blueprint initialized"} 