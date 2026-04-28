# Repository Structure

Tài liệu này mô tả cấu trúc thư mục chuẩn của dự án và quy tắc đặt tên file. **Mọi thành viên phải tuân theo** để đảm bảo sự nhất quán khi merge code.

```
A20-App-007/
├── docs/                        # Tài liệu dự án
│   ├── PRD.md                   # Product Requirements Document
│   ├── REPO_STRUCTURE.md        # File này
│   ├── GIT_WORKFLOW.md          # Quy trình Git & branching
│   ├── ENDPOINTS.md             # Tài liệu API cho Frontend
│   └── DATA_DICTIONARY.md       # Mô tả các trường dữ liệu LMS/SIS
│
├── src/                         # Toàn bộ source code của ứng dụng
│   ├── agents/                  # Các node & logic LangGraph
│   │   ├── agent.py             # Điểm khởi tạo chính của AI Agent (Compiled Graph)
│   │   ├── nodes/               # Định nghĩa các node trong graph (SQL, Plan, Respond)
│   │   ├── state.py             # Định nghĩa AgentState (schema trạng thái)
│   │   ├── schemas.py           # Pydantic schemas cho logic Agent
│   │   └── utils.py             # Các hàm tiện ích (masking, serialization)
│   │
│   ├── api/                     # Backend API (FastAPI)
│   │   ├── routes/              # Các route handlers (Thin controllers)
│   │   ├── services/            # Lớp dịch vụ (Business logic & Orchestration)
│   │   ├── models/              # Pydantic request/response models
│   │   ├── auth.py              # Cấu hình FastAPI-Users & RBAC
│   │   ├── lifecycle.py         # Startup/Shutdown hooks & DI providers
│   │   └── main.py              # Điểm khởi động FastAPI app
│   │
│   ├── database/                # Database abstraction layer
│   │   ├── engines/             # Database engines (DuckDB)
│   │   ├── algorithms/          # Anomaly detection algorithms
│   │   ├── manager.py           # DatabaseManager orchestrator
│   │   └── factory.py           # Registry & creation logic
│   │
│   ├── baml_src/                # BAML source files (AI prompt engineering)
│   ├── baml_client/             # Generated BAML client
│   │
│   ├── telemetry/               # Logging & tracking (Custom JSON logger)
│   ├── tools/                   # Custom tools cho Agent
│   └── utils/                   # Shared utilities (env, etc.)
│
├── data/                        # Local data (CSV mocks)
│
├── tests/                       # Toàn bộ hệ thống test (pytest)
│   ├── conftest.py              # Shared fixtures & DI overrides
│   ├── api/                     # Integration tests cho API endpoints
│   ├── database/                # Unit tests cho DB engines/algorithms
│   └── agents/                  # Tests cho agent nodes & PII masking
│
├── scripts/                     # Scripts vận hành & mock data generation
│
├── .env.example                 # Template biến môi trường
├── pyproject.toml               # Cấu hình dự án (dùng uv)
├── AGENTS.md                    # Quy tắc bắt buộc khi dùng AI coding agents
├── GEMINI.md                    # Hướng dẫn dự án cho AI agents
├── JOURNAL.md                   # Nhật ký hàng tuần
└── WORKLOG.md                   # Ghi chép quyết định kỹ thuật & ADR
```

## Quy tắc đặt tên file

| Loại file | Convention | Ví dụ |
| :--- | :--- | :--- |
| Python module | `snake_case.py` | `alert_service.py` |
| Tài liệu | `UPPER_CASE.md` | `REPO_STRUCTURE.md` |
| Test file | `test_<tên_module>.py` | `test_alerts_routes.py` |

## Quy tắc đặt tên thư mục

*   Luôn dùng **chữ thường** và **dấu gạch dưới** (`snake_case`).
*   Các thư mục code trong `src/` phải có file `__init__.py`.

## Những gì KHÔNG được commit

Xem file `.gitignore` để biết danh sách đầy đủ. Các mục quan trọng nhất:
*   File `.env` (chứa API keys thật)
*   Thư mục `.ai-log/`
*   Thư mục `.venv/`, `__pycache__/`, `.pytest_cache/`
*   File DuckDB local (`*.db`)
