# System Architecture: The Activation Engine (v2.0)

## 1. Executive Summary & Goals
The Activation Engine is designed to solve the "triple-point failure" in university interventions: student friction (academic shame), advisor inertia (check-the-box mentality), and the feedback void (invisible high-impact work). By combining AI-driven "Empathy Nudges" with a gamified performance engine, it shifts the focus from passive monitoring to proactive coaching.

The primary goals are:
- **Proactive Engagement**: Triggering student action through AI-generated, curiosity-based communication.
- **Incentivized Performance**: Using gamification to turn advisor tasks into high-impact, visible achievements.
- **Operational Resiliency**: Establishing a robust, clean architecture to support long-term maintainability and scale.

## 2. System Architecture
The system follows a **Clean Architecture** model to ensure separation of concerns, improve testability, and decouple core business logic from frameworks and external services.

### Core Layers:
- **Presentation**: Handles the delivery mechanism (FastAPI routes), Pydantic DTOs for request/response validation, and FastAPI-specific dependency injection.
- **Application**: Implements **Strict CQRS** (Command Query Responsibility Segregation). 
  - **Commands**: Encapsulate state-mutating use cases (e.g., `ApproveNudgeCommand`, `UpdateStatusCommand`).
  - **Queries**: Encapsulate read-only operations (e.g., `GetLeaderboardQuery`, `FetchStudentMetricsQuery`).
- **Domain**: The core of the system, containing pure business rules.
  - **Entities**: Business objects with identity (e.g., `Student`, `Advisor`, `Alert`).
  - **Value Objects**: Immutable types (e.g., `ImpactScore`, `Status`, `SatisfactionLevel`).
  - **Repository Interfaces**: Ports defined for the infrastructure layer to implement.
- **Infrastructure**: Contains concrete implementations of abstractions defined in the Application and Domain layers.
  - **Database**: DuckDB managed via the Repository pattern (SQLAlchemy).
  - **Extern**: External service adapters, including LLM clients and email drafting services.

## 3. Domain Model & Gamification
The system's value proposition is centered on the **Impact Score** formula, which rewards advisors for effective and timely interventions:
- **Nudge Velocity**: Points awarded based on the speed of nudge approval (Target: <4 hours).
- **Activation Rate**: Points awarded when students engage with the nudge (e.g., booking a meeting).
- **Recovery Bonus**: High-weight points awarded for measurable student performance improvement.

The gamification engine is encapsulated within the Domain layer (`GamificationService`) and executed through Application commands.

## 4. Infrastructure & Integrations
### LLM Orchestration
To prevent framework lock-in, LLM orchestrators (e.g., Agents, BAML) are treated as infrastructure adapters. The Application layer interacts with these through domain-defined interfaces (Ports), ensuring that the underlying AI technology can be updated or swapped without affecting core logic.

### Data Persistence
The system utilizes DuckDB for its high-performance analytical capabilities on local student data. All database interactions are strictly isolated within the Repository layer in `infrastructure/repositories/`, preventing SQL leakage and ensuring that the Domain layer remains agnostic of persistence details.

## 5. API Contracts & Resiliency
To ensure operational stability and prevent duplicate side effects (such as sending multiple emails or awarding points twice during a retry), all state-mutating API endpoints support **Idempotency Keys**.

- **Implementation**: Keys are provided by the client and stored in an `idempotency_keys` table to safeguard against network retries.
- **Boundary Enforcement**: Boundary invariants are enforced through structural linters and layer-specific exception mapping (e.g., mapping a Domain `NotFound` error to a Presentation `HTTP 404`).

## 6. Modernization & Refactoring Roadmap
The system is currently undergoing a phased modernization:
1. **Phase 1: Stabilization Boundaries**: Establishing layer-specific exceptions, refining the directory skeleton, and introducing idempotency for critical actions.
2. **Phase 2: Structural Refactoring**: Moving core logic from API routes into Application-layer CQRS interactors and isolating SQLAlchemy models within the Infrastructure layer.
3. **Phase 3: Scale & Hardening**: Consolidating dependency injection and implementing structural linters to prevent future architectural regressions.
