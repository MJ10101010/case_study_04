from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
# Importing the updated models
from models import SurveySubmission, StoredSurveyRecord
# New import for cryptographic hashing (required for exercises 2 and 3)
import hashlib

app = Flask(__name__)
@app.get("/time")
def get_time():
	now_utc = datetime.now(timezone.utc)
	# Local time according to the server’s timezone
	now_local = datetime.now()
	payload = {
		"utc_iso": now_utc.isoformat(),
		"local_iso": now_local.isoformat(),
		"server": "flask-warmup",
	}
	return jsonify(payload), 200

@app.get("/ping")
def ping():
    """Simple health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })

def sha256_hash(data: str) -> str:
    """Helper function to compute the SHA-256 hash of a string."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    try:
        # Validate incoming data using the SurveySubmission model (raw data)
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    # --- Server-side Data Capture and Transformation ---
    
    current_utc = datetime.now(timezone.utc)
    
    # Exercise 1: Capture User-Agent from header (preferred) or payload
    # Note: request.headers.get("User-Agent") captures the standard browser header.
    user_agent = request.headers.get("User-Agent", submission.user_agent)

    # Exercise 2: Protect PII with Hashing
    hashed_email = sha256_hash(submission.email)
    # Ensure age (int) is converted to a string before hashing
    hashed_age = sha256_hash(str(submission.age))

    # Exercise 3: Submission ID Logic
    submission_id = submission.submission_id
    
    if not submission_id:
        # Compute ID: sha256(email + YYYYMMDDHH)
        timestamp_str = current_utc.strftime("%Y%m%d%H")
        hash_input = submission.email + timestamp_str
        submission_id = sha256_hash(hash_input)

    # --- Create the final StoredSurveyRecord using transformed data ---
    
    # Note: We explicitly pass the fields required by StoredSurveyRecord,
    # ensuring raw PII (email, age) is replaced by hashes.
    record = StoredSurveyRecord(
        # Non-PII fields from submission
        name=submission.name,
        consent=submission.consent,
        rating=submission.rating,
        comments=submission.comments,
        
        # Hashed PII fields
        email_hash=hashed_email,
        age_hash=hashed_age,
        
        # New/Generated fields
        submission_id=submission_id,
        user_agent=user_agent,
        
        # Server Metadata
        received_at=current_utc,
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")
    )
    
    # Store the final record (which only contains hashes, not raw PII)
    append_json_line(record.dict())

    # Return the generated ID to the client
    return jsonify({"status": "ok"}), 201

if __name__ == "__main__":
	app.run(host="0.0.0.0", port = 5000, debug = True)