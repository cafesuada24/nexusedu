# API Documentation for Frontend Integration (v1)

**Base URL:** `/api/v1`

---

## 1. Data Ingestion
**Endpoint:** `POST /data/ingest`
**Description:** Ingests validated SIS and LMS data, or flexible custom datasets. Automatically triggers the anomaly detection engine.

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
    "sid": "uuid string",
    "student_name": "string",
    "email": "string",
    "current_risk_status": "Significant Drop",
    "intervention_status": "new"
  }
]
```

---

## 3. Update Intervention Status
**Endpoint:** `PATCH /alerts/{sid}/status`
**Description:** Advances a student through the Kanban lifecycle.

### Path Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `sid` | `string` | The unique student identifier. |

### Request Body (JSON)
```json
{
  "status": "sent" 
}
```
*Valid statuses: `none`, `new`, `sent`, `booked`, `supporting`, `resolved`, `expired`.*

---

### Key Integration Notes
1.  **PII Safety:** The AI Agent is instructed to use `sid` for identification in its thought process. Only request `email` or `student_name` if you specifically need contact details for the UI.
2.  **Anomaly Logic:** The anomaly engine runs automatically after every `/data/ingest` call. New problems will appear in the `new` column of your Kanban board automatically.
3.  **One-Problem-Rule:** If a student is already in an active intervention (e.g., `supporting`), new data uploads will update their `current_risk_status` but will **not** move them back to `new` until the current intervention is marked `resolved`, `expired`, or `none`.
