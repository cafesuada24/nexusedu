# API Documentation for Frontend Integration (v1)

**Base URL:** `/api/v1`

---

## 1. Data Ingestion
**Endpoint:** `POST /data/ingest`
**Description:** Ingests validated SIS and LMS data, or flexible custom datasets. Automatically triggers the anomaly detection engine. Requires `admin:all` role.

### Request Body (JSON)
```json
{
  "batch_id": "string (uuid)",
  "upload_timestamp": "string (iso-8601)",
  "data_sources": [
    {
      "source_type": "sis",
      "records": [
        {
          "sid": "student-uuid",
          "student_name": "Full Name",
          "email": "email@example.edu"
        }
      ]
    },
    {
      "source_type": "lms",
      "records": [
        {
          "sid": "student-uuid",
          "course_id": "CS101",
          "course_name": "Computer Science 1",
          "test_type": "quiz",
          "score": 85.5,
          "timestamp": 1713500000,
          "academic_year": 3,
          "semester": 2
        }
      ]
    },
    {
      "source_type": "custom",
      "table_name": "library_usage",
      "records": [
        { "sid": "student-uuid", "visits": 10 }
      ]
    }
  ]
}
```

---

## 2. Kanban Alert Dashboard
**Endpoint:** `GET /alerts`
**Description:** Retrieves all students with an active intervention (`intervention_status != 'none'`). Use this to populate the Kanban board.

### Query Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `status` | `string` | **Optional.** Filter by state: `new`, `sent`, `booked`, `supporting`, `resolved`, `expired`. |

### Response (200 OK)
```json
[
  {
    "sid": "string",
    "student_name": "string",
    "email": "string",
    "current_risk_status": "Significant Drop",
    "intervention_status": "new"
  }
]
```

---

## 3. Generate Email Draft (Async)
**Endpoint:** `POST /alerts/{sid}/draft`
**Description:** Triggers AI to generate a personalized, empathetic nudge email draft. This is an asynchronous operation.

### Request Body (Optional JSON)
```json
{
  "booking_link": "https://calendly.com/your-link"
}
```

### Response (202 Accepted)
```json
{
  "job_id": "string (uuid)",
  "status": "processing"
}
```
*Note: Use the `job_id` to poll the `/jobs/{job_id}` endpoint for the result.*

---

## 4. Job Status Polling
**Endpoint:** `GET /jobs/{job_id}`
**Description:** Polls for the status and results of a background job (e.g., email drafting or agent queries).

### Response (200 OK)
```json
{
  "job_id": "string",
  "status": "completed",
  "result": {
    "sid": "string",
    "recipient_email": "student@university.edu",
    "subject": "Checking in on your academic progress",
    "body": "Hi Student Name, I noticed..."
  },
  "error": null
}
```

---

## 5. Send Nudge Email
**Endpoint:** `POST /alerts/{sid}/send`
**Description:** Dispatches the finalized email and moves the student's Kanban state to `sent`.

### Request Body (JSON)
```json
{
  "body": "The finalized email content to send."
}
```

---

## 6. Update Intervention Status
**Endpoint:** `PATCH /alerts/{sid}/status`
**Description:** Manually advances a student through the Kanban lifecycle.

### Request Body (JSON)
```json
{
  "status": "booked" 
}
```
*Valid statuses: `none`, `new`, `sent`, `booked`, `supporting`, `resolved`, `expired`.*

---

## 7. AI Agent Query (Async)
**Endpoint:** `POST /query`
**Description:** Interact with the AI agent for analysis and summarization. This is an asynchronous operation.

### Request Body (JSON)
```json
{
  "query": "Identify students with significant performance drops.",
  "thread_id": "optional-session-id"
}
```

### Response (202 Accepted)
```json
{
  "job_id": "string (uuid)",
  "status": "processing"
}
```

---

## 8. Advisor Leaderboard
**Endpoint:** `GET /advisors/leaderboard`
**Description:** Retrieves the advisor leaderboard based on gamification points.

### Query Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `time_window` | `string` | **Optional.** One of: `weekly`, `monthly`, `semester`, `all_time` (default). |

### Response (200 OK)
```json
[
  {
    "advisor_id": "string",
    "name": "string",
    "total_points": 150,
    "actions_count": 12
  }
]
```

---

### Key Integration Notes
1.  **PII Safety:** The AI Agent and Draft generator use `sid` for identification. The backend securely injects student names into drafts using `{{STUDENT_NAME}}` and `{{ADVISOR_LINK}}` interpolation.
2.  **Async Pattern:** Endpoints returning a `job_id` (202 Accepted) require polling `/jobs/{job_id}` until the status is `completed`.
3.  **Anomaly Logic:** The anomaly engine runs automatically after every `/data/ingest` call. New problems appear in the `new` column of the Kanban board.
