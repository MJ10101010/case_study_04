from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from models import SurveySubmission, StoredSurveyRecord
import hashlib
import json
from pathlib import Path
from storage import append_json_line

STORAGE_FILE = Path("survey_submissions.jsonl")


app = Flask(__name__)
CORS(app)

@app.get("/time")
def get_time():
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now()
    payload = {
        "utc_iso": now_utc.isoformat(),
        "local_iso": now_local.isoformat(),
        "server": "flask-warmup",
    }
    return jsonify(payload), 200

@app.get("/ping")
def ping():
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })

def sha256_hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    current_utc = datetime.now(timezone.utc)

    # Exercise 1: capture User-Agent
    user_agent = request.headers.get("User-Agent", submission.user_agent)

    # Exercise 2: hash PII
    hashed_email = sha256_hash(submission.email)
    hashed_age = sha256_hash(str(submission.age))

    # Exercise 3: submission_id
    submission_id = submission.submission_id
    if not submission_id:
        timestamp_str = current_utc.strftime("%Y%m%d%H")
        hash_input = submission.email + timestamp_str
        submission_id = sha256_hash(hash_input)

    # Build stored record
    record = StoredSurveyRecord(
        name=submission.name,
        consent=submission.consent,
        rating=submission.rating,
        comments=submission.comments,
        email_hash=hashed_email,
        age_hash=hashed_age,
        submission_id=submission_id,
        user_agent=user_agent,
        received_at=current_utc,
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")
    )

    # Store record safely (convert with Pydantic JSON method)
    append_json_line(record.dict())  # for Pydantic v2
    # If your env is Pydantic v1: use record.json() instead of model_dump_json()

    # Return submission_id as confirmation
    return jsonify({"status": "ok"}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
