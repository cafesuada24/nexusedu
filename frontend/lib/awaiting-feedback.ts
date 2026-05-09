/**
 * Frontend-only store for the "student concern" indicator.
 *
 * When a student clicks "Chưa giải quyết xong" we persist their comment so
 * the advisor's card can show a red warning indicator until they ack it.
 * The case status itself is owned by the backend (PENDING_REVIEW / FAILED).
 */

const CONCERN_KEY = "nexusedu.feedback_concerns";

export type StudentConcern = { comment: string; submitted_at: number };

function readConcerns(): Record<string, StudentConcern> {
    if (typeof window === "undefined") return {};
    try {
        const raw = window.localStorage.getItem(CONCERN_KEY);
        if (!raw) return {};
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
        return {};
    }
}

function writeConcerns(map: Record<string, StudentConcern>) {
    if (typeof window === "undefined") return;
    try {
        window.localStorage.setItem(CONCERN_KEY, JSON.stringify(map));
    } catch {
        /* ignore quota errors */
    }
}

export function setStudentConcern(caseId: string, comment: string): void {
    const map = readConcerns();
    map[caseId] = { comment, submitted_at: Math.floor(Date.now() / 1000) };
    writeConcerns(map);
}

export function getStudentConcern(caseId: string): StudentConcern | null {
    return readConcerns()[caseId] ?? null;
}

export function getAllStudentConcerns(): Record<string, StudentConcern> {
    return readConcerns();
}

export function clearStudentConcern(caseId: string): void {
    const map = readConcerns();
    if (map[caseId]) {
        delete map[caseId];
        writeConcerns(map);
    }
}
