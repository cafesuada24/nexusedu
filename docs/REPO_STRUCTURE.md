# Repository Structure

Tài liệu này mô tả cấu trúc thư mục chuẩn của dự án và quy tắc đặt tên file. **Mọi thành viên phải tuân theo** để đảm bảo sự nhất quán khi merge code.

```
A20-App-007/
├── docs/                        # Tài liệu dự án (bạn đang đọc file này)
│   ├── PRD.md                   # Product Requirements Document
│   ├── REPO_STRUCTURE.md        # File này
│   ├── GIT_WORKFLOW.md          # Quy trình Git & branching
│   └── DATA_DICTIONARY.md       # Mô tả các trường dữ liệu LMS/SIS
│
├── src/                         # Toàn bộ source code của ứng dụng
│   ├── agents/                  # Các node & logic LangGraph
│   │   ├── llms.py              # Khởi tạo và cấu hình LLM models
│   │   ├── nodes.py             # Định nghĩa tất cả các node trong graph
│   │   ├── state.py             # Định nghĩa AgentState (schema trạng thái)
│   │   ├── schemas.py           # Pydantic schemas cho input/output
│   │   └── utils.py             # Các hàm tiện ích dùng chung
│   │
│   ├── api/                     # Backend API (FastAPI)
│   │   ├── routes/              # Các endpoint API
│   │   ├── models/              # Request/Response models
│   │   └── main.py              # Điểm khởi động FastAPI app
│   │
│   ├── prompts/                 # Prompt templates (versioned)
│   │   └── v1/
│   │       ├── planner/
│   │       ├── sql_generator/
│   │       └── responder/
│   │
│   ├── tools/                   # Custom tools cho Agent
│   │
│   ├── etl/                     # Scripts xử lý & nạp dữ liệu
│   │   ├── csv_parser.py        # Parser cho file CSV từ LMS/SIS
│   │   └── risk_engine.py       # Logic xác định sinh viên rủi ro
│   │
│   ├── telemetry/               # Logging & tracking
│   └── agent.py                 # Điểm khởi động chính của AI Agent
│
├── data/                        # Database files (KHÔNG commit file .db lên git)
│
├── tests/                       # Unit & integration tests
│   ├── test_agent_graph.py
│   ├── test_api.py
│   └── test_robust_outputs.py
│
├── scripts/                     # Scripts vận hành (CI/CD, hooks)
│   └── setup_hooks.sh
│
├── .env.example                 # Template biến môi trường (KHÔNG chứa secret thật)
├── pyproject.toml               # Cấu hình dự án & dependencies (dùng uv)
├── AGENTS.md                    # Quy tắc bắt buộc khi dùng AI coding agents
├── GEMINI.md                    # Hướng dẫn tổng quan dự án cho AI agents
├── JOURNAL.md                   # Nhật ký hàng tuần (cập nhật mỗi thứ Hai)
└── WORKLOG.md                   # Ghi chép quyết định kỹ thuật & ADR
```

## Quy tắc đặt tên file

| Loại file | Convention | Ví dụ |
| :--- | :--- | :--- |
| Python module | `snake_case.py` | `risk_engine.py` |
| Tài liệu | `UPPER_CASE.md` | `REPO_STRUCTURE.md` |
| Prompt template | `system.txt` hoặc `task.txt` | `system.txt` |
| Test file | `test_<tên_module>.py` | `test_agent_graph.py` |

## Quy tắc đặt tên thư mục

*   Luôn dùng **chữ thường** và **dấu gạch dưới** (`snake_case`).
*   Các thư mục mới trong `src/` phải có file `__init__.py`.

## Những gì KHÔNG được commit

Xem file `.gitignore` để biết danh sách đầy đủ. Các mục quan trọng nhất:
*   File `.env` (chứa API keys thật)
*   Thư mục `.ai-log/` (được push tự động bởi git hook riêng)
*   File `*.db` (database file nhị phân, quá lớn và thường xuyên thay đổi)
*   Thư mục `__pycache__/` và `.venv/`
