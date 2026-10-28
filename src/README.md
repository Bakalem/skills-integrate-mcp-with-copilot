# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teacher sign-in for student registration management
- Publicly view activity participants

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Generate a strong signing secret and set it in the server environment:

   ```
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   export ADMIN_SESSION_SECRET="<paste the generated value here>"
   export ADMIN_COOKIE_SECURE=false
   ```

   The environment variable must contain at least 32 characters. Keep the signing
   secret private. Set `ADMIN_COOKIE_SECURE=true` and use HTTPS in production.

3. Create a teacher account. The password is prompted securely and saved as a
   salted PBKDF2 hash in the ignored local file `src/teachers.json`:

   ```
   python src/create_teacher.py <username>
   ```

   Run this command from the repository root. Do not commit `src/teachers.json`.
   The example file `src/teachers.example.json` contains no accounts.

4. Run the application from the repository root:

   ```
   uvicorn src.app:app --reload
   ```

5. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                        |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------ |
| GET    | `/activities`                                                     | Get all activities and their current participants (public)        |
| GET    | `/admin/session`                                                  | Check whether a teacher session is active                          |
| POST   | `/admin/login`                                                    | Sign in with a teacher username and password                       |
| POST   | `/admin/logout`                                                   | Sign out and clear the session cookie                              |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Register a student (teacher session required)                      |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher session required)                  |

Teacher sessions use an HTTP-only, SameSite=Strict cookie that expires after
eight hours. Credentials are stored locally as salted PBKDF2 hashes; passwords
are never stored in plaintext. Login and registration management are unavailable
until `ADMIN_SESSION_SECRET` and at least one teacher account are configured.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity data is stored in memory and resets when the server restarts. Teacher
credential hashes are stored separately in the local, git-ignored
`src/teachers.json` file.
