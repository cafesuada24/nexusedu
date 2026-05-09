/**
 * Frontend-only override store for cases marked as "awaiting student feedback".
 *
 * Backend chưa hỗ trợ trạng thái AWAITING_FEEDBACK, nên khi advisor click
 * "Giải quyết" chúng ta KHÔNG gọi backend resolve (sẽ làm case nhảy thẳng
 * sang RESOLVED). Thay vào đó lưu case_id vào localStorage và frontend
 * override `intervention_status` thành "awaiting_feedback" cho đến khi
 * sinh viên submit đánh giá.
 *
 * Khi backend bổ sung endpoint thực sự, xoá file này và cập nhật mutation.
 */

const STORAGE_KEY = "nexusedu.awaiting_feedback_case_ids";

function read(): Set<string> {
    if (typeof window === "undefined") return new Set();
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) return new Set();
        const arr = JSON.parse(raw);
        return new Set(Array.isArray(arr) ? arr.filter((x) => typeof x === "string") : []);
    } catch {
        return new Set();
    }
}

function write(set: Set<string>) {
    if (typeof window === "undefined") return;
    try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...set]));
    } catch {
        /* ignore quota errors */
    }
}

export function isAwaitingFeedback(caseId: string | null | undefined): boolean {
    if (!caseId) return false;
    return read().has(caseId);
}

export function markAwaitingFeedback(caseId: string): void {
    const set = read();
    set.add(caseId);
    write(set);
}

export function clearAwaitingFeedback(caseId: string): void {
    const set = read();
    if (set.delete(caseId)) write(set);
}

export function getAwaitingFeedbackSet(): Set<string> {
    return read();
}

/* -------- Student concern store -------------------------------------------
 * When a student clicks "Chưa giải quyết xong" we persist their comment so
 * the advisor's card can show a red warning indicator. Stored per case_id.
 * ------------------------------------------------------------------------ */

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
