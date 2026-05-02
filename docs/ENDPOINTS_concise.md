# Agent Assistant API Endpoints (v1)

This document provides a concise, AI-friendly reference for integrating with the backend.

## Base URL
`http://localhost:8000/api/v1`

---

## Authentication & Authorization

The API uses **JWT Bearer Tokens**.
- **Login**: `POST /auth/jwt/login` (Body: `username`, `password`)
- **Header**: `Authorization: Bearer <token>`

### Roles & Scopes
Endpoints are protected by **Scopes**. A user's **Role** (`admin`, `advisor`, `viewer`) determines their available scopes.

| Role | Description | Scopes |
| :--- | :--- | :--- |
| **admin** | Full System Access | All Scopes (`*`) |
| **advisor** | Primary User | `alerts:*`, `query:execute`, `jobs:read`, `advisors:read` |
| **viewer** | Read-only | `alerts:read`, `jobs:read`, `advisors:read` |

---

## 1. Authentication

### Register
`POST /auth/register`
- **Body**: `{"email": "string", "password": "string"}`
- **Note**: New users default to the `viewer` role.

### Login
`POST /auth/jwt/login`
- **Form Data**: `username`, `password`
- **Response**: `{"access_token": "string", "token_type": "bearer"}`

---

## 2. Agent Interaction

### Submit Natural Language Query
`POST /query`
- **Scope**: `query:execute`
- **Body**:
  ```json
  {
    "query": "Show me student grades for 'CS101' in a bar chart.",
    "thread_id": "optional_session_id",
    "metadata": {}
  }
  ```
- **Response** (202 Accepted): `{"job_id": "uuid", "status": "processing"}`

### Poll Job Status
`GET /jobs/{job_id}`
- **Scope**: `jobs:read`
- **Response**:
  ```json
  {
    "job_id": "uuid",
    "status": "completed | failed | processing",
    "progress": 0,
    "created_at": "iso_timestamp",
    "started_at": "iso_timestamp | null",
    "completed_at": "iso_timestamp | null",
    "result": {},
    "error": "string | null"
  }
  ```

---

## 3. Alerts (Kanban Dashboard)

### Get Active Alerts
`GET /alerts`
- **Scope**: `alerts:read`
- **Query Params**: `status` (optional: `new`, `sent`, `booked`, `supporting`, `resolved`, `expired`)
- **Response**: `List[AlertStudent]` (includes `active_case_id`)

### Get Case History
`GET /alerts/{sid}/cases`
- **Scope**: `alerts:read`
- **Response**: `List[Case]` (History of all at-risk periods for student)

### Get Case Details
`GET /alerts/cases/{case_id}`
- **Scope**: `alerts:read`
- **Response**: `CaseDetails` (Includes status, timestamps, and associated emails)

### Update Intervention Status
`PATCH /alerts/{sid}/status`
- **Scope**: `alerts:write`
- **Body**: `{"status": "new_status"}`

### Generate AI Email Draft
`POST /alerts/{sid}/draft`
- **Scope**: `alerts:write`
- **Body**: `{"booking_link": "optional_url"}`
- **Response**: `JobAcceptedResponse` (Poll status via `/jobs/{job_id}`)

### Send Nudge Email
`POST /alerts/{sid}/send`
- **Scope**: `alerts:write`
- **Body**: `{"body": "final_email_content"}`

---

## 4. User & Advisor Management

### Get Current User Profile
`GET /users/me`
- **Requirement**: Active Token
- **Response**: `UserRead` (includes `role`)

### List All Users
`GET /users`
- **Scope**: `users:read` (Admin Only)

### Update User Role
`PATCH /users/{user_id}`
- **Scope**: `users:write` (Admin Only)
- **Body**: `{"role": "admin | advisor | viewer"}`

### Get Advisor Leaderboard
`GET /advisors/leaderboard`
- **Scope**: `advisors:read`
- **Query Params**: `time_window` (`weekly`, `monthly`, `semester`, `all_time`)

---

## 5. Data & System

### Ingest Data
`POST /data/ingest`
- **Scope**: `data:ingest` (Admin Only)
- **Body**: `DataIngestionRequest` (Multi-source SIS/LMS/Custom data)

### Health Check
`GET /health`
- **Public**: Check database and AI engine connectivity.

---

## Key Schemas

### AlertStudent
```json
{
  "sid": "string",
  "student_name": "string",
  "email": "string",
  "current_risk_status": "string",
  "intervention_status": "string",
  "active_case_id": "uuid | null"
}
```

### QueryResponse
```json
{
  "answer": "string",
  "tables": "list[list[dict]] | null",
  "visualizations": "list[plotly_json] | null",
  "session_id": "string"
}
```
