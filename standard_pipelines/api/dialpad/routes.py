from flask import Blueprint, jsonify, request
from standard_pipelines.api.dialpad.services import DialpadAPIManager

bp = Blueprint("dialpad", __name__)

@bp.route("/transcript/<call_id>", methods=["GET"])
def get_transcript(call_id):
    api_config = {"api_key": request.headers.get("X-API-Key")}
    manager = DialpadAPIManager(api_config)
    transcript, user_ids, names = manager.transcript(call_id)
    return jsonify({
        "transcript": transcript,
        "user_ids": user_ids,
        "names": names
    })
