# PRD: The Activation Engine (v2.0 - Gamified Edition)

## 1. Problem Statement
The current university intervention model suffers from a **triple-point failure**:
1.  **Student Friction:** High-risk students are paralyzed by "academic shame," avoiding support until it’s too late.
2.  **Advisor Inertia:** Academic Advisors (AAs) are buried under "risk lists" without a sense of urgency or progress, leading to a "check-the-box" mentality.
3.  **The Feedback Void:** High-impact intervention work is invisible, unrewarded, and lacks the competitive drive that spurs excellence.

**The Goal:** Shift the culture from *passive monitoring* to *proactive coaching* by using AI to trigger student action and Gamification to ignite advisor performance.

---

## 2. Target Users
*   **Academic Advisors (AAs):** The primary users who approve nudges and conduct sessions.
*   **Student Success Managers/Deans:** Admin users who oversee advisor performance and department-wide retention.
*   **The Student (End-Beneficiary):** Receives the AI-generated "Empathy Nudges."

---

## 3. User Stories

| Role | Requirement | Goal/Benefit |
| :--- | :--- | :--- |
| **Advisor** | I want to see a "Impact Leaderboard" comparing my intervention stats with peers. | To spark healthy competition and validate that my work is moving the needle. |
| **Advisor** | I want to earn "Impact Points" for every student who moves from "At-Risk" to "Stable." | To feel a sense of progression and professional achievement beyond just "clearing a list." |
| **High level manager** | I want to identify "Champion Advisors" (top 10%) based on student response rates. | To study their methods and scale their "tone of voice" or workflow to others. |
| **Student** | I want to receive data-backed nudges that feel supportive, not punitive. | To lower the psychological barrier to asking for help. |

---

## 4. MVP Scope: The "Impact & Action" Suite

### Phase 1: The AI Core (Non-Negotiable)
*   **Pattern-Based Detection:** Ingests CSV data to establish individual baselines. Flags students when they deviate by $>20\%$ from their personal norm (not just class average).
*   **The Empathy Nudge:** AI drafts "Curiosity-based" emails (e.g., *"Hey, we noticed your quiz pattern changed—is everything okay?"*).
*   **1-Click Approval:** A "Tinder-style" queue for AAs to swipe/approve AI-drafted nudges in bulk.

### Phase 2: The Gamified Leaderboard (The New Requirement)
*   **The Impact Score Formula:** Points are awarded for:
    *   **Nudge Velocity:** Time taken to approve a pending nudge (shorter = higher points).
    *   **Activation Rate:** % of students who clicked the Calendly link from your nudge.
    *   **Recovery Bonus:** Points awarded if a flagged student’s grades improve in the next data ingest.
*   **Peer Leaderboard:** A weekly "Top Intervenors" table visible to all AAs in the department.
*   **Achievement Badges:** Visual markers like *"First Responder"* (fastest average response) or *"The Closer"* (highest student recovery rate).

---

## 5. Success Metrics

### Primary Metrics (North Star)
*   **Advisor Engagement Rate:** Frequency of login and "Action Queue" clearance (Target: 90% daily).
*   **Student Self-Referral Rate:** % of students who book a meeting within 48 hours of a nudge (Target: $>30\%$).

### Gamification Metrics
*   **Leaderboard Volatility:** How often the top 5 positions change (indicates active competition).
*   **Average Response Lead-Time:** Reduction in time between "AI Flag" and "AA Nudge Sent" (Target: $<4$ hours).

---

## 6. Dependencies and Constraints

*   **Data Latency (Dependency):** The system is only as good as the CSV uploads. If LMS data is only uploaded monthly, the "nudge" is no longer relevant.
*   **Privacy & Sensitivity (Constraint):** The Leaderboard must show **Advisor Names** but strictly **Anonymized Student Data**. We compete on *our* performance, not on student failures.
*   **Toxic Competition (Risk):** Excessive gamification may lead to "nudge spamming." 
    *   *Mitigation:* Cap points for "Nudges Sent" and weight points heavily toward "Student Outcomes" (Recovery Bonus).
*   **FERPA Compliance:** All AI processing must be done within secure environments; no PII (Personally Identifiable Information) should be used to train external LLMs.

---

> **Sharpness Note:** This engine doesn't just track failure; it gamifies the *rescue*. By making the "Activation Gap" a visible metric, we turn a chore into a challenge.

