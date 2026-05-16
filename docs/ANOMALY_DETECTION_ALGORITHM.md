# Adaptive Anomaly Detection Algorithm (Tier 1)

This document provides a technical deep-dive into the Adaptive Evaluation Engine used to identify at-risk students. Unlike traditional static threshold systems (e.g., "flag if score < 40"), this engine utilizes **Volatility-Aware Adaptive Learning** to detect subtle performance shifts before they result in failure.

## 1. Core Philosophy
The algorithm is built on the principle that **risk is relative**. A student who usually scores 95 but drops to 65 is statistically more "at-risk" than a student who consistently scores 65. The engine models each student's unique "normal" and flags deviations from that personalized baseline.

## 2. Mathematical Framework
The engine processes data through four primary signal layers:

### A. Regularized Peer-Normalization ($z_{peer}$)
Before looking at a student's history, we must understand how they compare to their peers in a specific week. We calculate a regularized Z-Score:

$$z_{peer} = \frac{x - \mu_{course}}{\sqrt{\sigma_{course}^2 + \lambda_{peer}}}$$

*   **$\lambda_{peer}$ (Regularization):** Prevents extreme scores in small classes from skewing results. It acts as a "shrinkage" factor that pulls scores toward the mean when class data is noisy.

### B. Adaptive Personalized Drift ($p_{signal}$)
This is the heart of the "Subtle Anomaly" detection. We maintain an **Exponentially Weighted Moving Average (EWMA)** of each student's $z_{peer}$ to track their "Personal Baseline."

When a new score arrives, we calculate the **Drift**:
$$\text{Drift} = z_{peer} - \text{EWMA}_{baseline}$$

We then normalize this drift by the student's **Personal Volatility**:
$$\text{Normalized Drift} = \frac{\text{Drift}}{\sqrt{\text{EWMA}_{variance} + \lambda_{stability}}}$$

*   **Why this matters:** If a student is usually very consistent, a 10-point drop is a massive signal. If a student's grades are always erratic, that same 10-point drop is treated as "noise" and ignored (Low False Positives).

### C. Multi-week Trend Persistence
The engine tracks the "velocity" of a student's performance. A single bad week might be a fluke, but a sustained negative trend is an anomaly.
*   **Trend Score:** An EWMA of the student's drifts over multiple weeks.
*   **Threshold:** If the trend score falls below `-0.3`, an `ELEVATED` alert is triggered even if the absolute score is still passing.

### D. Systemic Breadth
The engine looks across all courses a student is taking in a given week. 
$$\text{Breadth} = \frac{\text{Domains with negative drift}}{\text{Total Domains}}$$
If a student is dropping in **all** their classes simultaneously, the risk level is automatically escalated to `CRITICAL`, as this indicates a systemic life issue rather than a specific course difficulty.

---

## 3. Risk Classification Policy

The engine classifies students into three categories based on the signals above:

| Status | Logic / Trigger | Purpose |
| :--- | :--- | :--- |
| **NORMAL** | Normalized Drift > -1.5 AND $z_{peer}$ > -1.5 | Student is performing within expected personal and peer bounds. |
| **ELEVATED** | Normalized Drift < -1.5 OR Trend < -0.3 | **Early Warning.** The student's performance is declining significantly from their own history. |
| **CRITICAL** | Normalized Drift < -2.2 OR $z_{peer}$ < -2.0 | **Urgent Intervention.** A sudden collapse or falling significantly behind the entire peer group. |

---

## 4. Adaptive Learning (Weighted Feedback)
The algorithm "learns" from the student over time, but it is careful not to learn "bad habits." 
*   **Normal Weeks:** The engine updates the student's baseline fully.
*   **Elevated Weeks:** The engine slows down learning (0.2x speed) so the baseline doesn't drop too quickly.
*   **Critical Weeks:** The engine **stops learning** (0.0x). We assume the student's current performance is an anomaly, not their "new normal," preserving their high baseline for future comparisons.

## 5. Summary of Benefits
1.  **High Recall:** Catches "A" students who drop to "C" levels before they fail.
2.  **Low False Positives:** Ignores erratic students whose performance fluctuates within their "normal" noisy range.
3.  **Cold Start Protection:** Uses Peer-Normalization until enough personalized data is gathered to build a reliable baseline.
