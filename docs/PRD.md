# PRD: Project "Pulse" – The Early Warning Engine

## 1. Problem Definition: The "Context Gap"

Academic advisors in universities are facing **Intervention Lag**. They operate in a **reactive** state. By the time an advisor manually merges a Learning Management System (LMS) report (showing low engagement) with a Student Information System (SIS) report (showing financial aid probation), the "at-risk" student has usually already checked out mentally or failed their midterms. 

A hard-coded dashboard is insufficient as it requires efforts of filtering, and looking back to past data to find out, for example, if the student's is "at-risk" or just a normal bad week. Instead, an AI integrated system do not provide charts, it provides insights, and judgements.

Hypothesis: Helping advisors moving from **Retrospective Reporting**  (what happened?) to **Proactive Intervention** (who need help *right now*?) would improve students engagement.

---

## 2. Examples of Paint Points

* **Example A: The "Silent Slider"** A student has a 3.8 GPA (SIS data). However, their LMS login frequency has dropped by 70% in the last 14 days (LMS data). Because these data points live in different tabs, the advisor congratulates the student on their GPA while missing the looming mental health crisis or burnout.
* **Example B: The "Prerequisite Trap"** An advisor has 15 minutes per student during registration. They miss the fact that a student is enrolling in "Organic Chemistry II" despite a "D" in the prerequisite two years ago, because that grade is buried in a 10-page transcript PDF while the current schedule is in a web portal.
* **Example C: The Monday Morning Rush** After a weekend of failed quizzes, an advisor needs to prioritize which 10 out of 300 students to call. Currently, they spend Monday morning (4 hours) "cleaning data." By the time they start calling on Tuesday, the window for a "course-correct" conversation has shrunk.

---

## 3. Core Value Proposition
1.  **Instant Synthesis:** Eliminate the "Merge & Pivot Table" workflow. Move from data gathering to "Actionable Insights" in a few minutes.
2.  **Risk Prioritization:** Automatically rank students based on multi-source red flags (e.g., Low LMS activity + Financial Aid Warning + Historic low grade in current subject).

---

## 4. Business Metrics (Success Criteria)
* **Time-to-Insight (TTI):** Reduce the time taken to identify "Top 10 At-Risk Students" from **4 hours to 5 minutes.**
* **Intervention Lead Time:** Increase the average number of days between "Risk Detection" and "Student Outreach."
* **Advisor Satisfaction Score:** A binary "Yes/No" on whether the AI-generated "Student Brief" was accurate enough to lead a 1:1 session without checking Excel.

---

## 5. Functional Requirements



### 5.1. The "Unified Feed" (RAG-based)
The application allows advisors to **upload CSV exports** from their SIS and LMS. 
* **AI Agent:** Processes the CSVs using a RAG (Retrieval-Augmented Generation) pattern.
* **The "So What?" Layer:** The agent doesn't just show data; it writes a 3-sentence summary for each student: *"GPA is high, but quiz scores dropped 40% this week. This is a new pattern for this student."*

### 5.2. Natural Language Query (The "Socratic" Advisor)
A chat interface where the advisor asks:
* *"Who has a GPA below 2.0 but hasn't logged into the LMS in 5 days?"*
* *"Summarize the academic hurdles for [Student Name] based on their history."*

---

## 6. Development Plan

**Team Composition:**
1.  **Lead Dev:** Backend, LLM Prompt Engineering, Data Parsing.
2.  **Product/Frontend:** UI/UX, Data Mapping, CSV Sanitization.
3.  **Data/QA:** Prompt Validation, Logic Testing, Documentation.

| Week | Focus | Deliverable |
| :--- | :--- | :--- |
| **Week 1** | **The Pipeline** | Build CSV parsers for common LMS/SIS formats (Canvas/Banner). Set up the Vector DB. |
| **Week 2** | **The Reasoning** | Develop the "Risk Logic" prompt. Create the agent that can "cross-reference" two different files. |
| **Week 3** | **The Interface** | Build a clean, "Zero-Training" UI. Run a "Stress Test" with 1,000 student rows. |

---

## 7. Technical Feasibility & Constraints
* **Feasibility:** High. By using LLMs (GPT-4o or Claude 3.5) with structured data (CSV), we bypass the need for expensive API integrations with legacy University systems.
* **Constraint:** Data Privacy. All PII (Personally Identifiable Information) must be anonymized or handled via local LLM processing to ensure FERPA compliance (for the MVP, we use "Student ID" instead of "Full Name").
