# NexusEdu: AI-Powered Student Support System

**NexusEdu** is a next-generation platform designed to empower academic advisors with AI-driven insights, automated workflows, and comprehensive student tracking. By bridging the gap between raw institutional data (SIS/LMS) and actionable interventions, NexusEdu ensures no student falls through the cracks.

---

## Links & Resources
- **Live Demo**: [Application URL](https://a20-app-007.vercel.app)
- **Pitch Deck**: [Link to Pitch Deck](https://docs.google.com/presentation/d/14oAJp1MUL2MmgAbsKcX1-nsxUtN04VDo/edit?usp=sharing&ouid=100201767592210803393&rtpof=true&sd=true)
- **Video Demo**: [Link to Video Demo](https://youtu.be/ihI0M3DhjL0?feature=shared)

---

## Key Features

### AI-Driven Intelligence
- **Automated Case Analysis**: Utilizes specialized algorithms to identify at-risk students based on indicators such as low grades or high absenteeism rates.
- **Smart Email Drafting**: Generates personalized, tone-aware intervention emails with PII masking for data security.
- **Tone Evaluation**: Analyzes and refines advisor communications to ensure the most effective outreach.
- **Deterministic Prompt Chains**: High-performance AI processing refactored from complex graph models for maximum reliability.

### Advisor Workflow (Kanban)
- **Centralized Alert Center**: Manage student cases through a responsive, localized (Vietnamese) Kanban board.
- **Unified Student Profiles**: View academic history, engagement trends, and contact logs in a single, modal-driven interface.
- **Real-time Synchronization**: Instant updates via WebSockets (Redis PubSub) when case statuses change.

### Scheduling & Appointments
- **Availability Management**: Advisors can manage working hours and time-off with automatic slot calculation.
- **Conflict-Free Booking**: Students can book appointments through a public-facing portal with built-in conflict detection.

### Gamification
- **Point Ledger System**: Advisors earn points for successful student interventions and milestones.
- **Leaderboard**: Track and reward top-performing advisors based on impact and engagement.

---

## Tech Stack

### Frontend
- **Framework**: [Next.js 16](https://nextjs.org/) (React 19, TypeScript)
- **Styling**: [Tailwind CSS 4](https://tailwindcss.com/), [Shadcn UI](https://ui.shadcn.com/)
- **State Management**: [TanStack Query v5](https://tanstack.com/query)
- **Charts**: [Recharts](https://recharts.org/)
- **Real-time**: WebSockets (Redis PubSub)

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12)
- **Database**: [SQLite](https://www.sqlite.org/) (default local) / [PostgreSQL](https://www.postgresql.org/) (production ready)
- **Analytics**: [DuckDB](https://duckdb.org/) for local ingestion and data analysis
- **ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Background Tasks**: [ARQ](https://github.com/samuelcolvin/arq) (Redis-backed)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Package Manager**: [uv](https://github.com/astral-sh/uv)

### AI & Security
- **Interfacing**: [BAML](https://www.boundaryml.com/)
- **Security**: [Presidio](https://microsoft.github.io/presidio/) (PII Masking), JWT Authentication
- **Models**: gemini-3.1-flash-lite

---

## Project Structure

```bash
├── src/
│   ├── application/    # CQRS Handlers, DTOs, and Interfaces
│   ├── core/           # Configs, logging, and centralized constants
│   ├── domain/         # Core entities, value objects, and exceptions (DDD)
│   ├── infrastructure/ # Persistence, Redis, and external adapters
│   └── presentation/   # FastAPI entry points, schemas, and DI
├── frontend/
│   ├── app/            # Next.js App Router (pages & actions)
│   ├── components/     # Reusable UI components
│   ├── hooks/          # React Query and specialized hooks
│   ├── lib/            # Shared logic, API client, and constants
│   ├── public/         # Static assets (logos, icons)
│   └── styles/         # Global styles and Tailwind configuration
├── terraform/          # Cloud deployment config
├── scripts/            # CLI tools for dev (seeding, user creation)
├── alembic/            # Database migration history
├── data/               # Sample institutional datasets (SIS/LMS)
├── tests/              # Backend testcases
└── docs/               # System architecture and product documentation
```

---

## Getting Started

### Prerequisites
- Python 3.12+ (managed by `uv`)
- Node.js 20+
- Docker & Docker compose
- Terraform

### 1. Repository Setup
```bash
git clone https://github.com/a20-ai-thuc-chien/A20-App-007.git
cd A20-App-007

# Create a virtual environment with Python 3.12
uv venv --python 3.12

# Activate the virtual environment
source .venv/bin/active

# Install backend dependencies
uv sync

# Configure environment
cp .env.example .env
```

### 2. Database Initialization
```bash
# Initialize database schema and seed default users
uv run alembic upgrade head

# WARNING: This resets the database (deletes data/app.db) and seeds default accounts:
# - Admin: dev@gmail.com / dev
# - Advisor: adv@gmail.com / adv
uv run scripts/reset.sh
```

### 3. Frontend Setup
```bash
cd frontend

# Install project dependencies
npm install
```

---

## Running the Application

### Backend
```bash
# Start all backend services
export ENV=dev # prod for production
make start

# Stop all services
make stop
```

### Frontend
```bash
cd frontend

# Start the development server
npm run dev
```

---

## Documentation
- **[JOURNAL.md](./docs/JOURNAL.md)**: Follow the product journey and weekly milestones.
- **[WORKLOG.md](./docs/WORKLOG.md)**: Review technical decisions (ADRs) and architectural changes.
- **[Architecture](./docs/SYSTEM-ARCHITECTURE.md)**: Deep dive into the DDD and CQRS implementation.

---

## Team
- **Hồ Sỹ Minh Hà**: Backend & AI Lead & DevOps
- **Đặng Hồ Hải & Trịnh Đức An**: Frontend & UX Specialist

---
