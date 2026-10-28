"""
High School Management System API

FastAPI application for viewing extracurricular activities and managing
student registrations.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=current_dir / "static"), name="static")

TEACHERS_FILE = current_dir / "teachers.json"
TEACHERS_EXAMPLE_FILE = current_dir / "teachers.example.json"
SESSION_COOKIE = "admin_session"
SESSION_MAX_AGE = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 600_000


class TeacherCredentials(BaseModel):
    username: str
    password: str


def _session_secret() -> bytes:
    secret = os.environ.get("ADMIN_SESSION_SECRET")
    if not secret or len(secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="Teacher sign-in requires an ADMIN_SESSION_SECRET of at least 32 characters",
        )
    return secret.encode("utf-8")


def _load_teachers() -> list[dict[str, str]]:
    credentials_file = TEACHERS_FILE if TEACHERS_FILE.exists() else TEACHERS_EXAMPLE_FILE
    try:
        data = json.loads(credentials_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Unable to read teacher credentials from {credentials_file}") from error

    teachers = data.get("teachers") if isinstance(data, dict) else None
    if not isinstance(teachers, list):
        raise RuntimeError(f"Invalid teacher credentials format in {credentials_file}")
    if any(
        not isinstance(teacher, dict)
        or not all(
            isinstance(teacher.get(key), str)
            for key in ("username", "salt", "password_hash")
        )
        for teacher in teachers
    ):
        raise RuntimeError(f"Invalid teacher credentials format in {credentials_file}")
    try:
        if any(
            len(bytes.fromhex(teacher["salt"])) < 16
            or len(bytes.fromhex(teacher["password_hash"]))
            != hashlib.sha256().digest_size
            for teacher in teachers
        ):
            raise ValueError("Invalid credential length")
    except ValueError as error:
        raise RuntimeError(f"Invalid teacher credentials format in {credentials_file}") from error
    return teachers


def _create_session(username: str) -> str:
    payload = json.dumps(
        {"username": username, "expires": int(time.time()) + SESSION_MAX_AGE},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        _session_secret(), encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def _session_username(token: str | None) -> str | None:
    if not token or "." not in token:
        return None

    encoded_payload, encoded_signature = token.rsplit(".", 1)
    secret = _session_secret()
    try:
        expected_signature = hmac.new(
            secret, encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        payload = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
        session = json.loads(payload)
    except ValueError:
        return None

    if not hmac.compare_digest(signature, expected_signature):
        return None
    if not isinstance(session, dict) or not isinstance(session.get("username"), str):
        return None
    if not isinstance(session.get("expires"), int) or session["expires"] <= time.time():
        return None
    return session["username"]


def _get_current_teacher(request: Request) -> str:
    username = _session_username(request.cookies.get(SESSION_COOKIE))
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher sign-in required")
    return username


def _password_matches(password: str, teacher: dict[str, str]) -> bool:
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(teacher["salt"]),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return hmac.compare_digest(password_hash, teacher["password_hash"])


@app.get("/admin/session")
def get_admin_session(request: Request):
    return {"username": _session_username(request.cookies.get(SESSION_COOKIE))}


@app.post("/admin/login")
def admin_login(credentials: TeacherCredentials, response: Response):
    _session_secret()
    teachers = _load_teachers()
    if not teachers:
        raise HTTPException(status_code=503, detail="No teacher accounts are configured")

    for teacher in teachers:
        if teacher["username"] == credentials.username and _password_matches(
            credentials.password, teacher
        ):
            response.set_cookie(
                SESSION_COOKIE,
                _create_session(credentials.username),
                max_age=SESSION_MAX_AGE,
                httponly=True,
                secure=os.environ.get("ADMIN_COOKIE_SECURE", "true").lower() == "true",
                samesite="strict",
                path="/",
            )
            return {"username": credentials.username}

    raise HTTPException(status_code=401, detail="Invalid username or password")


@app.post("/admin/logout")
def admin_logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict")
    return {"message": "Signed out"}

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, _: str = Depends(_get_current_teacher)):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    _: str = Depends(_get_current_teacher),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
