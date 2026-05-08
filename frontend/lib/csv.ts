/**
 * CSV parser + student-risk analyzer tied to the fixed student-test schema:
 *
 *   sid, student_name, course_id, course_name, test_type, email,
 *   last_notified_timestamp, last_notified_satisfaction,
 *   score, timestamp, academic_year, semester
 *
 * Scores are on a 0–100 scale. `last_notified_timestamp` is Unix seconds
 * (0 = never contacted). `last_notified_satisfaction` is 0 = no response /
 * unhappy, 1 = positive response.
 *
 * Each CSV row is one test result, so several rows can belong to the same
 * student (sid). The analyzer groups rows by `sid` and derives per-student
 * risk from their aggregated test performance.
 */

export type Problem = "failed_final" | "failed_midterm" | "low_average";
export type Severity = "low" | "medium" | "high";
export type TestType = "middle_semester" | "final_semester" | "other";

export type TestRow = {
    courseId: string;
    courseName: string;
    testType: TestType;
    score: number;
    /** Unix seconds. */
    timestamp: number;
    academicYear: number;
    semester: number;
};

export type StudentRow = {
    /** Student id (`sid`). */
    id: string;
    name: string;
    email: string;
    /** Most-recent academic year observed for this student. */
    academicYear: number;
    /** Unix seconds of the most recent notification, or `null` if never contacted. */
    lastContactedAt: number | null;
    /** Latest known satisfaction flag (0 = no response / unhappy, 1 = positive). */
    lastNotifiedSatisfaction: number;
    tests: TestRow[];
    averageScore: number;
    failedCount: number;
    hasFailedFinal: boolean;
    hasFailedMidterm: boolean;
    problems: Problem[];
    severity: Severity;
};

export type ParsedDataset = {
    students: StudentRow[];
    /** Number of unique students (by `sid`). */
    totalStudents: number;
    /** Total number of test rows read from the CSV. */
    totalTests: number;
    /** Arithmetic mean of `score` across all test rows. */
    averageScore: number;

    highRisk: number;
    mediumRisk: number;
    lowRisk: number;

    /** Number of emails to draft — equals `highRisk` (one email per high-risk student). */
    draftEmails: number;

    problemCounts: Record<Problem, number>;
    /** Number of at-risk students keyed by academic_year ("1" | "2" | ...). */
    yearRisk: Record<string, number>;

    headers: string[];
};

export const problemLabels: Record<Problem, string> = {
    failed_final: "Rớt thi cuối kỳ",
    failed_midterm: "Rớt thi giữa kỳ",
    low_average: "Điểm TB thấp",
};

/* ----------------------------------------------------------------------- */
/*  CSV parser                                                             */
/* ----------------------------------------------------------------------- */

type RawCsv = { headers: string[]; rows: Record<string, string>[] };

function parseCsv(text: string): RawCsv {
    if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);

    const lines: string[][] = [];
    let field = "";
    let row: string[] = [];
    let inQuotes = false;

    for (let i = 0; i < text.length; i++) {
        const ch = text[i];

        if (inQuotes) {
            if (ch === '"') {
                if (text[i + 1] === '"') {
                    field += '"';
                    i++;
                } else {
                    inQuotes = false;
                }
            } else {
                field += ch;
            }
            continue;
        }

        if (ch === '"') {
            inQuotes = true;
        } else if (ch === ",") {
            row.push(field);
            field = "";
        } else if (ch === "\n" || ch === "\r") {
            if (ch === "\r" && text[i + 1] === "\n") i++;
            row.push(field);
            field = "";
            if (row.length > 1 || row[0] !== "") lines.push(row);
            row = [];
        } else {
            field += ch;
        }
    }

    if (field !== "" || row.length > 0) {
        row.push(field);
        if (row.length > 1 || row[0] !== "") lines.push(row);
    }

    if (lines.length === 0) return { headers: [], rows: [] };

    const headers = lines[0].map((h) => h.trim());
    const rows = lines
        .slice(1)
        .map((line) => {
            const obj: Record<string, string> = {};
            headers.forEach((h, idx) => {
                obj[h] = (line[idx] ?? "").trim();
            });
            return obj;
        })
        .filter((r) => Object.values(r).some((v) => v !== ""));

    return { headers, rows };
}

/* ----------------------------------------------------------------------- */
/*  Helpers                                                                */
/* ----------------------------------------------------------------------- */

const normalize = (s: string) =>
    s
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9]/g, "");

function findCol(headers: string[], candidates: string[]): string | null {
    const norm = headers.map((h) => ({ orig: h, norm: normalize(h) }));
    for (const c of candidates) {
        const nc = normalize(c);
        const exact = norm.find((h) => h.norm === nc);
        if (exact) return exact.orig;
    }
    for (const c of candidates) {
        const nc = normalize(c);
        const partial = norm.find((h) => h.norm.includes(nc));
        if (partial) return partial.orig;
    }
    return null;
}

function toNumber(raw: string | undefined): number | undefined {
    if (!raw) return undefined;
    const cleaned = raw.replace("%", "").replace(",", ".").trim();
    if (cleaned === "") return undefined;
    const n = Number(cleaned);
    return Number.isFinite(n) ? n : undefined;
}

function toInteger(raw: string | undefined): number | undefined {
    const n = toNumber(raw);
    return n !== undefined ? Math.round(n) : undefined;
}

/**
 * Treats Unix-seconds `0`, missing values, or sentinel strings ("None"/"null")
 * as "never notified".
 */
function parseLastNotified(raw: string | undefined): number | null {
    if (!raw) return null;
    const v = raw.trim();
    if (!v) return null;
    const lower = v.toLowerCase();
    if (lower === "none" || lower === "null" || lower === "n/a") return null;
    const n = Number(v);
    if (!Number.isFinite(n) || n <= 0) return null;
    return n;
}

function normalizeTestType(raw: string | undefined): TestType {
    if (!raw) return "other";
    const v = raw.trim().toLowerCase();
    if (v === "middle_semester" || v === "midterm" || v === "middle") {
        return "middle_semester";
    }
    if (
        v === "final_semester" ||
        v === "final" ||
        v === "final_exam" ||
        v === "exam"
    )
        return "final_semester";
    return "other";
}

/* ----------------------------------------------------------------------- */
/*  Risk classification                                                    */
/* ----------------------------------------------------------------------- */

/**
 * Thresholds tuned for a 100-point grading scale:
 *  - score < 50    → failed the exam
 *  - avg   < 50    → clearly at-risk overall (high severity)
 *  - 50 ≤ avg < 65 → borderline, worth flagging (medium severity)
 */
const FAIL_SCORE = 50;
const HIGH_AVG = 50;
const LOW_AVG = 65;

/**
 * Read configurable high-average threshold from localStorage key
 * 'nexusedu:riskThreshold'.
 *
 * Expected storage format: a JSON array where the first element is the numeric
 * threshold (e.g. [50, ...]). Falls back to `HIGH_AVG` when:
 *  - window / localStorage are unavailable (server-side)
 *  - parsing fails or value is not a finite number
 *
 * This helper is intentionally small and defensive to be safe in SSR builds.
 */
function getConfiguredHighAvg(): number {
    const defaultVal = HIGH_AVG;
    try {
        if (typeof window === "undefined" || !window.localStorage)
            return defaultVal;
        const raw = window.localStorage.getItem("nexusedu:riskThreshold");
        if (!raw) return defaultVal;
        const parsed = JSON.parse(raw) as unknown;
        if (Array.isArray(parsed) && parsed.length > 0) {
            const n = Number((parsed as any)[0]);
            if (Number.isFinite(n)) return n;
        }
        if (typeof parsed === "number" && Number.isFinite(parsed))
            return parsed;
        if (typeof parsed === "string") {
            const n = Number(parsed);
            if (Number.isFinite(n)) return n;
        }
    } catch {
        // ignore and fall back
    }
    return defaultVal;
}

function classifyStudent(tests: TestRow[]): {
    problems: Problem[];
    severity: Severity;
    averageScore: number;
    failedCount: number;
    hasFailedFinal: boolean;
    hasFailedMidterm: boolean;
} {
    if (tests.length === 0) {
        return {
            problems: [],
            severity: "low",
            averageScore: 0,
            failedCount: 0,
            hasFailedFinal: false,
            hasFailedMidterm: false,
        };
    }

    const sum = tests.reduce((acc, t) => acc + t.score, 0);
    const averageScore = sum / tests.length;
    const failedCount = tests.filter((t) => t.score < FAIL_SCORE).length;
    const hasFailedFinal = tests.some(
        (t) => t.testType === "final_semester" && t.score < FAIL_SCORE,
    );
    const hasFailedMidterm = tests.some(
        (t) => t.testType === "middle_semester" && t.score < FAIL_SCORE,
    );

    const problems: Problem[] = [];
    if (hasFailedFinal) problems.push("failed_final");
    if (hasFailedMidterm) problems.push("failed_midterm");
    if (averageScore < LOW_AVG) problems.push("low_average");

    let severity: Severity = "low";
    // Use configured threshold for "high" severity so Settings slider can control it.
    const configuredHighAvg = getConfiguredHighAvg();
    if (hasFailedFinal || averageScore < configuredHighAvg) {
        severity = "high";
    } else if (hasFailedMidterm || averageScore < LOW_AVG) {
        severity = "medium";
    }

    return {
        problems,
        severity,
        averageScore,
        failedCount,
        hasFailedFinal,
        hasFailedMidterm,
    };
}

/* ----------------------------------------------------------------------- */
/*  Public API                                                             */
/* ----------------------------------------------------------------------- */

// Matches the fixed schema used by NexusEDU (scores 0–100).

export const LMS_SAMPLE_CSV = `
activity_id,sid,course_id,course_name,test_type,score,timestamp,academic_year,semester,week
cadc6047-f882-4e8e-b1cd-e1a64edbb120,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Quiz,84.5,2022-05-14 15:26:29+00:00,1,1,1
b234ab3c-80e1-4bff-98f7-8546b2b8580c,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Final,82.0,2022-06-04 06:14:03+00:00,1,1,4
22dc864f-9bc1-473b-83e7-61bdff2cf026,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Midterm,74.5,2022-06-11 12:10:14+00:00,1,1,5
d67ee541-4898-4d61-a4f1-0da9dea3e8a3,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Assignment,78.5,2022-06-25 10:33:53+00:00,1,1,7
0d1fe010-b238-4ce3-bb6a-6048ff371b4f,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Assignment,74.0,2022-07-02 15:07:58+00:00,1,1,8
dd363034-572a-412b-80ae-09c14e3b44f0,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Assignment,75.5,2022-07-09 08:45:14+00:00,1,1,9
56466cf0-da1d-4014-81e9-ad4844a8f78d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Final,72.0,2022-07-16 22:30:12+00:00,1,1,10
a9a7aa25-3354-4b72-9ff2-7e086f3e0d35,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Quiz,74.5,2022-07-23 11:18:10+00:00,1,1,11
43f2b356-c4a6-4428-b615-bc58dd6d6473,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Final,71.0,2022-07-30 17:28:35+00:00,1,1,12
2c9aa874-5da0-4056-ba07-c7d7090f6412,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Midterm,75.5,2022-08-06 11:00:41+00:00,1,1,13
4e05550b-78ce-469d-964e-fde119e4dad8,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Final,76.0,2022-08-13 11:13:32+00:00,1,1,14
a6c57ab1-8523-4450-ba3b-ff3def9a23f6,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Assignment,77.5,2022-08-21 03:05:38+00:00,1,1,15
a46aa013-fde5-48b3-b48a-6489b2f2aade,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,80.0,2022-05-22 02:19:59+00:00,1,1,2
82077f19-fa65-4449-b943-8eac97947153,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,81.0,2022-06-04 12:36:21+00:00,1,1,4
454a91db-ead7-4eba-b416-67a02facf3d4,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,73.5,2022-06-25 17:45:02+00:00,1,1,7
5cb24060-1320-4a5f-9bb0-0a5395a073d8,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,77.0,2022-07-03 01:09:43+00:00,1,1,8
09f29f81-1459-4e76-86da-ae2b4ad951b4,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,80.5,2022-07-10 00:51:32+00:00,1,1,9
4084dadc-b930-4752-acac-b6604ef1cde5,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,77.0,2022-07-16 11:24:55+00:00,1,1,10
0efddd79-88b9-4b4e-abde-9d7697a5956d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,78.5,2022-07-23 11:34:05+00:00,1,1,11
14d49ec2-4a71-4da8-9ce3-9d68aaff8a4a,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,76.5,2022-08-20 16:48:41+00:00,1,1,15
9563fae1-027f-40a2-85eb-47f5ea9c3d0b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,69.0,2022-08-27 22:13:55+00:00,1,1,16
25bed607-0cf3-456e-8497-f7a3619d5b23,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Assignment,84.0,2022-05-21 13:52:18+00:00,1,1,2
2392d999-80c4-46df-818d-844ca1dcc14e,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Quiz,77.5,2022-06-11 18:58:12+00:00,1,1,5
6782dab5-c017-4a32-8ff6-e05ac6f56b29,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Final,80.0,2022-06-18 21:00:49+00:00,1,1,6
5edfdd5b-0baf-48e6-a2a4-5c17831d272b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Final,73.5,2022-06-25 11:59:46+00:00,1,1,7
517a490f-79c6-4806-9103-392dbc902a2f,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Midterm,80.0,2022-07-02 04:57:58+00:00,1,1,8
882ea2df-41da-4967-aa11-2b95c4845377,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Assignment,75.5,2022-07-09 19:47:45+00:00,1,1,9
c8ff1717-0716-4923-8088-853b6797aa4f,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Assignment,79.0,2022-07-16 11:37:56+00:00,1,1,10
de97fa92-882e-484b-96d8-48dffd62e412,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Final,70.5,2022-07-23 15:11:34+00:00,1,1,11
44008281-c988-4911-ac3a-cc2644e521b2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Quiz,70.0,2022-07-30 21:48:55+00:00,1,1,12
56e2981f-d162-44e3-b7a9-5ce0afbcbc55,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Final,73.5,2022-08-06 14:25:12+00:00,1,1,13
63ab19c2-bcbf-4f10-a28f-6083f3b09207,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Final,68.0,2022-08-14 00:33:45+00:00,1,1,14
a3ac9852-2937-4288-8d42-175567bd4ed5,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Final,67.5,2022-08-20 06:04:26+00:00,1,1,15
8720e607-0550-4f2f-803a-2f03fd97f0f9,2d943e4a-13c9-4324-90fc-4977145bdf1d,C102,Algorithms,Quiz,77.0,2022-08-28 00:56:07+00:00,1,1,16
2a8d98d1-c8a0-4148-a1dd-cb1bb2518cba,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Assignment,76.0,2022-05-21 20:15:11+00:00,1,1,2
56746df8-2bde-4318-a741-31161229bb07,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Final,76.5,2022-05-28 19:29:46+00:00,1,1,3
6ca86095-7a91-496b-aec0-b25622cfa046,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Assignment,80.0,2022-06-19 01:20:55+00:00,1,1,6
b7dce091-4041-45ac-ad78-fddccda303ae,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Quiz,79.0,2022-07-03 03:07:03+00:00,1,1,8
612e4949-6319-41ad-ae46-bc7f352099d8,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Quiz,80.5,2022-07-09 21:43:16+00:00,1,1,9
7a0add71-ce9b-49f8-8f0c-0438c3a2bce9,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Assignment,75.0,2022-07-16 20:38:29+00:00,1,1,10
cc2f6754-52f1-42d1-a680-857febb72b68,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Final,69.5,2022-07-23 10:30:08+00:00,1,1,11
88a0bb56-bc6b-46d9-91b3-6c4f759014d5,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Quiz,76.5,2022-08-06 12:54:17+00:00,1,1,13
508db650-33ba-4166-9fd0-524c58b06187,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Quiz,74.0,2022-08-13 13:41:35+00:00,1,1,14
002f5f88-5a4b-4827-b13a-52ebb35c4d28,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Assignment,71.0,2022-08-28 01:19:01+00:00,1,1,16
43bf3ad2-6fa5-45f4-b16d-f6e08abcda47,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Assignment,75.5,2022-05-28 06:43:46+00:00,1,1,3
dd23d2ff-edf9-4790-a28a-0ae5a34539ef,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Assignment,81.0,2022-06-04 23:31:22+00:00,1,1,4
6fa7787d-f088-4f6f-9798-0ecfc9693865,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Assignment,75.0,2022-06-18 06:05:39+00:00,1,1,6
541ef43d-fdba-4892-99c1-b606255b9faa,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Quiz,73.0,2022-07-02 20:54:51+00:00,1,1,8
5214a708-83c1-41d0-9a99-d17af6794bc1,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Midterm,78.0,2022-07-16 04:34:57+00:00,1,1,10
c81e2820-549a-4305-ad3d-7bafd9e8b63d,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Final,75.0,2022-07-30 09:49:33+00:00,1,1,12
5cd914bd-0843-4385-813c-0d577787f4b4,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Assignment,71.5,2022-08-06 22:59:27+00:00,1,1,13
cdb89cfa-18df-4c9f-acd6-8e8d3f9943b7,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Midterm,73.0,2022-08-13 09:47:31+00:00,1,1,14
b1dad5fa-c567-4534-93d0-a3b9112f5245,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Midterm,70.5,2022-08-20 10:21:22+00:00,1,1,15
857b9d65-bfc1-4494-8ad6-cfc7a45b4436,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Quiz,69.0,2022-08-27 16:34:04+00:00,1,1,16
16491f84-3382-474b-87aa-e4c9a5cc5412,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Assignment,75.5,2022-05-14 14:41:00+00:00,1,1,1
ce6443b8-12e4-4f16-91f6-c8e2609865c9,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Midterm,77.0,2022-06-04 19:25:05+00:00,1,1,4
59bf56de-ce9f-4218-b511-0113d82f9eb8,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Assignment,73.0,2022-07-02 12:44:36+00:00,1,1,8
4d9f0b43-46c2-40fc-94f0-dab34f5710e1,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Midterm,74.5,2022-07-09 10:37:03+00:00,1,1,9
6f8ae3b5-56e1-48a4-8173-a3a414e93dca,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Midterm,74.0,2022-08-14 02:43:29+00:00,1,1,14
8bd68ae7-e099-446e-bc5b-37fd1470461d,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Assignment,79.0,2022-05-21 23:04:08+00:00,1,1,2
00300a4f-45e5-4abd-b90b-ae17d1c39a1f,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Quiz,82.0,2022-06-05 00:36:41+00:00,1,1,4
d8f73130-e780-44d4-b714-543797287457,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Final,82.5,2022-06-11 14:52:40+00:00,1,1,5
3cf149ef-9bbc-4a90-b40d-d7862264760a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Assignment,73.0,2022-06-18 19:42:58+00:00,1,1,6
b117af92-39b4-4cb9-a122-3d796bf3a4e5,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Quiz,74.5,2022-06-25 21:50:39+00:00,1,1,7
b11f9349-5bc2-4fcf-8aac-558253ce8eb5,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Quiz,75.5,2022-08-06 21:30:40+00:00,1,1,13
7b724f34-48aa-4b38-b35b-8e3f755874f7,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Final,76.0,2022-08-13 13:06:29+00:00,1,1,14
0dbd2fe0-3f29-4ccb-b9e0-4e9ece4922d4,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Final,67.5,2022-08-21 03:40:05+00:00,1,1,15
e40bd811-2351-4f4e-a171-72d9626c29c2,52dbd570-530a-45e1-a2ee-6ce2520216e2,C105,Machine Learning,Quiz,79.5,2022-05-14 08:18:42+00:00,1,1,1
dd906662-6714-4079-a23b-765790545dfe,52dbd570-530a-45e1-a2ee-6ce2520216e2,C105,Machine Learning,Midterm,78.0,2022-05-22 01:19:43+00:00,1,1,2
ce020010-6f21-4e6a-86d4-df5aa6bcd32d,52dbd570-530a-45e1-a2ee-6ce2520216e2,C105,Machine Learning,Quiz,75.5,2022-05-29 00:12:12+00:00,1,1,3
c1f34e05-3c99-409b-b0b0-3d0b8a989a45,52dbd570-530a-45e1-a2ee-6ce2520216e2,C105,Machine Learning,Midterm,77.0,2022-06-04 12:30:01+00:00,1,1,4
5a1f39c8-82ad-48f9-bf21-dbae20884043,52dbd570-530a-45e1-a2ee-6ce2520216e2,C105,Machine Learning,Quiz,78.5,2022-06-11 15:50:55+00:00,1,1,5
5664ec33-e6e2-4c8f-9566-13a6bb48f253,52dbd570-530a-45e1-a2ee-6ce2520216e2,C105,Machine Learning,Quiz,74.0,2022-06-19 00:53:19+00:00,1,1,6
325b884d-f87e-433e-8979-1732ae548878,52dbd570-530a-45e1-a2ee-6ce2520216e2,C105,Machine Learning,Final,76.0,2022-07-02 07:54:01+00:00,1,1,8
09114274-22a4-4ad8-a12d-a542be934946,52dbd570-530a-45e1-a2ee-6ce2520216e2,C105,Machine Learning,Midterm,78.5,2022-07-09 08:23:15+00:00,1,1,9
5c7375d5-19cd-4d6d-8d88-9035fb651e55,52dbd570-530a-45e1-a2ee-6ce2520216e2,C105,Machine Learning,Midterm,75.0,2022-07-16 06:30:33+00:00,1,1,10
933c9aeb-aaac-4181-94e6-9aab1207c41b,52dbd570-530a-45e1-a2ee-6ce2520216e2,C105,Machine Learning,Quiz,78.5,2022-07-23 10:56:55+00:00,1,1,11
7db03d8b-110a-4fa3-b2a2-50d99ffa73e1,52dbd570-530a-45e1-a2ee-6ce2520216e2,C105,Machine Learning,Quiz,78.0,2022-07-31 02:28:46+00:00,1,1,12
14c38ebd-a409-4b27-87d2-3ca8132b58b2,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Quiz,74.5,2022-05-14 16:24:34+00:00,1,1,1
ef504dfc-b58e-42c6-a8b2-047334eccc84,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Quiz,80.0,2022-05-21 06:25:26+00:00,1,1,2
d94f6c55-cb38-4ee4-89f5-92389472127d,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Midterm,75.0,2022-06-04 05:17:59+00:00,1,1,4
551a1291-bab2-4267-aea6-737a1f25a5f4,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Assignment,82.5,2022-06-11 06:14:13+00:00,1,1,5
1d1ced5e-8b7d-44e7-a5d3-7d8e78d416f2,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Quiz,73.0,2022-06-19 03:07:12+00:00,1,1,6
a23ac3e4-0406-46a3-b2b5-da1318faa3c3,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Midterm,77.0,2022-07-02 10:05:47+00:00,1,1,8
ce4747fb-08cf-4c00-a249-6f0c7429654f,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Assignment,74.5,2022-07-09 09:09:58+00:00,1,1,9
b2bde180-ed14-401c-8898-71a2531e7480,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Assignment,73.0,2022-07-16 12:49:01+00:00,1,1,10
ebe948aa-4937-4fd9-9459-d9ee24df7402,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Assignment,72.5,2022-07-23 07:38:27+00:00,1,1,11
adfb3ea0-a296-43d3-a997-9a0350fcfed4,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Assignment,72.5,2022-08-06 13:57:03+00:00,1,1,13
12c7e362-31a9-4662-9790-5628b32fc909,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Midterm,72.5,2022-08-20 18:18:52+00:00,1,1,15
37d14b5e-9a7c-4e76-b0bf-7d7308c044c7,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Final,67.0,2022-08-27 11:44:23+00:00,1,1,16
e2c0673b-03b9-45bb-a79b-3e9963c9bb58,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Quiz,83.5,2022-05-14 06:39:49+00:00,1,1,1
27bb1967-ccca-4794-af12-0dde6aae2f2c,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Midterm,76.5,2022-05-28 20:37:50+00:00,1,1,3
b269959e-1e40-4d05-a0d3-04b45fbfa0e0,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Final,79.0,2022-06-04 14:31:45+00:00,1,1,4
31eaa3b0-bf4b-445d-86dc-e1ed59b68314,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Final,73.5,2022-06-11 13:05:10+00:00,1,1,5
0c825675-0cc0-49aa-97e9-0b0361c08020,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,81.5,2022-06-25 06:17:35+00:00,1,1,7
c7c889c5-9b99-489a-bbc1-2b9834815a73,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,79.0,2022-07-02 21:51:36+00:00,1,1,8
2726a90a-f0be-4382-b9bd-c86772e20be5,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,79.5,2022-07-09 05:03:35+00:00,1,1,9
6b19b93a-4c7b-4c2c-a2a3-7f013449cbcb,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Final,69.0,2022-07-30 14:16:17+00:00,1,1,12
6f303b39-b6ec-4363-a7b9-e94b6fa0fb62,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Final,68.5,2022-08-06 15:43:14+00:00,1,1,13
e1be73e6-a636-4574-8a6c-fb29d8e5d77a,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Midterm,75.0,2022-08-13 19:54:36+00:00,1,1,14
78f92563-4f47-4854-a4d5-fbcdc9499489,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,67.5,2022-08-20 10:48:05+00:00,1,1,15
ba5c717f-1030-47d2-a708-66aea0017c4a,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Final,76.0,2022-05-21 08:51:00+00:00,1,1,2
052180bb-476c-4610-b0c9-535b70fcb738,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Final,79.5,2022-05-28 12:24:10+00:00,1,1,3
e54ffb95-2589-4f84-8a61-5fdbc6c3406a,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Midterm,79.0,2022-06-04 07:28:05+00:00,1,1,4
c4788e57-377f-4059-9e23-f4795fcbab87,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Quiz,80.5,2022-06-11 11:49:33+00:00,1,1,5
ecf22311-1bd4-49ae-b9db-e926b79d9a27,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Midterm,76.0,2022-06-18 14:32:16+00:00,1,1,6
9fc681c4-77da-44a2-8f38-62c785030e9a,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Final,78.5,2022-06-25 12:09:20+00:00,1,1,7
f970e65a-6195-441b-9e5c-bfdb667afffd,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Assignment,73.5,2022-07-09 18:54:50+00:00,1,1,9
1a921b0d-e97c-4924-b7e1-bbe98d75630f,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Final,80.0,2022-07-16 19:00:22+00:00,1,1,10
49905ef6-3169-40dd-b14e-c8a056b5fb22,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Midterm,70.5,2022-07-23 06:44:30+00:00,1,1,11
dad49eee-a3c4-48a8-bdd6-13c1deb41704,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Assignment,70.0,2022-07-30 14:12:41+00:00,1,1,12
e4c76283-5c19-4c2e-a49b-b5b453823717,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Final,77.5,2022-08-06 05:57:17+00:00,1,1,13
b13aa807-2384-45e9-b3ae-a65f1cede0a0,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Assignment,74.0,2022-08-13 08:48:26+00:00,1,1,14
4742c9e0-bd8d-49d2-80cd-c4f5b332771c,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Assignment,69.5,2022-08-20 14:59:59+00:00,1,1,15
81cafbcf-6f30-4784-9567-b26725877f41,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Final,80.0,2022-05-22 02:46:33+00:00,1,1,2
dc49fdda-450c-4353-a2ea-3412343187ae,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Final,76.5,2022-05-28 09:33:50+00:00,1,1,3
e0cb388c-e40a-4c6d-bd4f-3c6ea39d96c8,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,79.0,2022-06-04 07:30:05+00:00,1,1,4
2a71b3ee-a586-4104-941b-7ccb01398721,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Quiz,73.5,2022-07-09 11:25:25+00:00,1,1,9
450748b2-340c-425c-886d-003d223f7173,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,73.0,2022-07-17 03:26:39+00:00,1,1,10
5c2eab26-1e4c-4c24-b359-954f2e3bdbe6,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,84.0,2022-05-21 16:03:36+00:00,1,1,2
cb83c546-3959-4d71-a932-d3d3caff7670,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Quiz,74.0,2022-06-18 19:29:21+00:00,1,1,6
f5cbcde3-3f8f-4337-8e8d-c509dfad0569,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Final,74.5,2022-06-25 06:59:21+00:00,1,1,7
53f9d34c-3be5-417d-a45b-624baa7c28b5,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,80.0,2022-07-03 00:11:29+00:00,1,1,8
46689306-0f01-4f5b-be53-319413f082ec,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Quiz,79.5,2022-07-24 00:25:40+00:00,1,1,11
a81fa316-4c35-4644-be85-f991b3d459d2,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,77.0,2022-08-13 15:09:12+00:00,1,1,14
ea90544f-adfd-4688-81d1-7dc1c0299001,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,73.5,2022-08-20 16:53:38+00:00,1,1,15
bfc2f900-1d38-4f75-8b06-137c3788543c,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Quiz,72.0,2022-08-27 23:08:53+00:00,1,1,16
97899219-b9c6-4813-af58-e1e407587e95,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Midterm,83.5,2022-05-14 06:15:33+00:00,1,1,1
e5cb98b1-fe98-4e4f-966a-e52792e5f31f,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Final,84.0,2022-05-21 21:16:09+00:00,1,1,2
83b01f95-4dc0-4b4d-89e5-798afabf80f5,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Final,80.5,2022-06-11 12:06:38+00:00,1,1,5
42de3227-a0ab-46a5-87f5-8fbe28e0cfa2,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Final,74.0,2022-06-18 15:10:31+00:00,1,1,6
243b0fda-11b2-46a5-abca-22078841fece,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Quiz,70.5,2022-07-09 04:22:20+00:00,1,1,9
d94a449c-f478-4e8c-91e1-0f646e552516,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Quiz,76.5,2022-08-07 02:23:47+00:00,1,1,13
1d72b4a7-f51b-4ae3-82b3-2609de3d5978,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Assignment,68.0,2022-08-13 18:47:46+00:00,1,1,14
337d2772-9494-4eef-8d0b-7d62b8ee0a03,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Final,77.0,2022-08-27 19:53:09+00:00,1,1,16
d7e3be4f-91f3-4590-9d41-3af75307799b,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,78.5,2022-05-28 14:36:15+00:00,1,1,3
58e92f24-ae22-477a-b4b2-1dec73cb73a5,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,79.5,2022-06-11 15:59:12+00:00,1,1,5
88949dd9-dcdc-4c2d-a91a-f67d86798996,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,72.0,2022-06-18 21:26:55+00:00,1,1,6
056e0c02-4428-41d1-85ca-c6e6f5ff0b9d,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,81.0,2022-07-02 10:06:45+00:00,1,1,8
73d046cd-943e-499f-90da-5991fc5c3d5c,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,74.5,2022-07-09 11:21:33+00:00,1,1,9
efb3976a-8dbb-43af-a4dc-2310a48efe62,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,70.0,2022-07-17 00:40:30+00:00,1,1,10
dceb6b50-f09c-4742-a352-1780b4920241,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,76.5,2022-07-24 01:36:45+00:00,1,1,11
e1326723-c37b-4fe7-9dae-e5accbf1a957,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,76.5,2022-08-20 21:04:26+00:00,1,1,15
98a9e842-8484-43c0-a736-fa1485735738,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,67.0,2022-08-27 22:56:19+00:00,1,1,16
0de41b5d-7b62-4a6e-aebf-8c9b31326648,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Quiz,74.5,2022-05-14 06:45:09+00:00,1,1,1
2ea65aea-6f33-4415-8e46-eb438e077a09,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,77.0,2022-05-22 01:15:43+00:00,1,1,2
a4200bfc-c6ad-447a-aee4-1c672633e8cc,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,83.0,2022-06-04 19:01:36+00:00,1,1,4
ca2cdcc9-e223-40cd-9621-9fbdce66f993,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,75.5,2022-06-11 14:03:41+00:00,1,1,5
478d7f76-c2fc-42b8-afc2-fb1bc02de696,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Midterm,79.0,2022-06-18 08:45:09+00:00,1,1,6
c0290ee3-f004-435e-b301-932c0d8f4465,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Midterm,75.5,2022-06-25 05:10:05+00:00,1,1,7
39a4560d-ff2a-46cd-bf38-8f4de2fb8770,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,78.0,2022-07-02 23:57:09+00:00,1,1,8
a3d5a729-50d2-4c99-a06d-dfd3a3c62bca,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,80.0,2022-07-17 00:20:33+00:00,1,1,10
37acb50d-9763-4d0b-bd89-70af3e3b1789,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,76.5,2022-07-24 02:29:35+00:00,1,1,11
019f591b-cb09-45c7-b3ce-318006fc86f1,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,74.0,2022-07-30 11:37:00+00:00,1,1,12
fbd15637-42fd-4b2f-8759-5db490e100cf,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Quiz,72.5,2022-08-06 12:22:47+00:00,1,1,13
962ecfe7-66b9-44bd-a087-26c1f2f472e6,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,71.5,2022-08-20 17:23:29+00:00,1,1,15
576a5299-e330-4442-b085-29ade10f5052,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Final,79.5,2022-05-14 21:33:12+00:00,1,1,1
c731ff13-f89a-4651-8d34-3f41c20c8137,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Midterm,82.0,2022-05-21 22:30:55+00:00,1,1,2
39f35310-073a-48b5-959b-684620f50915,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Assignment,83.5,2022-05-28 07:09:14+00:00,1,1,3
09df8c9f-25ce-4a14-a845-fd1ea4bb8335,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Midterm,75.0,2022-06-04 23:39:20+00:00,1,1,4
6c580809-a599-4e1e-af8e-85b059e3bc29,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Quiz,72.5,2022-06-11 23:23:47+00:00,1,1,5
1a77eef7-cfe3-44b8-b54c-be29f37411c7,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Assignment,73.0,2022-07-02 18:05:15+00:00,1,1,8
54539226-8d6a-4a92-99cc-401ede2de115,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Midterm,70.0,2022-07-16 07:55:12+00:00,1,1,10
417e203b-0ac5-4430-8ee9-f9958c728cb2,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Assignment,76.5,2022-07-23 14:02:18+00:00,1,1,11
dc288365-34c0-48be-8020-232d8b0922b5,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Final,74.0,2022-07-31 03:35:45+00:00,1,1,12
40f06459-7962-47fb-a18b-43ac83560740,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Final,75.0,2022-08-13 16:55:34+00:00,1,1,14
8720f568-d97e-4482-a412-0963321bec40,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Assignment,68.5,2022-08-21 02:12:49+00:00,1,1,15
65bb3761-0927-447a-adf0-3cebbd678405,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Midterm,67.0,2022-08-28 01:15:51+00:00,1,1,16
fbe3dc70-6348-424b-8bb6-7dd139bf2205,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,74.5,2022-05-15 03:20:54+00:00,1,1,1
938cc9d3-4b90-4afe-a72b-ba88640eb5a3,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,84.0,2022-05-21 04:19:44+00:00,1,1,2
45a519c1-f932-408d-8011-b01fb4f78dbb,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,76.5,2022-05-28 11:26:41+00:00,1,1,3
52313d84-2fd6-4f40-862a-453562b8fe82,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,82.0,2022-06-04 06:32:23+00:00,1,1,4
32c07758-01c6-4598-bdd2-39b8c6be1b25,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,73.0,2022-06-18 21:47:22+00:00,1,1,6
f8e30e73-1fa7-4567-8104-ea6b767f1e08,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,78.5,2022-06-26 02:49:48+00:00,1,1,7
7b0531e7-29b4-46af-b21d-2ab641afd418,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,74.5,2022-07-09 07:29:29+00:00,1,1,9
bf128f51-e595-4a35-a82e-cf74a646a4fa,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,72.0,2022-07-17 01:26:53+00:00,1,1,10
8c55e88f-925b-48bf-bb2d-40e92ade01bb,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,78.0,2022-07-30 19:25:16+00:00,1,1,12
7fe93bef-ee03-4697-aad1-6ddc383ae30c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,75.0,2022-08-14 02:50:15+00:00,1,1,14
45cfea3b-5c1e-49ba-bdd5-d573d818aa75,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,71.5,2022-08-20 11:16:22+00:00,1,1,15
31a48ffd-96de-48f6-9b2b-a18f8b3efb17,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Final,83.5,2022-05-15 01:22:32+00:00,1,1,1
b6621b6d-15cc-4917-9b16-d9cc1a40a0cb,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Quiz,82.5,2022-05-28 18:15:10+00:00,1,1,3
a462e441-8bef-46fb-8d95-d2335baf0e89,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Quiz,75.0,2022-06-04 23:41:37+00:00,1,1,4
e03066ac-b1dd-49c9-8e52-f95b83d09ab6,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Midterm,74.5,2022-06-12 03:32:22+00:00,1,1,5
da2d09cb-beca-46bb-904f-a9106c7d0c56,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Final,81.0,2022-06-18 20:49:28+00:00,1,1,6
0d913e89-c5ca-4a40-bc44-789674fc6bf3,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Final,71.5,2022-06-25 16:18:58+00:00,1,1,7
ce390107-9a53-45b9-a751-ddae624577d5,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Final,76.0,2022-07-02 12:27:49+00:00,1,1,8
ebaa9503-f4e2-464f-bb86-40b0aab9b7dc,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Final,75.0,2022-07-30 08:28:48+00:00,1,1,12
a7a1d88c-7ca9-48b5-af15-fca3c9cabb92,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Final,69.5,2022-08-06 12:03:22+00:00,1,1,13
b6bb0f99-b0ba-4fc9-9488-073ee1352bcc,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Quiz,75.0,2022-08-27 16:48:27+00:00,1,1,16
e861f3c6-ec42-4551-a7f9-91db3728da4f,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Midterm,74.0,2022-05-21 07:14:17+00:00,1,1,2
befbc8c6-2dea-46b5-83d9-ad2f366ce592,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Final,81.5,2022-05-28 21:42:15+00:00,1,1,3
a29ec462-a338-4a48-a7b0-25dae38c8d93,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Midterm,73.0,2022-06-04 05:09:09+00:00,1,1,4
42c514bb-773d-4757-a3b9-5e1b0ee825f1,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Quiz,74.5,2022-06-11 21:05:14+00:00,1,1,5
24c0296e-ccea-4693-86de-9bab28619a80,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Assignment,72.5,2022-06-25 05:13:44+00:00,1,1,7
e9a65e2d-2483-4600-b99b-1c32092c8a24,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Final,75.0,2022-07-02 09:34:04+00:00,1,1,8
166219b4-563f-4a1c-8407-248baec0e153,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Final,78.5,2022-07-09 20:29:08+00:00,1,1,9
2dcf3da9-bcd1-4035-8579-fb432de41725,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Midterm,72.0,2022-07-17 00:43:14+00:00,1,1,10
00e1b089-56cc-4107-aaed-6f86d817ec53,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Quiz,76.5,2022-07-23 15:44:06+00:00,1,1,11
4b6c2dd0-f1c2-40e7-8488-09d3846eb85d,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Midterm,77.0,2022-07-30 11:13:54+00:00,1,1,12
11ecb371-f38a-4979-aafa-0a00648f14b8,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Midterm,68.5,2022-08-07 01:36:25+00:00,1,1,13
bdceeea6-2306-4847-bad0-ade7c8473926,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Assignment,73.0,2022-08-13 13:12:17+00:00,1,1,14
15814607-5dd3-4a29-a557-176bab7ca7b2,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Final,69.5,2022-08-21 00:45:32+00:00,1,1,15
4df33eaa-1ea1-427a-98e9-af79552b93da,c3e25355-5f44-456e-b452-18efaf9cf6e5,C106,Software Engineering,Final,68.0,2022-08-27 18:05:06+00:00,1,1,16
0c33851e-0f5d-43e1-bc3c-a5805538e40b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Quiz,76.0,2022-06-19 03:13:58+00:00,1,1,6
23ca3df7-aba1-49e5-af28-35d1dd44591d,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Quiz,72.0,2022-07-02 18:50:11+00:00,1,1,8
090395c6-a06a-49a2-b108-330560459a7a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Quiz,77.5,2022-07-10 03:33:50+00:00,1,1,9
e003d767-6390-4a5a-95f3-136e94db31c4,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,76.0,2022-07-16 23:52:11+00:00,1,1,10
e88ee1ae-b07b-4e82-9d66-0b3dd498a9d0,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,76.5,2022-07-23 03:56:44+00:00,1,1,11
b4ec3b75-f4ee-4ca7-86b6-8b0bcd07093f,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Assignment,77.5,2022-11-11 00:40:22+00:00,1,2,1
b2cfe289-4a44-4a78-ade9-30df43e42346,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,76.0,2022-11-18 02:13:00+00:00,1,2,2
be039936-aa6b-4e3e-8420-25a686f3354d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,77.5,2022-11-24 22:40:33+00:00,1,2,3
85b7fdbc-2e1a-4d34-a2e1-1fdde67ab753,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Assignment,80.5,2022-12-08 23:19:20+00:00,1,2,5
e6c75218-990a-45a5-bc7c-e27b1e223e70,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,81.0,2022-12-15 20:55:06+00:00,1,2,6
e08a4adb-a2b7-4896-85e8-aaa1754805f0,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,74.5,2023-02-02 10:49:34+00:00,1,2,13
17eba7e1-5200-46d7-a5da-df9ab523e52b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,71.0,2023-02-09 09:10:35+00:00,1,2,14
fbcc7497-37e1-4bd7-8c4f-125de48affbc,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Midterm,84.5,2022-11-10 12:42:23+00:00,1,2,1
b58d50cd-6d0c-40f5-95fc-fbccd62346b2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Midterm,80.0,2022-11-17 19:48:44+00:00,1,2,2
178c40bf-4f2d-4d78-8d87-adddf055f967,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Final,75.5,2022-12-22 09:39:59+00:00,1,2,7
c25d084d-121e-44f5-8326-42b46fb1446e,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Quiz,72.5,2023-01-05 22:05:28+00:00,1,2,9
31f0985c-0168-4ad7-b5f0-2bbf26234a6c,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Midterm,69.5,2023-01-19 18:36:58+00:00,1,2,11
db2215dd-027c-484c-b373-1188bca66434,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Final,70.0,2023-01-26 13:03:35+00:00,1,2,12
086fea73-9598-439a-90dc-62a94ee1c213,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Quiz,70.5,2023-02-02 07:56:15+00:00,1,2,13
f27970a9-63fb-41df-9310-6a8dc1263ea7,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Final,72.5,2023-02-16 09:31:46+00:00,1,2,15
b75cfcb0-1c73-45d9-aa88-ee2afadb6f1c,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Final,74.0,2023-02-23 17:55:45+00:00,1,2,16
d50ec977-a55f-42ba-8972-06cea99fa8a2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Final,74.0,2022-11-17 18:12:36+00:00,1,2,2
a95f6e48-e6cb-459a-887f-84a4a3146db6,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Final,81.5,2022-11-24 11:26:50+00:00,1,2,3
98d5603b-ff2d-4636-a7e9-15ddcc1e0e23,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Quiz,72.5,2022-12-22 11:45:38+00:00,1,2,7
9c1ae3f4-a2b5-46c6-8eca-46399b42fe9b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Assignment,71.5,2023-01-06 02:01:42+00:00,1,2,9
3f856f8b-eac4-43f9-878b-5664cbfe9049,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Midterm,72.0,2023-02-10 02:08:23+00:00,1,2,14
98464ddb-c798-4678-9cf0-f90671663661,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,73.5,2022-12-08 14:23:07+00:00,1,2,5
715f83d0-2c2b-43f3-b5a6-ef15d32d0aff,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,80.0,2022-12-16 01:36:27+00:00,1,2,6
c50ab143-14bb-4b2e-86f3-0f1cb3b4be69,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,80.5,2022-12-22 05:09:17+00:00,1,2,7
b869a70f-fcf6-480e-947f-fcd62b198522,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,78.0,2022-12-30 01:44:28+00:00,1,2,8
b7a77dce-1107-44f4-9db2-6cfbaddfa3b6,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,78.0,2023-01-26 09:29:05+00:00,1,2,12
1a738360-9eec-4707-b3e6-016d49e23259,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,69.5,2023-02-02 05:38:20+00:00,1,2,13
93cf596e-6a51-4c3c-b48d-2e45328eba7d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,76.5,2023-02-16 18:57:25+00:00,1,2,15
0d433696-adc1-4e73-8a96-be0c64ad9aab,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,67.0,2023-02-24 01:00:53+00:00,1,2,16
40a8b9e7-7243-4357-b05f-ff7b666a7c5b,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Final,80.5,2022-11-10 11:06:09+00:00,1,2,1
a83a41fe-40a3-44d1-a2e1-f54eaca10051,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Final,75.0,2022-11-17 05:06:46+00:00,1,2,2
37f840e3-e924-4f2a-83a0-9c70256027e2,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Assignment,77.5,2022-11-24 21:46:46+00:00,1,2,3
738a7a03-a462-4fa9-a6ae-cab842134c6c,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Final,80.0,2022-12-01 10:19:55+00:00,1,2,4
984cabc7-522d-45ec-8423-e62dd87a74fe,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Quiz,72.0,2023-01-12 15:27:10+00:00,1,2,10
8c769d2d-b3ae-416e-86ba-87aa5465496e,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Final,78.5,2023-01-19 17:37:13+00:00,1,2,11
a56cce31-bf8e-4ad1-865b-1f856f338dda,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Assignment,69.0,2023-01-26 09:47:06+00:00,1,2,12
fff1fad6-cf61-40e7-a08b-1e292ad30a5d,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Final,80.5,2022-11-11 02:14:35+00:00,1,2,1
55ab6646-2e7e-4859-8309-9b1a8d8f51ff,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Midterm,83.0,2022-11-17 12:41:07+00:00,1,2,2
30ae2798-294a-4403-87f0-ce4f28afe6e3,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Quiz,80.5,2022-12-08 12:35:39+00:00,1,2,5
5ffad034-3caf-4f45-a412-63cefe88507b,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Final,78.5,2022-12-22 11:48:44+00:00,1,2,7
b389cc41-ed11-4631-a36f-69539c6e958e,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Quiz,71.5,2023-01-06 01:52:01+00:00,1,2,9
f1e46d72-f00d-490b-b9a9-5aec75c69168,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Midterm,74.5,2023-01-20 01:13:24+00:00,1,2,11
94b75a5c-bfdd-4c39-a9e3-5684c257f1a0,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Quiz,75.5,2023-02-16 21:46:45+00:00,1,2,15
ab868b72-5175-448d-ac8f-85b903f334e1,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Assignment,78.0,2022-11-17 19:20:03+00:00,1,2,2
f2a1e068-c510-4637-bfcb-95bf600fbae5,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Quiz,83.5,2022-11-24 08:16:55+00:00,1,2,3
dc5118f7-2d00-49b6-8a8b-f40f6f91ac68,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Final,81.0,2022-12-01 05:01:04+00:00,1,2,4
fc25fb36-97ff-4a45-900a-901fd0e477d6,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Midterm,79.5,2022-12-08 16:46:17+00:00,1,2,5
c9e32623-c11a-492f-bb71-963d71cc45c6,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Assignment,77.0,2022-12-15 19:54:38+00:00,1,2,6
35c34526-67ac-4ba2-a2b0-545cdd8d26a7,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Midterm,73.5,2022-12-22 16:48:03+00:00,1,2,7
68a82302-95cc-4bd7-b12c-f3f253be0f61,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Quiz,76.0,2022-12-29 12:53:39+00:00,1,2,8
662d8eab-595e-4ac0-acfa-782094de1b6b,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Assignment,78.5,2023-01-19 10:22:40+00:00,1,2,11
8cf7b560-aa8c-4ff2-a704-3c1afdff0d79,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Quiz,79.0,2023-01-26 05:14:40+00:00,1,2,12
063c33e6-714f-4ede-a5e0-85f7adfd7893,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Assignment,78.5,2023-02-02 16:28:56+00:00,1,2,13
cd151eb2-e966-410d-aae6-13cd4e863cf6,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Final,70.0,2023-02-09 15:08:52+00:00,1,2,14
dd7d9ff8-07a2-4dd2-a7e8-946bae2bfa78,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Final,77.5,2023-02-16 14:31:57+00:00,1,2,15
f68f7354-0186-4d51-9483-10644045fd92,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Quiz,82.0,2022-11-17 04:34:02+00:00,1,2,2
48a2b38a-ac31-4310-9664-1bf77f24f2e9,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Assignment,75.5,2022-11-24 09:59:30+00:00,1,2,3
35b27119-599b-4c4e-a4ec-f3ba299e4868,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Final,72.5,2023-01-06 02:10:29+00:00,1,2,9
ccdd1454-cb20-4ac4-b092-eb0bda788fa2,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Final,75.0,2023-01-12 11:06:09+00:00,1,2,10
c989444d-fc79-4078-8655-c30f146a969c,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Midterm,72.0,2023-01-26 06:18:00+00:00,1,2,12
8028a213-a7f5-4402-bd11-4c51fdf5ebfc,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Quiz,73.5,2023-02-02 15:08:03+00:00,1,2,13
632497ba-fffe-44b0-b367-a1ca4c9bc266,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Assignment,72.5,2023-02-16 22:47:47+00:00,1,2,15
45acb26e-9a6c-4196-ace5-146b3651640b,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,76.5,2022-11-10 10:19:21+00:00,1,2,1
bc63ed30-e3ed-44b5-9e9e-08160fd8ca83,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,78.0,2022-11-18 00:02:16+00:00,1,2,2
71e24dd0-0e41-463a-909c-c5d5c433586f,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,83.0,2022-12-01 23:38:37+00:00,1,2,4
37826c69-e56a-4bad-aac6-24482c9d6e70,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,75.5,2022-12-08 08:08:38+00:00,1,2,5
cbfbd708-ee10-4d08-9919-2d576fa109f8,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Final,80.5,2022-12-23 01:31:33+00:00,1,2,7
cf6bcd61-7809-422f-a4d9-cb4ef8a5b616,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Quiz,77.0,2022-12-29 08:41:53+00:00,1,2,8
6680f1f9-9a1f-46e4-adaa-976504abc83c,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Quiz,72.0,2023-01-26 17:00:54+00:00,1,2,12
af31caaf-0a3b-4cc0-a61c-0b1c06500cb5,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,69.5,2023-02-16 12:01:38+00:00,1,2,15
274c6a86-34db-4c8f-8e59-4c4b890a1010,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,77.0,2023-02-23 18:34:12+00:00,1,2,16
713d9144-0fb4-4d31-af7c-f2eb0cacf652,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Quiz,80.5,2022-11-10 10:57:43+00:00,1,2,1
27d7081a-4984-4b04-ab21-ea13b16ef787,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Quiz,81.5,2022-12-08 07:07:23+00:00,1,2,5
61017d49-8ece-4be9-9300-bf681e388f72,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Midterm,77.5,2023-01-19 06:30:55+00:00,1,2,11
7e85e3f8-027a-4161-95d8-b6ea55473f70,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Midterm,75.0,2023-01-26 09:31:41+00:00,1,2,12
446adfb2-2ffb-4d61-8cdf-f0ce977a4072,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Final,76.5,2023-02-02 04:56:06+00:00,1,2,13
83d3616a-4cf7-4780-a1fb-2b23eea3c6f2,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Assignment,80.5,2022-11-10 07:37:36+00:00,1,2,1
1b047431-cacf-420c-a2b4-ac2eba8aaae4,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Midterm,78.0,2022-11-17 05:21:36+00:00,1,2,2
3ad1d983-77c5-4bbf-855c-3ecddf1a0d3d,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Final,82.5,2022-11-24 17:07:34+00:00,1,2,3
5e913670-da1b-4db1-b2c0-12e87a4b685c,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Final,77.0,2022-12-02 03:23:43+00:00,1,2,4
5c4e46d5-9d1e-43ce-8fbb-a0d8d872e1fa,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Assignment,80.5,2022-12-08 18:02:00+00:00,1,2,5
250e0c42-fca0-4f31-ada1-09dcea52b445,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Assignment,78.0,2022-12-29 19:08:48+00:00,1,2,8
0ea0a38a-564b-48be-abf3-ac2b79fb17b8,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Midterm,73.5,2023-01-05 17:42:02+00:00,1,2,9
ac726ed5-2643-40e9-9411-b1d5e269bfb7,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Midterm,78.0,2023-01-12 19:20:23+00:00,1,2,10
0fbfe709-d6f9-418a-9765-a15d6bc63922,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Midterm,71.0,2023-01-26 12:34:51+00:00,1,2,12
0060123d-6d15-4cc1-a592-ed7479ec1dd8,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Final,74.0,2022-11-17 19:27:51+00:00,1,2,2
aa5f2fed-cb94-4d7a-8a21-8f40cca556c1,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Quiz,76.5,2022-11-24 06:14:37+00:00,1,2,3
df3390ac-133e-4534-ae3d-0414bde43519,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Assignment,74.0,2022-12-01 16:23:55+00:00,1,2,4
69c8bb8a-06d1-4bd8-8b0d-4b4077f4c86b,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Final,80.5,2022-12-22 22:34:05+00:00,1,2,7
1c403bee-0495-4ccf-b383-126f5541238d,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Midterm,74.5,2023-01-06 01:08:18+00:00,1,2,9
e250931e-55f2-4516-9d2c-f97d7dd75c51,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Assignment,79.0,2023-01-12 08:45:59+00:00,1,2,10
a7031f20-0e37-4d54-af1d-64809a416730,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Assignment,75.5,2023-01-19 12:37:39+00:00,1,2,11
dba5ee60-9d04-400f-bd60-bcbce8f0ae7d,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Assignment,72.0,2023-01-26 06:30:32+00:00,1,2,12
35146066-586a-45ea-a1d5-69458afd0c99,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Assignment,78.5,2023-02-03 00:56:27+00:00,1,2,13
5ba67bb2-b375-43a8-90f0-5775b9ae80b7,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Midterm,68.0,2023-02-09 22:57:44+00:00,1,2,14
6a17257e-13f5-44f4-9206-b2e028f81bdc,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Assignment,72.5,2023-02-17 00:28:51+00:00,1,2,15
e7b375ae-9e1f-4524-a6d1-5d959ea24409,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Assignment,76.0,2023-02-23 05:34:57+00:00,1,2,16
f15026b9-4423-41c4-8e93-257c0e1e06b9,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,81.0,2022-11-17 17:11:10+00:00,1,2,2
255e8f61-793f-4720-85b0-2c72014b8c8d,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Midterm,83.5,2022-11-24 10:10:35+00:00,1,2,3
48327655-ffc8-43d2-9e59-f94bd739f1ec,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Assignment,83.0,2022-12-02 01:59:58+00:00,1,2,4
f25b5fcb-f2ba-4e8b-b9ca-5596a2c0aef2,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Quiz,77.5,2022-12-08 18:31:26+00:00,1,2,5
5b4f36f4-c92c-428a-b042-0e3bb7a547f3,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Quiz,82.0,2022-12-15 13:47:34+00:00,1,2,6
93850dd8-a2a8-4c78-b971-579854bb292a,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Midterm,78.5,2023-01-19 19:09:50+00:00,1,2,11
c2315276-ded3-4446-9422-ff04a6cd42f7,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,72.0,2023-01-27 02:09:58+00:00,1,2,12
5e05c19d-48e0-48b0-9a61-fbeee475a5d5,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Midterm,71.5,2023-02-02 23:01:48+00:00,1,2,13
219738de-a9a6-4545-94f7-ef6b6d8b09fd,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Quiz,74.0,2023-02-09 12:47:40+00:00,1,2,14
309cb4ca-052a-452b-bfbe-e3e943627daa,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,67.0,2023-02-23 12:59:33+00:00,1,2,16
80bbad4c-25c8-404d-b01b-88fee27bdee1,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Midterm,83.0,2022-12-01 13:17:05+00:00,1,2,4
5f1f5b77-0fcc-42d5-9681-3d45b88a4b23,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Midterm,73.5,2022-12-22 05:34:54+00:00,1,2,7
f43d0eb8-8825-435f-9df0-78ee271de808,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,80.0,2022-12-29 04:06:14+00:00,1,2,8
71a6edcf-66e5-4c24-a59f-2680e18adbe0,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,79.5,2023-01-06 00:56:00+00:00,1,2,9
77b53fca-3468-4d39-956d-090f7ce79c8f,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Final,77.0,2023-01-26 17:12:29+00:00,1,2,12
bdb7d34f-0e05-4855-ba73-fe04799cccf3,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Midterm,78.5,2023-02-02 22:01:10+00:00,1,2,13
0c019c1d-9c18-49a5-a068-7d53aeb7e23b,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Midterm,68.0,2023-02-09 14:59:16+00:00,1,2,14
ff29f743-efcb-429f-8a35-6960030ce5cf,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Assignment,73.5,2023-02-16 06:10:31+00:00,1,2,15
170133f8-61cc-4e5f-a376-8e069cc3586d,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Final,74.5,2022-11-10 21:05:58+00:00,1,2,1
0c13025f-4173-47bd-89bb-2ac9adc00d8f,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Quiz,79.0,2022-11-17 11:43:10+00:00,1,2,2
3a60b270-6eed-4532-852b-28239d319369,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Assignment,81.5,2022-11-24 15:58:42+00:00,1,2,3
940f0c99-5d44-42f9-ad95-dcf29aeda6b3,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Quiz,73.0,2022-12-01 21:40:25+00:00,1,2,4
6ab17bbb-52be-4287-b020-1a78344356b8,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Assignment,79.5,2022-12-08 19:32:07+00:00,1,2,5
139f3e8e-560e-4376-bd20-7af565494888,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Quiz,72.0,2022-12-15 17:22:02+00:00,1,2,6
5577625d-abcc-418c-b2a7-15b0efaec571,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Midterm,71.5,2022-12-22 18:21:00+00:00,1,2,7
7955cc1f-a40e-41b9-bdcc-92ed95177ab4,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Assignment,70.5,2023-01-05 04:10:08+00:00,1,2,9
df46548a-eaf3-44de-913c-66ea9219f0eb,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Midterm,76.5,2023-01-20 02:27:01+00:00,1,2,11
7995ceb1-4b8c-47c2-b56d-84e851973c94,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Quiz,73.5,2023-02-03 03:38:18+00:00,1,2,13
40152774-465b-46b4-ba0a-155291a46d9f,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Midterm,71.0,2023-02-09 16:34:03+00:00,1,2,14
02f8c05b-cf57-4c3d-aecf-e1ec0d9ccc0e,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Quiz,74.0,2022-12-02 00:27:53+00:00,1,2,4
9d5fec66-f175-4595-8600-e91c43e62010,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Final,79.5,2022-12-08 06:51:36+00:00,1,2,5
f6b5842d-241a-41dc-9943-952ecaf67535,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Midterm,80.0,2022-12-15 10:32:51+00:00,1,2,6
1d4136b4-440f-4e94-a722-e388db5bcd63,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Midterm,81.0,2022-12-29 10:15:52+00:00,1,2,8
f451f3d3-0816-4b9d-9c07-f2a473a49d3e,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Assignment,76.5,2023-01-05 19:07:22+00:00,1,2,9
a4537aab-d443-4250-a0f4-cd736ce7a1bb,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Quiz,77.0,2023-01-12 22:49:18+00:00,1,2,10
4f546f02-5fa4-450c-8a1b-3da4f0d10adb,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Quiz,79.5,2023-01-19 10:31:17+00:00,1,2,11
18ba4afc-c582-4920-acc5-1510acd054a7,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Assignment,77.5,2023-02-02 04:15:49+00:00,1,2,13
51db4bdb-434a-4166-9b5e-1f23753fa888,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Quiz,74.0,2023-02-09 08:53:24+00:00,1,2,14
4f8e6325-9f0f-483f-ad23-2ab512a70b0d,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Assignment,77.0,2023-02-23 06:07:09+00:00,1,2,16
4044c9e8-3666-435d-ae26-f121fb8f5df1,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,74.5,2022-11-24 18:41:08+00:00,1,2,3
7e7e7b55-aa95-457a-a5f4-164bf35e9c4a,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,78.0,2022-12-01 11:45:37+00:00,1,2,4
482d6b5d-a9ac-494a-93b1-216707b5c391,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,76.5,2022-12-08 15:44:12+00:00,1,2,5
0474a28d-ceb6-44fe-98d3-f5cfadf5c957,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,78.5,2022-12-22 14:36:09+00:00,1,2,7
8c8d2327-1532-4be1-a666-3516ac0176d8,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,71.5,2023-01-05 07:19:22+00:00,1,2,9
adc85dd6-fbe9-453b-86b2-cb3aee38c878,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,70.5,2023-01-19 06:31:08+00:00,1,2,11
ea81a867-de70-42d8-9c74-767cb5d769ba,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,75.5,2023-02-02 09:29:49+00:00,1,2,13
aa3cfef0-2db5-45d0-8ee1-d5a467706298,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,72.0,2023-02-23 19:40:16+00:00,1,2,16
513a6a85-63e1-42be-ba97-5a8f2299d43f,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,83.5,2022-11-10 17:54:31+00:00,1,2,1
f546f1a4-c5b8-4156-a419-4966f8c89867,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,84.0,2022-11-17 13:38:58+00:00,1,2,2
7d2974d4-ba7c-4873-83cb-04bec9bd5033,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,83.5,2022-11-25 00:25:51+00:00,1,2,3
1b2c9f3b-7c0c-4392-8400-6ea12519aa23,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,76.5,2022-12-08 11:04:59+00:00,1,2,5
56103536-712f-4bb8-9908-9c75fedfe82e,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,77.5,2022-12-22 09:56:59+00:00,1,2,7
5b34bc7b-ad1e-4739-ad02-61a8fd7c1a8d,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,76.0,2022-12-29 06:44:08+00:00,1,2,8
ee317b56-2c4c-4e0f-9a49-3dd927e25b8d,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Quiz,73.0,2023-01-12 05:51:20+00:00,1,2,10
d5ed2a69-5e37-48fd-b8a6-d7b7b26843c3,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,70.5,2023-01-19 04:18:39+00:00,1,2,11
af57f6b5-708b-42a8-8dc7-36666474b092,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,74.0,2023-01-26 05:05:40+00:00,1,2,12
acbc0945-ee6b-42c5-a4d2-b90d71d597c6,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,74.5,2023-02-02 05:37:24+00:00,1,2,13
ce7b5e0b-8b4f-4e96-a567-d98968ae540a,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,68.0,2023-02-10 00:58:02+00:00,1,2,14
54cd2b6f-2e30-4ed1-8e27-282b7fd75239,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,69.5,2023-02-17 01:51:33+00:00,1,2,15
eebb8db1-af8a-47e5-aa12-75972513936a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,82.5,2022-11-24 08:07:56+00:00,1,2,3
a355e654-afb1-4b93-a5db-24ae6412c3c6,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,72.5,2022-12-09 02:50:54+00:00,1,2,5
7140a72a-40f8-40df-b830-121c2c61cd8e,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,79.0,2022-12-15 05:28:33+00:00,1,2,6
97e81105-279f-4f5c-98b4-4b30d745ab18,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,78.5,2022-12-22 19:32:45+00:00,1,2,7
393d8416-6437-4ba6-9f15-f613805e022d,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,72.0,2022-12-29 23:42:41+00:00,1,2,8
1f8cdb84-6b9d-4b81-ab80-aaea02242390,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,74.5,2023-01-05 17:18:02+00:00,1,2,9
e9d3479f-4ccd-4db5-87b3-e24d3bc86a16,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,71.0,2023-01-12 10:59:34+00:00,1,2,10
ba89f988-b496-41f5-9c62-c56a5825866b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,78.5,2023-01-19 10:21:12+00:00,1,2,11
210ee95b-5f2b-4aa3-8ab6-eeacc82c9aa2,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,77.0,2023-01-26 08:59:36+00:00,1,2,12
7b9a441a-3c39-450e-a12b-ffd312de0d98,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,71.0,2023-02-09 22:14:06+00:00,1,2,14
01062846-8052-429a-bf19-59e8e709c1a6,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,69.0,2023-02-24 01:17:06+00:00,1,2,16
2853e9bc-8850-48d1-b6c2-ab504f6f94ee,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Quiz,76.5,2022-11-10 19:03:54+00:00,1,2,1
d673101f-9a50-4814-b77b-75f7f31c10a1,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Quiz,76.0,2022-12-01 20:49:34+00:00,1,2,4
e4f86964-53c4-45f7-90d2-940f639557e0,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Final,80.0,2022-12-15 18:30:03+00:00,1,2,6
eea637e0-2c5e-4230-b47d-e4f0d19fbb41,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Assignment,71.0,2022-12-29 12:18:24+00:00,1,2,8
e48a9482-8c26-4e7e-88e0-ec6eee6fc37c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Quiz,72.5,2023-01-19 11:10:20+00:00,1,2,11
7bea5a80-ef93-4a05-a4fa-39561a212e9c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Assignment,74.0,2023-01-26 04:54:58+00:00,1,2,12
102f534e-f93e-47f1-83e4-0abb18a0b22a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Quiz,73.5,2023-02-02 12:32:43+00:00,1,2,13
14a6e4e2-414b-431a-8fa2-b1a59e58aeb1,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,76.5,2022-11-10 16:58:00+00:00,1,2,1
01078bbe-4c5c-4bfc-842a-d49358c82067,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,83.0,2022-12-01 08:40:06+00:00,1,2,4
e182607b-1f39-4cfb-a82c-5c85cf5c38cd,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,80.5,2022-12-22 09:09:00+00:00,1,2,7
d83576ae-841f-41ea-8960-e1eefb484b91,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,74.0,2023-01-26 18:06:11+00:00,1,2,12
775ff017-d441-4917-b571-3e6579caf879,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,76.5,2023-02-02 13:49:59+00:00,1,2,13
0f5c372f-52ed-460d-922f-46ec078f83ac,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,71.0,2023-02-09 21:57:15+00:00,1,2,14
76a53a09-1423-4c3b-8e1a-5a96384ac701,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,76.5,2023-02-16 05:19:11+00:00,1,2,15
d0325a85-9123-417e-bf9f-9ed881064ef0,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Quiz,73.0,2023-02-23 08:34:20+00:00,1,2,16
00d171e2-6e19-4028-ade4-77d82b7c315e,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Assignment,76.5,2022-11-10 14:39:47+00:00,1,2,1
d303f851-f41d-46ce-a056-611e628235dd,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Quiz,75.0,2022-11-17 20:58:12+00:00,1,2,2
92f7a209-ed47-488f-b242-f9a015f809f7,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Quiz,82.5,2022-11-24 11:31:36+00:00,1,2,3
e2dc8702-8191-4816-bf60-c3d7bdd88c21,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Assignment,80.5,2022-12-08 09:11:52+00:00,1,2,5
4b428b23-d2c6-4548-9443-8e29946f92cf,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Quiz,81.0,2022-12-15 10:29:43+00:00,1,2,6
f9993c23-1215-4232-95b3-be2a59dfc6b0,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Assignment,75.5,2022-12-23 00:01:30+00:00,1,2,7
cbe43e65-75c4-47bc-87c7-9bac56de2a4e,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Final,81.0,2022-12-29 23:58:40+00:00,1,2,8
38ecdd59-21fe-4660-b9f9-0e3ca48c7a63,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Final,79.5,2023-01-05 13:58:37+00:00,1,2,9
31c7593c-e2c0-4cfd-9104-a1e5d4fa0a69,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Midterm,74.0,2023-01-13 02:11:18+00:00,1,2,10
e5bf390b-d783-4bb9-a46e-399cde5ec399,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Midterm,75.0,2023-01-26 18:17:46+00:00,1,2,12
45385613-0451-4ecf-9344-626ab19f9382,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Quiz,69.5,2023-02-03 03:09:12+00:00,1,2,13
51f8f573-6a96-4457-acd1-c1bec8909c07,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Midterm,72.0,2023-02-10 02:56:05+00:00,1,2,14
e0c51bb0-5d99-4dac-bb3d-3058fc6f7e67,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Midterm,68.5,2023-02-16 05:05:27+00:00,1,2,15
dd948c78-7367-4068-a062-67f37315ec03,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Quiz,68.0,2023-02-23 14:57:28+00:00,1,2,16
fbe3b936-aeef-41bf-b3e5-022c27674e54,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,76.5,2022-11-10 07:22:35+00:00,1,2,1
1e60bc41-afb7-4b6e-b3f2-74d677764bbb,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,81.0,2022-11-17 04:25:28+00:00,1,2,2
8ad66d87-9a0b-4404-b20c-0900b1bd8bf5,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Assignment,83.0,2022-12-01 14:51:13+00:00,1,2,4
9e80aabf-4858-4392-b4ea-27f39bd1b749,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Final,77.5,2022-12-09 01:18:20+00:00,1,2,5
be5a04cb-6aba-4c0c-a9c7-3ce35ddca4cf,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Quiz,79.0,2022-12-15 20:08:48+00:00,1,2,6
1d4bec03-85e9-4c30-9637-a2238bdb0387,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Quiz,77.5,2022-12-22 06:36:06+00:00,1,2,7
a487d364-6a73-45f5-93e7-ee28295d1fb3,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Final,80.0,2023-01-12 07:38:03+00:00,1,2,10
9db2323a-6a29-4b68-84c9-b5018bae7498,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Quiz,71.0,2023-01-26 19:52:15+00:00,1,2,12
4a05891d-f5ba-4b83-b3da-0b6daf1deb25,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Quiz,75.5,2023-02-02 06:09:42+00:00,1,2,13
f7ad7007-a4b5-449a-a126-9d330b2e7f73,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,72.5,2023-02-16 15:07:30+00:00,1,2,15
327520e6-7316-41d4-9ca3-45b24f9880c8,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,69.0,2023-02-23 07:21:15+00:00,1,2,16
376779a9-f7b6-461d-b9b9-04caf54657d8,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Assignment,73.5,2023-05-09 19:57:45+00:00,2,1,1
b8b2af24-ac24-4711-b331-73792f96ed88,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Final,67.0,2023-05-16 14:47:20+00:00,2,1,2
66127a59-c4df-40b9-b71f-82aa05ca380a,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Quiz,70.0,2023-05-30 19:58:06+00:00,2,1,4
8a43cea9-8f28-422a-9304-2bd5fae9c73a,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Quiz,68.5,2023-06-06 23:24:07+00:00,2,1,5
c15dd0d2-4d1e-4d57-86dc-27c0b456716a,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Midterm,63.0,2023-06-13 16:19:16+00:00,2,1,6
66457ebb-f361-453e-b021-94fc54f28ef1,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Assignment,63.5,2023-06-20 09:29:28+00:00,2,1,7
05515fbe-2b73-43de-b81e-7c112290b2b5,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Final,66.5,2023-07-05 01:01:04+00:00,2,1,9
d2dedb06-5e34-4641-bb78-3f93ce0f8993,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Assignment,63.0,2023-07-11 11:51:57+00:00,2,1,10
1e16cf44-dbcf-4c78-855e-4943962df0d4,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Midterm,66.5,2023-08-15 18:12:03+00:00,2,1,15
5096b404-cb2e-4175-ba22-be11fa16b36c,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Final,57.0,2023-08-22 09:35:09+00:00,2,1,16
c5cc23ec-c746-4b76-8f1d-45a60468012f,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Quiz,64.5,2023-05-09 21:57:15+00:00,2,1,1
556e911a-2983-44f6-8d2e-66054891e1eb,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Quiz,69.0,2023-05-30 05:33:11+00:00,2,1,4
fe9d68b2-95ab-4dde-84dd-911c2d5718c2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Midterm,71.5,2023-06-07 01:08:45+00:00,2,1,5
6ea6c96d-0ddc-4a9d-a843-6655619c9422,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Final,69.0,2023-06-13 19:49:17+00:00,2,1,6
ead337aa-5898-48f2-803d-52907ed64c72,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Final,71.5,2023-06-21 01:24:28+00:00,2,1,7
4a331ae9-70c5-4e08-b071-a224db86a76d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Quiz,59.5,2023-07-18 12:20:14+00:00,2,1,11
8d3c8660-e3e6-44dd-b5f8-40757a514e16,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Final,66.5,2023-08-15 09:31:03+00:00,2,1,15
6c953b03-7d80-4ae6-805c-8b1d27bdf861,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Quiz,72.5,2023-05-09 11:05:21+00:00,2,1,1
265f81c1-f0d0-43c3-b18d-6302eaaf3180,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Assignment,67.0,2023-05-16 14:59:34+00:00,2,1,2
52d93f49-e6f5-4548-9fd9-6382e9fcfec2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Quiz,71.0,2023-06-13 19:00:13+00:00,2,1,6
d4f9d5f2-5e0a-4827-a9b7-cc06ed9aee8d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Midterm,66.5,2023-06-20 17:14:17+00:00,2,1,7
c29be605-bb70-4c7a-9954-80569c931394,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Midterm,67.0,2023-06-27 16:13:30+00:00,2,1,8
6cb15212-0c40-49c3-bb2f-ceaaa12ea16b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Midterm,63.0,2023-07-11 05:16:07+00:00,2,1,10
804ba173-9165-4eda-ac8c-ba70cfb2a3c0,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Quiz,63.5,2023-08-01 20:12:02+00:00,2,1,13
4ddff6c9-f4e3-4bc9-9430-c4186101efc9,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Quiz,58.5,2023-08-15 10:37:05+00:00,2,1,15
45d538b2-e982-499b-b1b5-76fbfbfb8116,2d943e4a-13c9-4324-90fc-4977145bdf1d,C103,Database Systems,Midterm,62.0,2023-08-22 16:34:14+00:00,2,1,16
d49c7a78-bd05-47cb-8687-c0cb80fb7bf4,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,66.0,2023-05-16 11:01:09+00:00,2,1,2
e7f42b82-0a51-422e-ac0e-14bb69c2e300,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,69.5,2023-05-23 20:18:43+00:00,2,1,3
d05e884a-21d2-48b0-bdd7-15888ba8c4ce,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,69.0,2023-05-30 17:48:45+00:00,2,1,4
05f13251-e7ab-4582-9962-f8e3551439ce,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,63.0,2023-06-13 11:07:42+00:00,2,1,6
f0efe457-51d4-4051-9523-cb872012033b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,67.5,2023-07-05 00:36:45+00:00,2,1,9
ce9157c8-4310-4ab1-9ffa-91b32c78d680,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,66.5,2023-07-18 21:07:42+00:00,2,1,11
bd44b66d-bab0-4ef4-9513-653f93177972,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,62.0,2023-07-25 23:39:29+00:00,2,1,12
92c7677e-ff59-4f84-a018-72075bb68add,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,61.0,2023-08-09 01:25:57+00:00,2,1,14
4460fda0-7fd1-45da-8552-79c2c6c4cfb1,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,65.5,2023-08-15 11:48:43+00:00,2,1,15
ead38178-b519-4e84-a026-e01a6011a682,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,60.0,2023-08-22 06:09:56+00:00,2,1,16
29d6951c-266f-419a-8e60-1cd551b700db,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Quiz,71.5,2023-05-09 07:54:50+00:00,2,1,1
816ae350-b1f3-4829-bcc9-f1e3fe78fc7c,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Final,68.0,2023-05-16 10:42:09+00:00,2,1,2
88a02005-e0a6-4138-94c6-86d5c4a0c52e,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Final,65.0,2023-05-31 00:18:52+00:00,2,1,4
d0278904-a0db-4b4a-a63b-022553694cff,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Quiz,72.0,2023-06-14 00:48:35+00:00,2,1,6
313ffaf4-5fae-4fb5-86b6-76c9e24b2a08,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Midterm,63.5,2023-06-20 12:19:10+00:00,2,1,7
c6dd7c08-0ee1-482f-966a-ba9ca5df5041,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Quiz,67.0,2023-06-28 02:31:16+00:00,2,1,8
2abc5320-56df-4594-97cc-029b628fe7cd,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Quiz,65.5,2023-07-05 03:14:08+00:00,2,1,9
e8f73eb7-d594-4b3c-9469-fdc99d5e3865,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Midterm,69.0,2023-07-12 02:37:34+00:00,2,1,10
94636622-5b39-437e-88e4-ce22fbb8b156,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Assignment,61.5,2023-08-01 10:51:11+00:00,2,1,13
acc6f3a4-5a4c-435f-80cb-1f8e030dc165,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Assignment,64.0,2023-08-08 22:28:26+00:00,2,1,14
90352091-54f9-41ef-abc3-b6045ccd2466,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Quiz,61.0,2023-08-22 14:37:42+00:00,2,1,16
0eae823c-59e1-4a56-a2f5-86cd4e223af8,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,74.0,2023-05-16 06:10:40+00:00,2,1,2
779c6e12-dfe8-4276-92a8-60529f934f14,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,68.5,2023-05-23 11:00:24+00:00,2,1,3
4fa6d06b-9e1c-4a11-8917-36dedaaf43d3,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,63.5,2023-06-06 04:19:33+00:00,2,1,5
3bb6a9a3-5b98-4825-80a1-92a18241a941,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Assignment,67.5,2023-06-20 21:22:03+00:00,2,1,7
d2499455-f2f1-4171-8f0c-6bd5c6ca94cb,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,60.5,2023-08-15 06:52:08+00:00,2,1,15
7993fef5-d661-463e-9acd-d44c829092f0,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Midterm,72.5,2023-05-09 08:38:50+00:00,2,1,1
b5d611c7-0c91-4fae-b720-6e99a10c8f51,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Assignment,68.5,2023-05-23 15:24:12+00:00,2,1,3
8904d8a3-d8a9-4ccb-a491-2f1b178f7c8f,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Final,73.0,2023-05-30 07:53:15+00:00,2,1,4
5f5a75d3-c56e-4285-b75d-a11474483a11,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Midterm,72.5,2023-06-07 02:21:12+00:00,2,1,5
708fbff1-d208-44c6-9b44-89c9d995b61e,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Assignment,71.0,2023-06-13 10:55:44+00:00,2,1,6
c2dd1126-fb36-4e78-88f3-e65591376d8f,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Quiz,65.0,2023-06-28 03:24:27+00:00,2,1,8
b5cc3b1e-88ee-4a6f-9f9c-626405debea0,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Assignment,63.5,2023-07-04 22:35:42+00:00,2,1,9
98b6c031-9b3a-4dee-b1a8-8cb2737ad1f3,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Final,70.0,2023-07-11 06:36:02+00:00,2,1,10
8a1fd24f-9aae-4352-acea-c5f960ef6a0b,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Assignment,59.5,2023-07-18 04:31:41+00:00,2,1,11
1ffc9839-166c-4cd3-831f-fae8cb18fbb3,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Midterm,64.0,2023-07-25 04:40:27+00:00,2,1,12
3b40259c-821f-4ca4-90bf-e4cbc9438ce2,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Quiz,58.5,2023-08-01 10:21:03+00:00,2,1,13
85d9b062-a43f-4746-bfc4-1a1ade1f384a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Quiz,62.5,2023-08-15 15:09:50+00:00,2,1,15
2d7a46f8-0da0-4f53-a1d6-d0967f121472,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Assignment,58.0,2023-08-22 05:54:23+00:00,2,1,16
bb218346-38bf-44d9-bf83-2335665003c1,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Assignment,64.5,2023-05-09 17:31:00+00:00,2,1,1
97043a5c-35c5-4a46-b965-ea947a135e2c,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Quiz,68.0,2023-05-30 15:56:15+00:00,2,1,4
5701ff8a-0b3d-4f2f-8f87-455457d0eb34,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Final,72.5,2023-06-06 11:32:05+00:00,2,1,5
eda0ad7d-3882-4f2f-aace-9d22ef305182,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Final,70.5,2023-06-21 00:52:08+00:00,2,1,7
66a92b10-2f8b-4f48-9797-57e61851e909,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Midterm,63.0,2023-07-12 01:10:53+00:00,2,1,10
9356331d-af87-450b-aceb-f14ecd042fb5,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Midterm,62.5,2023-07-18 12:44:17+00:00,2,1,11
d628cf45-e37a-4f29-a9f9-46bd8a4e6817,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Quiz,65.0,2023-07-25 15:18:47+00:00,2,1,12
9dc0ab33-17fa-41cd-ac7a-aa1dd84035a3,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Quiz,61.5,2023-08-01 03:53:44+00:00,2,1,13
eb7a8756-642f-4119-be79-f524908b1fcc,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Quiz,59.0,2023-08-08 13:24:21+00:00,2,1,14
32755eb1-9fe0-4f8c-bc07-7bc49b3dec19,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Final,67.5,2023-08-15 11:14:41+00:00,2,1,15
e6840f8e-d774-4ae7-844c-4d99276889d9,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Assignment,61.0,2023-08-22 23:56:14+00:00,2,1,16
561d2d9d-8fbe-45aa-9c03-c9ae3dbed00c,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Final,70.5,2023-06-07 02:04:09+00:00,2,1,5
99651448-7b7c-4d10-b773-113d08facaa2,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Final,64.0,2023-06-13 23:03:13+00:00,2,1,6
4d35fbe1-fd98-49a0-a2e6-4ea38d5dcee2,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Midterm,70.0,2023-06-27 04:13:10+00:00,2,1,8
3d4c8c7a-2077-47a4-9ba4-70ab3ad83034,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Midterm,62.0,2023-07-11 20:28:46+00:00,2,1,10
37a817ed-347b-483d-ba08-243d53d15387,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Final,65.0,2023-07-25 14:52:48+00:00,2,1,12
8ea272c9-3d10-4fed-a0ce-8598b2ac688f,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Midterm,63.5,2023-08-01 23:30:46+00:00,2,1,13
45bc45eb-0be4-4963-af12-f6652a1e8ff0,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Final,63.0,2023-08-08 05:08:28+00:00,2,1,14
4623b189-1aa8-483e-884d-cf6079b754ca,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Final,74.0,2023-05-16 18:26:26+00:00,2,1,2
c60f66bb-ec30-40ec-aa36-33ba5a394fe9,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,69.0,2023-05-31 02:48:36+00:00,2,1,4
09ddf66a-2ef1-4136-b42d-ab09662b610a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,66.0,2023-06-27 13:30:10+00:00,2,1,8
0d602ab6-924f-4286-8922-4c03d92ff7b0,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Assignment,70.0,2023-07-11 16:51:27+00:00,2,1,10
5b3f5953-f0cd-433b-93a7-83bb62bbcb1b,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Final,65.5,2023-07-18 20:31:34+00:00,2,1,11
474d4170-84ab-4f2e-a0cc-1a7792db8fd3,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,66.0,2023-07-25 03:57:03+00:00,2,1,12
c7896ebe-0880-48d1-b1d7-ee524e068d8e,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,67.0,2023-08-08 20:09:12+00:00,2,1,14
bd03fe1a-86cc-49e1-af3d-9c7c9ade524f,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,64.0,2023-08-22 22:32:31+00:00,2,1,16
d8ffd19b-1993-44c7-b4c8-a4bedc5bb2f7,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Final,70.5,2023-05-09 03:58:04+00:00,2,1,1
3f7b34e9-be7d-4aaf-9939-369bfe59d6e1,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Midterm,72.0,2023-05-30 20:13:05+00:00,2,1,4
4fd06c72-0e4f-45dc-8972-8024bc58a316,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Final,65.0,2023-06-13 05:36:56+00:00,2,1,6
d51ac2eb-ea96-4454-bcb0-d27e044c52f5,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Midterm,70.5,2023-06-21 02:21:31+00:00,2,1,7
a0924291-66f6-4287-ab1c-a2cf66dc521f,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Assignment,64.0,2023-06-27 13:52:18+00:00,2,1,8
d7958136-fbce-4e60-9cdd-1628d2eb3182,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Midterm,61.0,2023-07-11 18:31:48+00:00,2,1,10
2ad1f77a-a896-4b8c-8fb5-a42def8e50e7,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Quiz,59.5,2023-08-15 09:01:00+00:00,2,1,15
bb930e64-a217-4589-86b2-c0b8fd418c1f,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Quiz,66.0,2023-08-22 12:43:52+00:00,2,1,16
f6220b56-be32-4cc9-b50e-f183ca9e37e7,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,73.5,2023-05-23 14:02:20+00:00,2,1,3
f9b7f88d-2270-4d59-9380-0b1dd0a157a5,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Quiz,67.0,2023-05-30 21:56:31+00:00,2,1,4
2be19886-b9a5-4200-8b1f-8890003f7315,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Quiz,65.5,2023-06-06 18:15:20+00:00,2,1,5
34b75cd3-cbe4-4f0d-8607-4bc119f49034,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Midterm,67.0,2023-06-13 21:35:27+00:00,2,1,6
cc578f7e-c180-41a6-aa1b-49e7ca8a1225,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Midterm,63.5,2023-06-20 15:29:36+00:00,2,1,7
d35f2ca4-d7f7-471e-8efa-62994acd9217,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Assignment,67.5,2023-07-04 05:45:50+00:00,2,1,9
9164c388-20ee-45fd-a006-20d8fbc7efc3,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,62.0,2023-07-11 09:50:51+00:00,2,1,10
1acec5a6-393d-495d-93bd-dd8d163f0a77,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Assignment,66.5,2023-07-18 10:47:14+00:00,2,1,11
da5cd1c0-6fbb-4252-b7e7-db828de224b1,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,67.0,2023-07-25 15:36:44+00:00,2,1,12
da3311d7-40da-4800-a91a-ee5ef5b8803b,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Quiz,67.5,2023-08-16 02:47:48+00:00,2,1,15
cabc3268-6534-4812-9902-6118741c3879,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Quiz,66.0,2023-05-16 18:11:15+00:00,2,1,2
2847ebcd-de76-4b33-9001-69bbe270a293,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Assignment,63.5,2023-05-23 09:18:16+00:00,2,1,3
547e3233-2175-412d-b19b-d6a0cb907862,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Final,67.0,2023-05-30 17:44:10+00:00,2,1,4
52755ceb-0a58-4cdb-9b56-5c3938a1dca7,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Final,62.5,2023-06-06 18:38:45+00:00,2,1,5
d09c6da7-70e5-4c1a-bed3-82c24df9635d,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Midterm,63.0,2023-06-14 02:32:31+00:00,2,1,6
c15e6847-dfa3-46f3-938c-f3e692ac8dd9,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Assignment,65.0,2023-06-27 08:34:45+00:00,2,1,8
0a6197b9-0683-4bac-b0dc-b92c2868efeb,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Quiz,65.5,2023-07-05 01:03:07+00:00,2,1,9
8751d12c-46fc-47f8-9749-0508d9c865d3,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Quiz,65.0,2023-07-12 03:30:02+00:00,2,1,10
435ff86b-48bd-42fd-9c62-b11b3900e6e7,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Assignment,63.5,2023-07-18 14:10:53+00:00,2,1,11
ed2f19c9-8782-40eb-8d78-f25a9a2239c9,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Quiz,63.0,2023-07-25 19:27:02+00:00,2,1,12
6135441b-9a78-4ee6-943f-cac194b826b1,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Final,67.5,2023-08-01 10:47:12+00:00,2,1,13
d21f8177-89aa-4492-ac52-e658da880509,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Quiz,65.0,2023-08-08 13:30:45+00:00,2,1,14
88ef0e83-7867-46ca-a200-787df7b8416e,d4341dc6-04e1-498c-8d4b-abb221969162,C108,Artificial Intelligence,Midterm,57.5,2023-08-15 08:19:57+00:00,2,1,15
de70a6ec-df7f-4008-9a04-eafa4772f4d7,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,74.5,2023-05-09 22:01:39+00:00,2,1,1
60c0c74d-c9fb-4124-9cc4-9f770273551f,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,71.0,2023-05-17 02:00:28+00:00,2,1,2
35d57e55-18c5-4cfc-87f1-f86cc2214876,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,68.5,2023-05-23 16:05:14+00:00,2,1,3
b8eb56e3-f637-4562-9d6d-2e2625095eab,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,72.0,2023-05-30 16:44:00+00:00,2,1,4
1e5f2c71-1519-48dc-8ad6-ff4b11be7377,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,68.5,2023-06-06 16:22:30+00:00,2,1,5
a907ba7c-5e8c-4ff4-a158-e28ee24f2661,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Midterm,70.0,2023-06-14 02:40:01+00:00,2,1,6
da0a6307-63f7-40ec-be1c-350edf2b19b3,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,62.5,2023-06-20 11:54:38+00:00,2,1,7
3dee79e1-7c84-412f-8ad1-7b06e4a8b3db,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Midterm,70.0,2023-06-27 16:30:21+00:00,2,1,8
3eb5347d-11d9-4ec5-b910-af2496899c13,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Midterm,70.5,2023-07-04 10:32:17+00:00,2,1,9
e3e5fa4c-7879-448d-8b15-9151491f1de0,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,69.0,2023-07-11 07:03:16+00:00,2,1,10
7bb8fb4d-c6a8-46c0-9c39-097b7eb3c8aa,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,69.5,2023-07-18 20:58:15+00:00,2,1,11
10f6dd0d-9985-4d8e-bfd2-abca54e0cdb2,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Quiz,64.0,2023-07-25 21:34:04+00:00,2,1,12
880618b1-48e9-4cff-8510-123d457853c0,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,65.5,2023-08-02 00:37:57+00:00,2,1,13
2df2994b-ad3c-4956-941b-f3f14735e930,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,62.0,2023-08-08 15:07:34+00:00,2,1,14
bac3028b-9f15-4053-a98e-1fbef601a3a3,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Final,69.0,2023-05-16 09:39:44+00:00,2,1,2
3dc63704-ef67-4de4-afd9-4a3230cefb64,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Quiz,69.5,2023-05-23 04:58:26+00:00,2,1,3
edace156-124a-474b-bb00-987c236ca7c6,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Midterm,67.0,2023-05-30 20:27:23+00:00,2,1,4
6ee0a108-9c82-4cb2-aaf9-e9f05c189b25,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Midterm,62.5,2023-06-06 18:42:06+00:00,2,1,5
c30897eb-96f4-4983-ab1b-19c3adb7adee,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Assignment,71.0,2023-06-13 13:25:52+00:00,2,1,6
d85d0bdb-10e8-4501-b5f9-8d6af4b823bf,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Quiz,63.5,2023-06-20 19:59:02+00:00,2,1,7
1ae45953-0cc5-44c7-aa00-f14895c5bf2b,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Quiz,67.0,2023-06-27 07:44:50+00:00,2,1,8
743f25b8-7bb4-4bd0-9c68-38e408be5d13,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Assignment,63.5,2023-07-04 20:35:53+00:00,2,1,9
8213573e-546e-4c3b-a084-a835549231ff,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Final,68.5,2023-07-18 14:44:40+00:00,2,1,11
52c4a64a-ca63-4d91-915f-496c61debfc0,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Midterm,64.0,2023-07-26 00:14:03+00:00,2,1,12
bc619ff8-96bd-4ece-8989-2fd4039801d0,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Assignment,62.5,2023-08-01 18:46:18+00:00,2,1,13
4b745164-401f-4e97-9b2b-be24e584f36e,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Midterm,64.5,2023-08-15 15:53:16+00:00,2,1,15
e596a1c9-7417-4de4-a6df-c589ab046ee3,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Final,67.0,2023-08-22 23:20:16+00:00,2,1,16
f8d4a8a1-30df-48a2-a3e2-fb5be7f33721,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,64.5,2023-05-09 08:53:39+00:00,2,1,1
84980274-8d64-4b60-a02a-3321021146f9,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,66.0,2023-05-16 10:29:21+00:00,2,1,2
a3c2bc0f-1caa-46a7-8e5e-97952a4f42f4,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,72.0,2023-06-13 08:42:48+00:00,2,1,6
16448031-83a9-4dde-af97-73e1d22fb241,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,65.0,2023-06-27 05:00:21+00:00,2,1,8
889c365d-ea2f-469c-baaf-090f3cfe7172,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,63.5,2023-07-04 06:44:20+00:00,2,1,9
a4e8f31c-a352-43be-b69b-4ef1fbbb2a8b,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,64.0,2023-07-11 19:04:13+00:00,2,1,10
3bc76609-469b-490c-aff3-26923d44fe8a,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,66.5,2023-07-18 12:42:15+00:00,2,1,11
1a25d5e6-320b-4b8d-bfaa-708c76975d75,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,65.0,2023-07-25 10:28:44+00:00,2,1,12
2b2d4733-70d4-477c-8ac9-a6f8cc869645,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,63.5,2023-08-02 02:26:59+00:00,2,1,13
da3cc2c2-5799-4371-b71a-edf568513aea,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,65.0,2023-08-08 10:49:53+00:00,2,1,14
bffd57a8-4826-4dbd-9a7f-810aabeb7c6f,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Assignment,69.5,2023-05-09 21:14:19+00:00,2,1,1
31b330c8-b8b4-4602-8263-49844cae33b5,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Final,62.0,2023-06-13 14:49:22+00:00,2,1,6
adde7d6f-3736-4090-9e71-e918b80387a7,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Final,71.5,2023-06-20 23:35:31+00:00,2,1,7
74339f07-af48-44eb-9e12-d31999a75d18,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,67.0,2023-06-27 12:17:38+00:00,2,1,8
00767904-73c0-42e4-ae97-1aa78f2cc01d,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Final,69.5,2023-07-05 02:25:08+00:00,2,1,9
e47ebbcf-b7e6-449c-88a5-3b82b3b230d1,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,66.0,2023-07-11 22:41:06+00:00,2,1,10
a0f44458-9104-4434-b53d-2939cfb1087c,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,65.5,2023-08-01 10:36:45+00:00,2,1,13
6807367c-30f2-4c01-83b1-d21415aee0fb,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Midterm,60.0,2023-08-22 06:19:48+00:00,2,1,16
149a3c96-5f01-4e5e-8eca-7a9931a2b3ef,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,73.0,2023-05-16 12:05:36+00:00,2,1,2
24283dd3-ab04-4ff1-b8a3-f3f6824b93e2,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,73.5,2023-05-23 16:08:21+00:00,2,1,3
a66d8d6d-4f01-40be-acaa-042eec4e8ae9,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,71.0,2023-05-30 15:25:07+00:00,2,1,4
567ca9fd-454a-4c5f-9134-af93ca2b0c2f,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Quiz,65.5,2023-06-06 05:22:06+00:00,2,1,5
fbebf2b5-0e39-4f8c-981e-b4d6b65bd975,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Quiz,70.0,2023-06-13 19:39:22+00:00,2,1,6
a17a50f8-a541-4cc2-a08a-65c0ec2bd99c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,66.0,2023-06-27 22:29:31+00:00,2,1,8
408be972-a127-4b83-a002-6d83bb642fab,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Quiz,60.5,2023-07-04 08:40:15+00:00,2,1,9
f87f617c-e504-47d4-858c-3b737e95bb22,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,67.0,2023-07-11 17:35:39+00:00,2,1,10
5826f8dc-99a7-43bf-96ca-86147ac716cd,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,63.5,2023-07-18 17:12:50+00:00,2,1,11
f79b0a3c-4d36-4d9c-921b-a90537e02763,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,61.0,2023-07-25 11:24:20+00:00,2,1,12
f06a0997-1e67-4ca9-8284-cd1b76513b93,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,60.5,2023-08-01 08:38:17+00:00,2,1,13
56eb7038-78fa-4c26-98f2-7846533208b3,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,62.5,2023-08-15 03:58:25+00:00,2,1,15
90349cc2-47de-424b-b4eb-a8bad760878d,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Quiz,65.0,2023-05-30 09:56:32+00:00,2,1,4
7b0c7cac-1fd8-4226-8278-2ca45b1b0371,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,69.5,2023-06-06 03:55:22+00:00,2,1,5
c04620e0-c340-4013-b0b4-1d73495f0c2a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Assignment,62.5,2023-06-20 22:53:55+00:00,2,1,7
3fc7b895-7b88-4a00-af00-c2df1ac2f730,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Assignment,62.0,2023-06-28 02:17:00+00:00,2,1,8
17961f05-6edd-406f-acb2-75d5f352ff67,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Quiz,59.0,2023-08-22 18:49:35+00:00,2,1,16
cf79fdf8-5226-4e1a-9742-b11751621bda,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Quiz,74.5,2023-05-09 04:30:26+00:00,2,1,1
994aee5d-ef42-4711-90df-35359b5f76c6,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Final,64.5,2023-06-06 22:22:36+00:00,2,1,5
22041e50-778e-459d-8c62-5fc4a216dd52,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Assignment,70.5,2023-06-20 05:09:22+00:00,2,1,7
dcb01921-8369-4971-85e2-46eef61a5621,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Assignment,71.0,2023-06-27 10:06:32+00:00,2,1,8
72577411-bf60-4a5e-a9de-4a04b8a14e62,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Midterm,67.5,2023-07-04 23:07:01+00:00,2,1,9
7e00af94-b9d1-424b-b501-cd5c91dc13a2,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Midterm,63.0,2023-07-25 11:38:53+00:00,2,1,12
6e1f94f6-0ea6-4584-8890-be2514d6157c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Final,66.5,2023-08-01 09:25:33+00:00,2,1,13
862d2810-c24f-4c58-bb3f-958ab68fb934,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Quiz,65.5,2023-08-15 06:44:26+00:00,2,1,15
6dd50159-2e4d-468e-b934-6acee4cc4750,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Midterm,66.0,2023-08-22 14:14:56+00:00,2,1,16
c76d6f5a-fe5e-4add-aee1-52c64712c1c9,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,65.5,2023-05-09 21:12:16+00:00,2,1,1
4408cbcc-b6e5-4d5b-ace4-3a4be0f0c04f,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,66.5,2023-05-23 15:55:38+00:00,2,1,3
59a1c2aa-e854-4431-8561-22173aaab1ab,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,63.0,2023-05-30 21:56:24+00:00,2,1,4
4f0921b1-bb34-4d15-95ab-50e63aa355a7,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,69.5,2023-06-06 08:33:17+00:00,2,1,5
2e80d850-b8aa-48a6-9f38-eaf9bd2e52ea,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,70.0,2023-06-13 05:30:20+00:00,2,1,6
341e83b5-4ef9-48a2-8d25-84279134b78a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,67.5,2023-06-20 10:56:57+00:00,2,1,7
6c10d835-d422-494c-93b1-cc83a2fae7f9,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,66.0,2023-06-27 13:36:56+00:00,2,1,8
60224a81-d851-4d00-930b-3ea16d877cd9,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,65.0,2023-07-11 14:34:17+00:00,2,1,10
55fd6bb9-d89b-4c9b-b400-545607c2c101,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,63.5,2023-07-18 05:41:17+00:00,2,1,11
cdd19a82-780d-4c74-a733-50c7c0e852dc,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,67.0,2023-07-25 21:01:37+00:00,2,1,12
9c1283ea-0fb2-40eb-9288-a4c9a84657f7,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,63.5,2023-08-01 21:05:13+00:00,2,1,13
c40aa85f-60b5-4d09-97b9-0d2c5d696b73,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,65.5,2023-08-15 15:23:55+00:00,2,1,15
e7e96be2-1857-4799-beba-30da894ec148,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,59.0,2023-08-22 14:32:06+00:00,2,1,16
9c49352e-818f-45dc-a6ce-631bcef2f3b2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Midterm,69.5,2023-11-05 22:07:17+00:00,2,2,1
25fe659b-a8e9-4514-823f-3c56dde2c2a4,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Quiz,65.0,2023-11-12 07:36:19+00:00,2,2,2
7cfad80e-54f9-4d4d-be57-8803e9232eb8,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Assignment,64.5,2023-11-19 10:47:50+00:00,2,2,3
50a1ab2d-e1d1-4ee6-a630-dde46715df41,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Assignment,66.0,2023-11-26 16:34:51+00:00,2,2,4
0c913137-5ae1-49df-b51d-e6fb3d090219,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Assignment,67.5,2023-12-03 15:47:37+00:00,2,2,5
5aa2357b-db37-4fc4-bf2a-7130fcebc929,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Midterm,70.0,2023-12-25 00:15:40+00:00,2,2,8
5522fee8-7e37-469a-8549-8468bccd4651,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Final,62.0,2024-01-07 17:32:37+00:00,2,2,10
fdf3f8e3-b96f-4529-b90f-8f993e04ead2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Assignment,65.5,2024-02-11 22:58:07+00:00,2,2,15
3185f15d-a979-458a-80c4-1cefe6aa293b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Quiz,60.0,2024-02-18 05:50:21+00:00,2,2,16
98cad3ff-c0fa-4322-8ef5-eab4243f02dd,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,71.0,2023-11-12 20:07:41+00:00,2,2,2
40007642-e146-4f37-a591-6b5469e134fb,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,63.5,2023-11-19 13:49:59+00:00,2,2,3
0338b5b3-2ac9-4b70-8b0f-127ccd8e8346,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,67.0,2023-11-26 09:17:07+00:00,2,2,4
91e9728b-fba0-4e7a-b70e-4aa028d3734b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,62.5,2023-12-04 03:33:25+00:00,2,2,5
a6cee54f-43ff-4f97-8f29-e798d524108e,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Assignment,70.0,2023-12-10 15:58:02+00:00,2,2,6
19376571-e728-437f-82a6-6450d5dda2a5,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Assignment,70.5,2023-12-17 06:18:07+00:00,2,2,7
a9636f32-5eb2-4836-b93c-0a6025e4f997,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,62.0,2023-12-24 12:40:06+00:00,2,2,8
7adf83e7-72c1-4d78-b4e8-f8eec95567ad,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,63.5,2023-12-31 16:41:52+00:00,2,2,9
957975df-cd11-4a2f-a743-1fdec5a326df,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,67.5,2024-01-15 01:16:40+00:00,2,2,11
bd53b147-4354-4162-8b6b-c5bc4f6d429d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,68.5,2024-01-29 01:49:31+00:00,2,2,13
b0e5f1ed-a594-49ae-86f0-5aafbf780fd0,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,63.0,2024-02-04 08:59:47+00:00,2,2,14
cf3e6d5e-9513-413d-96ad-34412ba29fd1,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,63.0,2024-02-19 02:10:45+00:00,2,2,16
6026f26b-af32-4b69-9d26-5065261e840a,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,66.5,2023-11-05 23:40:55+00:00,2,2,1
5daa2d72-0975-4c1d-896c-6c0ddf273296,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,65.0,2023-11-12 16:23:22+00:00,2,2,2
5806c2e2-3805-4d09-af8f-e6a83b2630e0,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,66.0,2023-11-26 14:07:15+00:00,2,2,4
5144bbdb-fc36-4d87-beeb-78c3200e347c,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,62.5,2023-12-04 01:17:21+00:00,2,2,5
f6a1d672-99c0-419f-b628-aaa684e8845d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,62.0,2023-12-10 14:50:56+00:00,2,2,6
3cb9e95a-b853-4036-bacd-661518a57369,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,61.5,2023-12-17 15:17:52+00:00,2,2,7
8d2c549d-a05c-4e99-b1bc-1ec2a1bc62a6,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,62.0,2023-12-24 11:32:26+00:00,2,2,8
268e3462-84a0-4c57-8760-8b9a2e2f8105,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,70.0,2024-01-08 02:34:13+00:00,2,2,10
93ff7e54-778d-4e35-a76e-0497785b8562,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,67.5,2024-01-14 23:08:14+00:00,2,2,11
f15f22f3-45f6-4fbc-bc5b-e8efa2ddaabe,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,59.5,2024-01-28 15:47:56+00:00,2,2,13
ffbcd478-925a-44f9-88cf-540015745ec0,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,60.5,2024-02-11 13:17:41+00:00,2,2,15
64d31562-1551-4eaf-8866-d18fb5ddbc14,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,58.0,2024-02-18 12:57:28+00:00,2,2,16
0f2b86d7-117f-4dfe-9d77-fa8e01177842,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Assignment,71.5,2023-11-05 22:23:18+00:00,2,2,1
69fadf40-bf3a-48c7-9029-86879538019f,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Final,64.0,2023-11-12 04:37:08+00:00,2,2,2
caacde44-34ea-4bf9-8e21-e2b575fc0664,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Assignment,71.5,2023-11-19 05:53:22+00:00,2,2,3
f878b10a-16eb-45e7-b076-0287a0f46287,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Assignment,69.5,2023-12-03 14:07:27+00:00,2,2,5
2fc85540-3b5d-47b4-ba50-e168455ed8fe,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,69.0,2023-12-10 11:20:52+00:00,2,2,6
871a721a-2d87-42d8-abd8-af564a7dcfa0,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,65.5,2023-12-17 12:03:39+00:00,2,2,7
480d5e43-437f-45e4-a090-6cecb8401233,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,65.5,2024-01-01 03:21:10+00:00,2,2,9
acedbb9b-b18a-478e-8f11-ead16eeaa1f0,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Assignment,62.0,2024-01-07 12:23:45+00:00,2,2,10
a6c6cecf-316c-4ff1-8871-356ee1ef1b63,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,68.5,2024-01-14 09:48:23+00:00,2,2,11
39363fb6-5ba9-4c3b-a3bb-1236e624db1d,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,68.5,2024-01-28 17:04:05+00:00,2,2,13
f1e64c7c-f8a0-44b3-9731-6a8fef52e15e,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,58.0,2024-02-04 12:08:45+00:00,2,2,14
82c5a93d-27b3-44d6-9c2b-e8e4cc58ce9c,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Final,72.5,2023-11-05 10:13:09+00:00,2,2,1
53661dbd-9b8c-485f-b3d4-eee85ec0763c,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Midterm,71.0,2023-11-12 20:10:51+00:00,2,2,2
5740fc7b-f3e5-4853-a014-746d5ffe642e,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Quiz,72.5,2023-11-19 15:55:46+00:00,2,2,3
3c2601e2-5992-4414-a9e8-7c90accccb66,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Assignment,64.0,2023-11-26 21:37:11+00:00,2,2,4
70eb16f8-0c48-4977-9c41-8e831dad7a82,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Final,63.0,2023-12-10 05:41:56+00:00,2,2,6
a6d48fae-a259-4394-a32e-d8ebecd00bb4,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Assignment,65.5,2023-12-17 04:04:03+00:00,2,2,7
f576257f-e763-4600-a9b5-108c9c9ba541,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Quiz,64.0,2024-01-07 23:58:19+00:00,2,2,10
c85bcf49-066c-4c5c-8f94-f65d3674c534,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Assignment,61.5,2024-01-15 00:54:00+00:00,2,2,11
aee69e5e-7826-4730-91b4-4789f8a278f0,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Midterm,65.0,2024-01-21 16:32:25+00:00,2,2,12
5e5abd27-d610-46b9-958d-082ab3e04ee2,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Quiz,63.5,2024-01-28 21:10:17+00:00,2,2,13
d50afa32-dab8-43c6-9c66-676b82e6da5c,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Midterm,66.0,2024-02-04 20:46:51+00:00,2,2,14
d3dda108-b958-4ca4-bb41-1ed4e665dd98,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Midterm,65.5,2024-02-11 10:06:06+00:00,2,2,15
de6d5655-c989-4199-b627-0cd940fecf40,52dbd570-530a-45e1-a2ee-6ce2520216e2,C104,Operating Systems,Midterm,58.0,2024-02-18 04:16:55+00:00,2,2,16
554a10f5-f303-4e3d-8518-e19460a8aa1a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,68.5,2023-11-05 12:33:19+00:00,2,2,1
dd9f27f3-ae1e-4627-8a13-40d377adb322,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Final,63.5,2023-11-19 12:27:53+00:00,2,2,3
d5254f04-211d-48e2-8a2d-6480ce61ad59,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Assignment,64.0,2023-11-26 04:11:38+00:00,2,2,4
202de531-8580-479f-b48d-84037b9d9650,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Midterm,70.0,2023-12-25 03:48:07+00:00,2,2,8
9b26b831-dd3c-4236-b252-ab289b1ecc88,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Midterm,61.5,2023-12-31 21:51:32+00:00,2,2,9
cd7d5907-69e2-4643-84ba-d47d617a4960,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Assignment,67.0,2024-01-08 01:42:50+00:00,2,2,10
cb03658a-8397-4db9-9b46-e1ef552fe5d8,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Final,61.5,2024-02-11 23:35:15+00:00,2,2,15
a8ec1fa4-6d1c-472f-9ec9-843a4158c8a6,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Midterm,57.0,2024-02-18 22:28:59+00:00,2,2,16
a4aab7c1-09d7-4ebb-9a66-5922984979e0,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Quiz,65.5,2023-11-05 13:38:58+00:00,2,2,1
aeea1767-e9a5-4e0f-a438-912c8941e1f0,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Final,64.0,2023-11-12 05:59:12+00:00,2,2,2
79b6082e-d3e5-4720-9186-23b0d8ee2bd8,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Midterm,73.5,2023-11-20 01:03:19+00:00,2,2,3
0f7f63a0-64da-4719-993a-ed4a01fb180c,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Final,68.0,2024-01-07 11:51:11+00:00,2,2,10
9b75b689-c153-4592-99dc-08309c07c993,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Final,68.0,2024-01-21 13:32:01+00:00,2,2,12
af423acc-7011-4a70-9bd8-9d32b576f5f9,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Assignment,62.5,2024-01-28 16:22:25+00:00,2,2,13
27d96428-62eb-413d-b56c-42e422c7eeaa,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Assignment,59.0,2024-02-05 01:29:22+00:00,2,2,14
127cd4ee-6913-4d98-85be-a3b3e81e6cf6,d4341dc6-04e1-498c-8d4b-abb221969162,C101,Data Structures,Midterm,65.5,2024-02-11 10:45:14+00:00,2,2,15
7cbe5473-75b1-401b-a513-1dae0f5e9aff,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Quiz,65.5,2023-11-05 07:09:08+00:00,2,2,1
9b5b9e45-640b-4de0-938a-a9a433b59438,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Midterm,70.0,2023-11-12 17:40:30+00:00,2,2,2
8fbc6fb4-7371-4585-b5ac-c1c7fe00317f,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Quiz,64.0,2023-11-26 20:13:57+00:00,2,2,4
4ab0c390-3937-41e3-93e9-70deadc725ff,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,62.5,2023-12-03 22:44:07+00:00,2,2,5
9743ff08-ffb8-41f5-925f-b918e6c4ef25,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,64.0,2023-12-10 19:24:41+00:00,2,2,6
c7a8fdca-0cbe-4722-9b3f-979017bb6710,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Final,68.5,2023-12-17 09:38:41+00:00,2,2,7
89dbdd77-1763-4636-815d-2cd742011f2f,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,65.5,2024-01-14 15:28:15+00:00,2,2,11
e8a1aacf-e7be-4e75-bffa-c1d2b2697e00,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,65.0,2024-01-21 09:23:26+00:00,2,2,12
6ed1edb7-8116-45b8-b02c-bd3f3c9747be,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Midterm,61.5,2024-01-28 19:19:32+00:00,2,2,13
e2b7b72d-2bf5-43ad-b138-46c41d2bd505,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Midterm,59.0,2024-02-04 06:43:56+00:00,2,2,14
097233e9-9bb5-4d6c-88a0-a8564d162d1c,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Final,67.5,2024-02-11 16:27:40+00:00,2,2,15
3ad507b3-24b7-491a-abf5-988fc2bdee9f,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,66.0,2024-02-18 15:20:26+00:00,2,2,16
a5bf7e5c-933e-4d36-873f-55f25ec8e561,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Assignment,66.0,2023-11-12 22:28:14+00:00,2,2,2
24bc21f8-4507-4466-9d2e-b7376a63d2ea,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,64.5,2023-11-19 08:42:35+00:00,2,2,3
ede3032f-080b-41cd-899f-c6565d43bbb5,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Assignment,73.0,2023-11-26 06:05:35+00:00,2,2,4
005339db-ac73-4fc7-b2b3-2cf135cfe132,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Assignment,72.5,2023-12-03 05:47:35+00:00,2,2,5
04a9812a-251b-4ea1-be95-fefd7477760c,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,65.0,2023-12-10 07:56:45+00:00,2,2,6
9ee54eee-eeae-4617-a8cb-8835f5a57ac9,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,61.5,2023-12-17 16:35:59+00:00,2,2,7
4daac51a-91f7-4a57-9a02-9247ef78fb8b,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,61.0,2023-12-24 17:09:37+00:00,2,2,8
2a12706d-40f9-48e3-a576-bd51a9e580e9,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Midterm,63.0,2024-01-07 23:24:58+00:00,2,2,10
49ef5870-7bd0-45fd-972f-ab68e4fdab48,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,60.5,2024-01-14 19:41:36+00:00,2,2,11
e232a8c8-d8a8-4d76-b880-9f4a8172c9d1,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Assignment,65.0,2024-01-21 22:22:32+00:00,2,2,12
38390591-a07a-4e41-9ea2-0182ccbad17c,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Quiz,58.5,2024-01-28 21:34:06+00:00,2,2,13
724e8183-3557-43e5-830c-f12d61f73e29,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Midterm,67.0,2024-02-04 07:44:00+00:00,2,2,14
03d3087c-7b06-4813-a27d-16290b89221c,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Quiz,57.5,2024-02-11 11:16:34+00:00,2,2,15
00cff865-2216-47ac-95c2-dacbb0ee5a25,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,67.0,2024-02-18 19:14:54+00:00,2,2,16
b40f50f2-debb-47ea-9544-f38cd76364f6,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Quiz,73.5,2023-11-05 08:26:37+00:00,2,2,1
15d4c718-9175-4276-b86f-056c0f99e8d8,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,73.0,2023-11-12 08:27:55+00:00,2,2,2
96d81315-1ec8-4c5c-9df6-2d5cb5225ff0,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,65.5,2023-11-19 12:27:09+00:00,2,2,3
437d8907-7b83-4c35-a77c-ce4ad64a6ba0,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Quiz,69.0,2023-11-26 12:28:42+00:00,2,2,4
aa9c9252-2a9c-4b21-bf5d-e28cbcd148ba,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,69.5,2023-12-03 07:32:44+00:00,2,2,5
f03b62db-4012-4e82-8248-dd375b41c927,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Final,70.0,2023-12-11 00:03:46+00:00,2,2,6
0e4d1d81-585d-43ca-af99-9ab79a3017db,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,65.5,2023-12-17 07:49:26+00:00,2,2,7
e97d1643-0fcf-40f3-aacf-bb8bebe93871,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Final,63.0,2024-01-07 23:20:26+00:00,2,2,10
d69579ba-457d-47fc-ad2c-9bcd538b65ba,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,67.5,2024-01-15 03:44:22+00:00,2,2,11
a5844678-f940-4ba6-900c-73a4503e9db9,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,64.0,2024-02-04 05:43:48+00:00,2,2,14
c23ac24a-e425-4f8d-a4f1-006a0e2e3a6c,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,65.5,2024-02-11 04:02:54+00:00,2,2,15
0d94f7d5-89d7-4312-ab02-61b75ec272b3,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,65.0,2024-02-18 08:59:58+00:00,2,2,16
561cee2c-a365-4949-b85f-4cfc425c3dcc,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,70.5,2023-11-05 22:31:41+00:00,2,2,1
e0b0e103-78fa-4993-8bca-5f9ce3a038ce,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,72.0,2023-11-12 19:10:20+00:00,2,2,2
d782dbc8-62bf-4f49-b9e2-fdfd65ef8f1f,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,66.5,2023-11-19 10:11:29+00:00,2,2,3
04b978d4-bb9e-4f32-a3b8-258816c05def,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,72.5,2023-12-03 11:49:20+00:00,2,2,5
4cbad062-b132-4f01-94f5-e93bcd6bd8cc,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,64.0,2023-12-10 10:30:22+00:00,2,2,6
0b680156-9013-48f1-a04e-240493b8c901,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,69.0,2023-12-24 18:44:39+00:00,2,2,8
9e5ea092-457b-485b-b2b0-b36d9a266586,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,67.5,2024-02-11 04:48:54+00:00,2,2,15
79b2f85b-16df-46c7-884d-535652815b3f,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,61.0,2024-02-18 13:23:03+00:00,2,2,16
5283b4bb-4bf1-4631-8320-744a7ff671e9,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,68.0,2023-11-12 06:30:18+00:00,2,2,2
fd26b9cd-cca9-4fb5-9c67-728e26404bae,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,66.5,2023-11-19 19:14:04+00:00,2,2,3
3c9b8e0b-3aad-4b08-a844-4d817a0b81e6,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,66.0,2023-11-27 01:00:00+00:00,2,2,4
225acc42-22ff-4f6a-bc16-adf91c47ae87,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Quiz,66.0,2023-12-10 21:00:15+00:00,2,2,6
7c0c4b1e-a724-41e6-a182-b7b3b22ffa8e,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Midterm,65.5,2023-12-17 22:27:45+00:00,2,2,7
8daac2a0-3e8a-49b4-85e8-600dcc4c6bee,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Quiz,67.5,2023-12-31 06:48:23+00:00,2,2,9
13795214-672d-4045-8d8a-6de0d58f9d52,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,69.5,2024-01-14 06:05:54+00:00,2,2,11
371f3db4-2d2c-4324-ba1f-3d6e7130cb92,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,67.0,2024-01-21 21:01:04+00:00,2,2,12
a44eaa5b-a90d-412d-aac8-e7c4f723f7e5,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,60.5,2024-01-28 19:09:12+00:00,2,2,13
23ccbe25-44ed-416c-b2e7-929a11f2a23d,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Midterm,63.0,2024-02-05 01:11:40+00:00,2,2,14
f320434d-a0dd-4c13-9200-5bf1d7901f30,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,65.5,2023-11-06 01:31:38+00:00,2,2,1
0fa4cc52-9fce-4375-976b-a852ca5c9f94,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,66.0,2023-11-12 16:07:33+00:00,2,2,2
39fdb0e4-3f0b-4efc-ba7d-c6bfd32f8e39,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,69.5,2024-01-01 00:58:49+00:00,2,2,9
0cb8b333-e8c5-4168-8120-e3226dbe171d,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Midterm,66.0,2024-01-07 09:20:07+00:00,2,2,10
7c153de3-235a-4711-9f10-0d1a7f84df9a,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Midterm,59.5,2024-01-14 14:59:50+00:00,2,2,11
8e91fac8-15b7-4e4d-9455-ea396505f5f2,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Final,68.5,2024-01-28 07:20:06+00:00,2,2,13
fc6c20a4-3a10-4594-85a8-18ef93f49ce5,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Midterm,62.0,2024-02-04 23:16:38+00:00,2,2,14
fb3f999e-bbe2-4b93-82c3-be5a906cc320,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Assignment,60.5,2024-02-11 19:01:34+00:00,2,2,15
24f1b0ce-fe2f-4b87-a03f-5ea23ac7e335,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Quiz,66.0,2023-11-12 06:15:57+00:00,2,2,2
8f52ad67-ec3e-458b-a525-1f89acc58794,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Assignment,69.5,2023-11-19 03:55:13+00:00,2,2,3
66c54fe5-c9dc-428a-9363-376fbb17023b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Final,73.0,2023-11-26 19:22:33+00:00,2,2,4
f6ef7e75-b463-4c34-9678-a503e1c752bf,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Quiz,69.0,2023-12-10 06:02:06+00:00,2,2,6
9fdb1bb1-31c9-46a0-a4d0-1ea0467d2f2c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Assignment,64.0,2023-12-24 13:59:14+00:00,2,2,8
63b162e2-2d13-401c-929a-81998df238eb,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Assignment,60.5,2023-12-31 05:11:47+00:00,2,2,9
32d70260-2abb-4462-9be3-00e5033c326b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Midterm,69.5,2024-01-14 23:29:10+00:00,2,2,11
74812c97-9d0a-4414-a622-1a391f76c6f9,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Assignment,61.0,2024-02-04 05:31:13+00:00,2,2,14
0e170c62-641b-4304-99d9-09267760e274,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Midterm,64.0,2024-02-18 15:21:18+00:00,2,2,16
53cd75d3-9e52-434b-bdeb-17d42ff9b2dd,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Midterm,73.5,2023-11-05 13:20:22+00:00,2,2,1
19e9e9f3-f87b-42ee-b834-17a2ec7d2450,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Final,71.0,2023-11-12 09:48:06+00:00,2,2,2
98aa0d2e-276a-41d1-ac2f-fdb499a01768,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Assignment,67.5,2023-11-19 18:07:33+00:00,2,2,3
6af61ab7-c88a-4016-95cd-7b3bcd1741c5,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Quiz,71.0,2023-11-26 11:05:46+00:00,2,2,4
1ad9b486-cd0f-44d8-8fca-e8553e205759,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Assignment,66.0,2023-12-10 13:06:48+00:00,2,2,6
95d62536-1a34-4de6-b344-dda08c1ed9ce,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Quiz,68.5,2023-12-18 01:14:30+00:00,2,2,7
f6684aa7-9700-4783-9e43-fa2614679086,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Quiz,64.5,2023-12-31 17:10:31+00:00,2,2,9
1fee393a-03e5-45bc-aaf6-3052f9221a2c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Quiz,62.0,2024-01-07 23:49:21+00:00,2,2,10
1f5d8f6c-0d60-42ab-a306-7065d3e42586,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Final,60.5,2024-01-15 02:37:39+00:00,2,2,11
b6992495-8684-4a8b-8fd7-8da2302c5162,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Assignment,63.0,2024-01-21 15:33:32+00:00,2,2,12
0fa67729-15b8-4c92-90dc-11ca55d79c2a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Midterm,64.5,2024-01-29 02:08:58+00:00,2,2,13
0e7bcf8b-64e8-4df6-b090-727c527e8c88,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Quiz,59.0,2024-02-04 14:11:05+00:00,2,2,14
6ab3b523-2e97-4134-8006-736dda160c22,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Midterm,63.0,2024-02-18 14:56:37+00:00,2,2,16
c9ffbb5e-10db-400e-8112-f0dc8cd5898b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Midterm,64.0,2023-11-12 15:50:33+00:00,2,2,2
a79c06b6-ffe0-4836-8be0-1d35e48991ac,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Midterm,65.0,2023-11-26 23:53:30+00:00,2,2,4
21e60a68-dd3d-486b-a0ea-af7eaed3574c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Midterm,68.0,2023-12-10 16:07:35+00:00,2,2,6
cf91893f-9444-4671-9426-8f9da486fa81,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Midterm,61.0,2023-12-24 20:00:11+00:00,2,2,8
8f0495fd-4877-406a-a431-4d05fb9cc40f,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Midterm,63.5,2023-12-31 12:26:44+00:00,2,2,9
efaf1342-3ccb-42f0-9f21-2bab42714b3c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Midterm,61.5,2024-01-15 03:38:39+00:00,2,2,11
aeba61c4-452d-4b0d-b93f-ff4ca410e4ad,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Final,62.5,2024-01-28 08:03:01+00:00,2,2,13
6974208c-6b5f-4bab-9900-8203988b5393,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Final,63.0,2024-02-05 00:12:29+00:00,2,2,14
45500bb8-bf47-4a66-b297-59b62c2de1de,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Quiz,63.5,2024-02-11 21:35:46+00:00,2,2,15
6506503c-131b-472e-9dd5-67fbcf737396,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,55.0,2024-05-24 09:29:55+00:00,3,1,4
93cde62d-ab67-4fa8-bf7a-caa030883766,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,56.5,2024-05-31 19:41:15+00:00,3,1,5
de42a2c8-1d85-42dc-8c5c-3d9ed8ef8f14,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,54.0,2024-06-07 21:38:19+00:00,3,1,6
4c0db10f-6529-41c7-be5f-f70f4024dfc1,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,58.5,2024-06-14 12:27:50+00:00,3,1,7
1c9a118e-cd45-4ec0-8eca-7061db774196,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,52.0,2024-07-05 20:51:48+00:00,3,1,10
c6267e29-209d-4417-a149-688382a17afe,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,56.0,2024-07-19 19:17:33+00:00,3,1,12
fdd5c0f2-de06-4f1c-b293-27303366b450,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,51.0,2024-08-16 19:27:12+00:00,3,1,16
250b2cd0-6dbb-408b-8a0a-cd31603bd339,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Assignment,58.5,2024-05-17 08:48:34+00:00,3,1,3
bb683a2a-860a-42f2-8337-b9f4b2a05fa5,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Midterm,61.0,2024-06-07 17:37:04+00:00,3,1,6
41d32675-c9a0-422f-904a-019f10e1bbd4,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Midterm,53.5,2024-06-14 08:32:46+00:00,3,1,7
e8d105ab-db1d-4a9c-a048-130b2cec81d2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Final,55.5,2024-06-28 15:32:51+00:00,3,1,9
721be65e-e4e8-44ee-832b-7ee682c93e38,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Final,55.0,2024-07-05 06:27:17+00:00,3,1,10
92140381-7737-41a4-8ba3-83900fadbb76,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Quiz,50.5,2024-07-12 08:30:31+00:00,3,1,11
abe33b14-6002-4813-9d33-7fbceb894cc9,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Final,51.0,2024-07-20 03:32:45+00:00,3,1,12
968c6eb9-9574-4fe4-ba19-58936fe2d597,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Quiz,49.5,2024-07-26 08:28:42+00:00,3,1,13
1caae997-fcea-4159-8e39-9827363c0879,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Quiz,51.0,2024-08-17 01:08:40+00:00,3,1,16
a680754c-f129-4764-a5b4-c4c3dea351cf,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Midterm,56.0,2024-05-10 23:34:04+00:00,3,1,2
37227b8c-4b3d-45ef-956b-627dd4b88d2c,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Final,57.5,2024-05-17 04:10:53+00:00,3,1,3
8fdb32d7-c9dd-4e90-9bd3-acd94c9b2161,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Quiz,55.5,2024-05-31 22:11:03+00:00,3,1,5
c0ca3e34-98a1-4a41-8b8e-810f58ddc59d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Quiz,54.0,2024-06-07 09:06:47+00:00,3,1,6
e7975438-26f1-4e77-a595-02d54639453f,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Assignment,59.5,2024-06-14 05:51:39+00:00,3,1,7
c86b597d-31c5-4b5f-8585-718c027170a1,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Midterm,55.5,2024-07-26 17:40:01+00:00,3,1,13
0e3fa85a-18e5-44c6-8dde-0febdd77f1b2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Midterm,52.0,2024-08-02 16:25:03+00:00,3,1,14
c866e88e-3b11-4c25-ab77-f5932363a3ab,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,63.5,2024-05-03 13:29:07+00:00,3,1,1
ac1b521a-acdc-493a-a912-9f4470f0365d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Assignment,53.5,2024-05-17 12:20:20+00:00,3,1,3
304b7ae3-b9c5-473b-b051-b45005cb945b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Assignment,63.0,2024-05-24 08:38:27+00:00,3,1,4
238e4149-b371-4950-a8ef-968818b4a358,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,58.5,2024-05-31 16:50:38+00:00,3,1,5
e91cb2af-bde4-40f3-a869-724b38ad17d1,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,61.5,2024-06-14 12:40:49+00:00,3,1,7
85a716d3-2c73-4ba8-aac8-61472942c8ac,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Assignment,60.0,2024-06-22 03:26:07+00:00,3,1,8
8bf2d07d-d655-4113-af72-1ed26fa27812,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,58.5,2024-06-28 15:44:27+00:00,3,1,9
3651eefc-7df8-43a8-aa0d-9573d2e3c02a,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,57.5,2024-07-12 07:10:14+00:00,3,1,11
bbde504f-9342-4a26-a908-95cff2db4ae1,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Assignment,50.0,2024-07-19 13:33:22+00:00,3,1,12
accc287d-b119-49dc-8fb5-47e028e85469,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,49.0,2024-08-02 13:33:21+00:00,3,1,14
480c0ea1-6cde-44e7-82b7-2263e7abccb2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,57.5,2024-08-09 08:32:19+00:00,3,1,15
64075622-65eb-4038-b6ec-58076b442fee,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,56.0,2024-08-16 11:07:10+00:00,3,1,16
2e644905-266b-4e7a-9d8c-306e0fa79f36,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Assignment,58.5,2024-05-03 11:17:57+00:00,3,1,1
44226023-5bd8-46fd-8285-592062f4d3c1,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Final,58.5,2024-05-17 14:21:47+00:00,3,1,3
c7d35809-8535-4c5e-9552-0b7007c25724,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,57.0,2024-05-24 23:39:49+00:00,3,1,4
1ac52cad-960b-4497-8e9c-209faa4c918f,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Assignment,59.5,2024-05-31 14:51:37+00:00,3,1,5
204a99c6-ab09-41d0-bc3d-695199d9a9bb,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,51.5,2024-06-14 23:49:01+00:00,3,1,7
1c00e2fe-2c97-4ef3-ad05-1ccaee593828,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,53.0,2024-06-21 07:12:41+00:00,3,1,8
e6a224d9-5305-4bc7-bf05-174195ae024a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,60.0,2024-07-05 11:16:17+00:00,3,1,10
ec25d2d4-5b4d-4670-9859-14f3769a1c7e,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Assignment,53.5,2024-07-12 15:49:18+00:00,3,1,11
d1fb20de-81cb-46e4-9ac8-3bb0331ff8ee,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Assignment,53.0,2024-07-19 13:05:06+00:00,3,1,12
a977cdf2-f45b-4383-ba74-9171bdf393c7,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,48.5,2024-07-26 04:45:49+00:00,3,1,13
78687f7d-4cd4-4b24-9a6e-7a3d8c8a980f,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,55.0,2024-08-02 04:31:04+00:00,3,1,14
e81f3376-ec53-4791-8578-8d03bc494eef,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Final,48.5,2024-08-10 02:58:59+00:00,3,1,15
48c0ef17-46a8-4acc-a9d3-b47527ae09b3,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Final,49.0,2024-08-16 22:46:12+00:00,3,1,16
3d3a7ad9-fa66-4734-b9c8-991ea8816764,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Quiz,58.5,2024-05-03 10:17:19+00:00,3,1,1
ed45cea1-216e-4f95-96b8-eb17415b00a6,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Midterm,62.0,2024-05-10 09:43:20+00:00,3,1,2
815d4a55-a417-4396-8196-a48927d7d3c9,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Midterm,62.0,2024-05-24 05:30:14+00:00,3,1,4
f1e8653e-57c8-4788-8302-ff241434dd6f,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Final,59.0,2024-06-08 02:11:14+00:00,3,1,6
01d67c1e-96b8-4c9a-be32-88dc39dd74b5,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Final,59.5,2024-06-14 09:11:25+00:00,3,1,7
458b5a07-dadc-47bc-86f4-040dde5b32a1,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Final,54.0,2024-06-21 20:18:02+00:00,3,1,8
ab2305a9-5029-44a7-888b-1f362bec6f5d,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Final,59.0,2024-07-05 16:30:04+00:00,3,1,10
5a325ce6-ed1b-4661-aef5-6d2d62525296,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Quiz,51.5,2024-07-26 08:32:16+00:00,3,1,13
052b4b62-aaa4-4969-b455-c2f69804586b,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Final,52.0,2024-08-02 09:05:23+00:00,3,1,14
acff13b6-0595-47d3-9282-c8a327a67051,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Midterm,52.5,2024-08-09 17:59:40+00:00,3,1,15
a8263aa9-d7f5-4d14-ae27-a19cc1734860,52dbd570-530a-45e1-a2ee-6ce2520216e2,C106,Software Engineering,Quiz,57.0,2024-08-16 12:10:58+00:00,3,1,16
64a3f150-c5ce-4902-bce3-3ded6114de4c,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Quiz,58.5,2024-05-03 22:39:24+00:00,3,1,1
cca6fcd3-c41a-4342-b2af-ed879cacbf55,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Final,64.0,2024-05-11 01:10:25+00:00,3,1,2
b6937d20-e4fd-444f-bdd4-2fa025e46c3c,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Final,59.5,2024-05-31 09:16:25+00:00,3,1,5
acc53403-8999-4ddc-adfe-5ec30f9e2508,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Midterm,53.0,2024-06-07 18:37:34+00:00,3,1,6
a37ab879-a342-4f58-b1b1-3f5dc8be3ac0,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Midterm,55.5,2024-06-15 02:28:25+00:00,3,1,7
95e3c731-98fb-4f9d-bdf2-0ae4dbe0b8e0,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Quiz,51.0,2024-06-21 20:05:56+00:00,3,1,8
9b916126-48be-44df-bf88-9a7ea2935a3d,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Quiz,52.0,2024-07-06 03:07:43+00:00,3,1,10
5455017e-ce9c-43e7-9a03-dbc03b316f3a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Assignment,59.0,2024-07-19 09:29:05+00:00,3,1,12
9dc7817c-d0a8-4a1e-885a-db974a04fefb,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Midterm,56.0,2024-08-02 05:34:30+00:00,3,1,14
0c78303c-7aca-4da7-bf2c-65c78e9b1ae2,52dbd570-530a-45e1-a2ee-6ce2520216e2,C109,Cybersecurity,Final,55.5,2024-08-09 22:38:25+00:00,3,1,15
60448e52-f7e3-4e99-b658-651713b206d8,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,64.5,2024-05-04 02:46:59+00:00,3,1,1
4ed49a59-8ad5-428a-8218-52bb9fd502d6,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,63.5,2024-05-17 23:24:49+00:00,3,1,3
3cf283e2-06ce-499d-97d8-d44e3b2683ee,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,57.0,2024-05-24 05:30:49+00:00,3,1,4
4d8bacc2-90c5-487f-9f7c-b65a280225d1,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,57.5,2024-05-31 16:02:25+00:00,3,1,5
b0d1f9fc-7ec0-441f-a81e-21985a701d97,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Assignment,58.0,2024-06-08 03:05:30+00:00,3,1,6
b44bd1ac-fdfe-4506-bb16-7302e53084e1,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,51.5,2024-06-28 20:27:41+00:00,3,1,9
b139877d-c1c1-46b9-a4e0-3000503d434b,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,53.0,2024-07-05 17:52:44+00:00,3,1,10
5607740b-3ca5-4d27-b06b-467358f0789a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Final,54.5,2024-07-12 08:48:28+00:00,3,1,11
9ed6abec-a83f-430b-be1a-f25ca5576910,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,57.5,2024-07-27 02:45:16+00:00,3,1,13
8e672a51-5493-44be-a91a-41687396d6b4,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Assignment,51.5,2024-08-09 05:43:42+00:00,3,1,15
e947d524-c9f9-4913-bbe4-640f8c217bbf,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,52.0,2024-08-16 21:50:07+00:00,3,1,16
5a30e524-54e4-4a04-83ef-00d27ae748e3,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Midterm,62.5,2024-05-04 03:50:27+00:00,3,1,1
d805e61c-44be-4649-8fd5-f840cdc6f546,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Assignment,58.0,2024-05-10 23:40:44+00:00,3,1,2
71523666-6772-4a05-af64-09339e8ad24a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Assignment,63.5,2024-05-17 05:34:24+00:00,3,1,3
8796b9ba-414e-4939-ac28-429e21e6101e,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Quiz,57.0,2024-05-24 13:13:43+00:00,3,1,4
ec90e7ad-43a5-4214-8cd3-f87cd9354022,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Quiz,51.5,2024-06-14 16:41:08+00:00,3,1,7
516aad10-9535-43ec-be59-1b48af4a047a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Assignment,53.0,2024-06-22 00:56:01+00:00,3,1,8
24727e3d-e296-4be6-8c16-bf8d2e0bae16,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Quiz,54.5,2024-06-28 16:47:49+00:00,3,1,9
9394fde2-2356-4a4f-91dc-4efe7647d3ba,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Final,55.0,2024-07-05 10:41:04+00:00,3,1,10
fe92b456-e6be-4ae9-bcd1-b34df0c7b01c,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Quiz,58.0,2024-07-19 22:49:55+00:00,3,1,12
7ae68f51-dcac-4f24-809d-4a9ca7e87f75,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Assignment,58.5,2024-07-27 03:02:07+00:00,3,1,13
f5665714-cea9-4e96-be37-1afd0b12de0e,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Quiz,51.0,2024-08-02 07:41:49+00:00,3,1,14
3ed4f1cd-6b3a-4bd6-8992-03673373c208,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Quiz,57.5,2024-05-04 01:27:35+00:00,3,1,1
ccefb431-6b22-4910-b4f5-270e95eb6493,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Final,57.0,2024-05-10 16:03:46+00:00,3,1,2
40a8dbcd-0d8e-46aa-b7db-35fc087ebe80,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Quiz,61.0,2024-05-24 15:13:24+00:00,3,1,4
e31c190d-a1e8-4347-8587-1dede3a4960a,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Final,53.5,2024-05-31 06:42:53+00:00,3,1,5
51fa0ec8-5858-4607-bd6d-c162f987faaa,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Final,56.0,2024-06-07 04:13:19+00:00,3,1,6
be88b35d-fcee-4e04-8a40-c762d1416680,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,51.5,2024-06-14 16:12:55+00:00,3,1,7
b8fea18f-848f-4bd0-a9de-6cedf236cc9b,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,50.5,2024-06-28 04:06:06+00:00,3,1,9
780161da-4e9f-4019-aef3-595a7a513466,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,51.5,2024-07-12 12:43:57+00:00,3,1,11
45b768e2-662f-48d4-8117-3c5361da52cd,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,57.0,2024-07-19 14:35:44+00:00,3,1,12
f6766961-6de4-41e9-8f07-7ec1f1bab2aa,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,55.5,2024-08-09 05:30:48+00:00,3,1,15
35f21b2d-8500-418b-b768-54c0b30dd293,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Final,52.0,2024-08-16 14:39:27+00:00,3,1,16
996016ca-b38e-428b-bbe9-07f048a78cfb,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Quiz,61.5,2024-05-03 22:52:40+00:00,3,1,1
6c59ac85-6540-4fac-8559-1d7c7b6c1d5f,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Midterm,58.5,2024-05-17 10:42:34+00:00,3,1,3
db862eea-13af-4b5c-a234-13fbbc17c359,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,59.0,2024-05-24 11:46:36+00:00,3,1,4
b394b140-d0db-4943-887a-0bca0ed3d3df,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Midterm,62.5,2024-05-31 13:59:22+00:00,3,1,5
25cae07c-1ce3-4381-bf41-6ae195dddeb7,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Midterm,56.0,2024-06-07 09:41:15+00:00,3,1,6
8d081fdd-ee0d-4013-b1d8-12f2464af968,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,60.5,2024-06-14 08:14:01+00:00,3,1,7
82c3cbd5-f0d7-46e2-824b-0bd716f3965c,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Final,58.5,2024-07-12 04:16:20+00:00,3,1,11
6b7830b1-0420-4fbe-9c0f-748417999ae4,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,57.5,2024-07-26 09:16:23+00:00,3,1,13
8133b581-ee78-4780-b6bb-09fbdbe4cce6,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Quiz,58.0,2024-08-02 22:31:06+00:00,3,1,14
cde1dc68-c1f2-4ced-8a00-785eb9caa80d,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Midterm,53.5,2024-05-17 04:07:59+00:00,3,1,3
66177e93-ed21-46a2-b570-2481bb44fadd,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Assignment,59.0,2024-05-25 02:07:21+00:00,3,1,4
30f00d59-0c8d-43c6-a6c7-c5d73016aff0,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Midterm,58.5,2024-05-31 10:46:50+00:00,3,1,5
76fe1df7-a542-4675-87e8-103d97792170,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Quiz,57.0,2024-06-07 19:09:28+00:00,3,1,6
da84e5d0-4da6-483e-8dcb-0bf207dd1953,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Midterm,61.5,2024-06-14 10:16:11+00:00,3,1,7
26be6d6a-040f-4a78-825c-e79b9b90f093,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Quiz,51.5,2024-07-26 10:16:13+00:00,3,1,13
93bb40c4-9378-49a4-9165-85d0b07a8f96,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,58.0,2024-08-02 22:42:25+00:00,3,1,14
14c6210d-9d31-4695-a3c6-c3c2354bbaa7,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,48.5,2024-08-10 01:22:09+00:00,3,1,15
951f27b2-21a6-4406-b98d-bb6ef170d8ec,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Midterm,47.0,2024-08-17 00:46:44+00:00,3,1,16
ad90a0a1-76d4-4b2c-92b6-39ec45e999f3,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,58.5,2024-05-03 18:46:41+00:00,3,1,1
48412c5c-9fc0-40c0-a1d8-82f5f9218576,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,56.0,2024-05-10 10:28:38+00:00,3,1,2
cca191d1-1a6b-45b8-a0e9-db0738dbea6c,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,63.5,2024-05-18 00:07:00+00:00,3,1,3
718d725f-6028-461f-9e58-d3ddd3873365,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,54.0,2024-05-24 08:43:19+00:00,3,1,4
5f43ff99-b0b6-43d3-9222-87f00d93f5c9,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,54.0,2024-06-21 19:29:25+00:00,3,1,8
91c08a59-dfcc-4dad-a2a8-f7d66169f848,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,50.0,2024-07-05 08:00:41+00:00,3,1,10
6fe8f57d-ce14-4a79-9468-af01cc18e6ef,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Quiz,52.5,2024-08-09 18:44:47+00:00,3,1,15
4a79b919-1d99-469b-924d-19fae37906c0,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,49.0,2024-08-16 12:06:57+00:00,3,1,16
3fe4fd7c-1156-4dc1-817f-f54eaa842720,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Assignment,62.0,2024-05-10 18:28:14+00:00,3,1,2
26d0b0fe-20a6-482c-a710-0f0bf1385e31,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Assignment,63.0,2024-05-24 07:52:09+00:00,3,1,4
c09f5eb1-8741-4b7a-b45c-590cb1abc33f,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Final,60.5,2024-05-31 23:33:12+00:00,3,1,5
c59dd15c-bf8e-4baf-8561-2490e6b28e6b,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,62.0,2024-06-07 18:16:18+00:00,3,1,6
6c8841b5-ed29-4f24-970b-6dcdc515d73a,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Midterm,61.5,2024-06-14 22:27:12+00:00,3,1,7
864a01cd-1481-4c5a-a190-dfc7149b49ac,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,60.0,2024-06-21 06:16:45+00:00,3,1,8
6b8caf59-2a6d-4a72-a5a0-51dd302d6540,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,56.5,2024-06-28 05:08:30+00:00,3,1,9
690cfd4f-df3d-42a1-9ba7-b83b29b6d34d,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Midterm,52.0,2024-07-05 04:04:28+00:00,3,1,10
f629382c-3112-4cd2-8b46-70772335d622,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Assignment,56.5,2024-07-12 21:49:38+00:00,3,1,11
340a4f0b-e06f-4bf1-91bf-9678e53b6293,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,54.0,2024-07-19 11:44:51+00:00,3,1,12
5affcfd3-38d4-4ce1-aa9a-fe2d45983295,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Final,48.5,2024-07-26 13:27:22+00:00,3,1,13
f0b9ed80-591b-4f41-937e-e78339352322,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Quiz,57.0,2024-08-02 21:01:41+00:00,3,1,14
c5d25979-679c-43e8-a067-9e7ca0c3a7fa,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Final,47.5,2024-08-09 15:23:27+00:00,3,1,15
8bb6939e-6b77-4174-8938-2fbd10f6de3c,f37e112a-f649-4321-a042-ae5dff11d297,C105,Machine Learning,Assignment,49.0,2024-08-16 11:10:51+00:00,3,1,16
3aab3378-9a17-4bd9-868b-f6d1ae0e4f7c,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Quiz,58.5,2024-05-03 12:45:29+00:00,3,1,1
3854715f-ad0c-4052-94cc-1885943c6d4a,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Assignment,64.0,2024-05-10 14:30:23+00:00,3,1,2
e244fbe6-52a9-43e8-9cb3-70fe8f738d90,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Quiz,53.0,2024-05-24 20:33:06+00:00,3,1,4
3caa8cec-0387-4b73-b8fa-8ea9a6a357c0,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Assignment,62.0,2024-06-07 10:49:54+00:00,3,1,6
4e049e14-ca32-4767-b203-2a7e8a412baa,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Quiz,60.0,2024-06-21 09:27:38+00:00,3,1,8
e17a3a8b-7bf7-40d4-80be-978a8862fb8b,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Final,58.5,2024-06-28 20:19:55+00:00,3,1,9
fd1fe4a6-0db7-4178-9f1a-2a4722a45ec0,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Final,53.0,2024-07-05 08:48:34+00:00,3,1,10
d573f0b5-86ee-4cec-ac60-b7203df2aaa3,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Quiz,51.5,2024-07-12 22:17:06+00:00,3,1,11
6145adb2-e0ba-498b-ac13-17a29ecae6a9,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Assignment,52.5,2024-07-26 08:40:52+00:00,3,1,13
441814e2-54b2-4528-9004-024bc4a5bdda,f37e112a-f649-4321-a042-ae5dff11d297,C109,Cybersecurity,Final,48.0,2024-08-02 04:38:15+00:00,3,1,14
f78ffda2-8b78-49be-934e-8e28f4a0035d,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Quiz,58.5,2024-05-03 07:01:51+00:00,3,1,1
f4aa0d84-7ecd-4812-9540-52cbde68f1e4,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Assignment,59.5,2024-05-17 14:48:54+00:00,3,1,3
ab5a4d24-3e75-49d0-8038-840c82666bc5,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Quiz,58.0,2024-05-24 05:45:57+00:00,3,1,4
87c464b8-14e5-41a6-85d1-77a2ff8f0b66,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Quiz,62.5,2024-05-31 19:16:27+00:00,3,1,5
d7635a89-4927-4674-81d6-7c6ff71ccc3d,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Midterm,61.5,2024-06-14 03:56:12+00:00,3,1,7
45dd7566-d784-4652-8836-fdaff23de2c9,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Final,56.0,2024-06-21 17:12:07+00:00,3,1,8
1b3c87bb-688f-4ebf-9887-ca764d2add0f,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Assignment,55.5,2024-06-29 01:15:01+00:00,3,1,9
0409f61b-c174-46b1-879d-b6180ffd4613,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Midterm,59.0,2024-07-06 01:53:18+00:00,3,1,10
98e3d9fe-646a-4fb5-b10e-b2dd1d11c4ef,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Assignment,57.5,2024-07-12 10:16:54+00:00,3,1,11
ebe5f964-c928-4a3a-aa27-e751ec123e2a,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Quiz,50.0,2024-08-02 22:07:04+00:00,3,1,14
35f1da6a-8106-4e10-a3ab-98a4855560b7,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Final,56.0,2024-08-17 03:13:34+00:00,3,1,16
21355c51-9156-4fd2-a7a0-7a94dd066edf,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,59.5,2024-05-03 21:51:14+00:00,3,1,1
e23f251c-3dac-4780-bb20-a97e1804752f,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Midterm,55.0,2024-05-11 00:06:15+00:00,3,1,2
bc672236-0f02-48f8-b7b2-da35667a67bb,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,56.5,2024-05-17 20:01:04+00:00,3,1,3
4c9155dd-b784-4d48-b5da-85613958e6e3,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Midterm,56.0,2024-05-24 19:27:36+00:00,3,1,4
628dcb03-624a-455c-a7bf-6b2491ce1e45,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,60.5,2024-05-31 12:15:56+00:00,3,1,5
b8d5db51-6a13-43ec-85d6-21944fb72a1a,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Final,56.5,2024-06-14 12:55:56+00:00,3,1,7
b37cbbdc-3468-4593-a8d8-9029dd9ac9ab,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Midterm,55.5,2024-06-28 16:02:00+00:00,3,1,9
a8cf9558-0233-46fd-826c-3ccddb9ecaca,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,54.0,2024-07-05 17:59:27+00:00,3,1,10
3bb04677-4489-4d02-8b5b-a9d6960402d2,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Quiz,57.5,2024-07-12 04:22:53+00:00,3,1,11
0984d110-bf57-4360-9347-946a19d5ff14,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Quiz,53.5,2024-07-26 13:18:56+00:00,3,1,13
0a57c1c4-0d42-4fbd-b990-aeca0adb6e0a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Assignment,62.5,2024-05-03 05:21:36+00:00,3,1,1
a99d7a72-1155-412a-93b8-a5c659bcb8c4,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Assignment,60.5,2024-05-17 16:31:28+00:00,3,1,3
9c4f22ad-1bbe-44f7-98ce-c72c4bc8d192,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Quiz,62.5,2024-05-31 04:23:44+00:00,3,1,5
92417ce1-6643-41ef-ad0f-2dbf8c643832,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Midterm,54.5,2024-06-28 06:28:23+00:00,3,1,9
4373e713-5030-46a3-bfe7-08c7d531298f,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Midterm,52.5,2024-07-26 23:03:20+00:00,3,1,13
fd687325-4ddf-472f-bbc4-387a891cab48,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Quiz,54.0,2024-08-16 21:16:19+00:00,3,1,16
3bbb7014-f8c4-442f-a7fc-2a57a200c7d6,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Assignment,56.0,2024-05-11 02:35:02+00:00,3,1,2
046c8c03-2257-4baa-affe-aa9b17111930,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Quiz,57.0,2024-06-08 00:13:14+00:00,3,1,6
7b126995-0689-4be1-8286-7a3b71978b4f,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Quiz,60.0,2024-06-21 21:08:15+00:00,3,1,8
42b6dadc-524b-4c2d-9e12-e6c4f72cdc69,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Midterm,51.0,2024-07-05 12:00:10+00:00,3,1,10
853cf63d-f50d-4155-acb4-1579769438d8,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Midterm,55.5,2024-07-12 07:37:28+00:00,3,1,11
9ce0eb0c-5b48-43d4-94be-8816bd7a962d,c3e25355-5f44-456e-b452-18efaf9cf6e5,C107,Computer Networks,Assignment,55.0,2024-08-02 16:18:02+00:00,3,1,14
7b7604f6-c060-451d-b343-324e061a848d,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,56.5,2024-05-03 06:10:09+00:00,3,1,1
728b4ae9-ef4f-4031-ac3c-719ca18b90ab,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,57.5,2024-05-17 08:38:15+00:00,3,1,3
486c59fc-28dc-4a06-b3ac-370a15131c49,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,60.0,2024-05-24 08:53:38+00:00,3,1,4
2bad2112-6944-4f88-a2c8-d034aff825a5,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,61.5,2024-06-14 23:42:49+00:00,3,1,7
3d140a4a-7093-4d0c-85b3-4767b84b9231,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,59.5,2024-06-28 18:02:32+00:00,3,1,9
4a1add7e-b62d-48d8-b09b-4aab79706173,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,56.0,2024-07-05 05:03:22+00:00,3,1,10
e7220845-3443-4c9b-882b-c14c1b9e0dc3,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,52.5,2024-07-12 22:12:56+00:00,3,1,11
619d7b84-4281-46d8-89bc-14b2f28bc4f7,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,59.0,2024-07-19 15:50:11+00:00,3,1,12
41f120a0-15ea-4198-b08e-5d627e9d3c80,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,55.5,2024-07-27 02:45:47+00:00,3,1,13
da7d17a8-91c2-4d0c-add8-6ea6df582028,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,49.0,2024-08-02 19:05:07+00:00,3,1,14
5c95569c-82bd-49ae-9c14-3a5591a85ab0,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,51.5,2024-08-09 11:27:31+00:00,3,1,15
7314498b-9134-45fc-aa57-08fafe32837c,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Assignment,64.5,2024-10-30 06:31:31+00:00,3,2,1
a80295cc-3d09-4541-85db-815c150bfdc4,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Midterm,62.0,2024-11-06 12:25:14+00:00,3,2,2
b1389e54-31c8-4443-a4ac-f43c8b020267,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Quiz,62.0,2024-11-21 01:17:33+00:00,3,2,4
c111312a-636a-4966-8caa-4bbf231bc48d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Assignment,56.5,2024-11-27 18:53:44+00:00,3,2,5
ac6c4b3e-1c0e-4da3-8699-5fe58ed83641,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Midterm,54.0,2024-12-04 04:15:30+00:00,3,2,6
788ffcaa-3f5a-49e6-9d2b-1a3bad65e0b3,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Final,61.0,2024-12-18 13:08:10+00:00,3,2,8
ef609e9c-3cc5-416d-9737-0672815984b9,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Quiz,56.5,2024-12-25 12:45:52+00:00,3,2,9
8a945b21-5397-40fa-b072-61526a75238a,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Assignment,57.5,2025-01-08 13:11:40+00:00,3,2,11
e6208460-a8b6-47ef-b050-0e24ff52886f,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Final,51.0,2025-01-15 16:12:50+00:00,3,2,12
54e37a8a-1416-47cd-81b8-d54c843d641b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Assignment,54.5,2025-01-22 04:42:49+00:00,3,2,13
bc29e3cc-1ad1-401f-8005-5e2eb4aa2267,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Midterm,54.0,2025-01-30 00:19:43+00:00,3,2,14
0fd640a4-5c2e-4c93-952a-3be3220dc0f2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Quiz,55.0,2025-02-12 15:29:27+00:00,3,2,16
805e63b4-a967-418e-87a1-f52b1adebc38,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,54.0,2024-11-06 21:48:44+00:00,3,2,2
9cda5c90-30bf-489e-a8bf-e39eb8e6d72d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,56.5,2024-11-13 21:48:38+00:00,3,2,3
38b4ffea-e746-4cc3-88ad-d6f90afd3dd3,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Assignment,56.0,2024-11-20 20:21:52+00:00,3,2,4
1ffe5e3a-8941-40ec-94bf-1c8b2950ff38,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,61.0,2024-12-04 05:25:10+00:00,3,2,6
33560521-e828-4d7b-9750-4bec7a865c0e,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,58.0,2024-12-18 10:26:34+00:00,3,2,8
01e17992-fa6e-49ee-b12a-260140ac3209,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,55.0,2025-01-01 19:12:37+00:00,3,2,10
e6818665-0a06-4b99-82d3-ceed974b45dd,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,54.5,2025-01-08 06:18:02+00:00,3,2,11
84b00d32-7f41-464d-b073-6a4c719d71de,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,54.0,2025-01-15 11:27:28+00:00,3,2,12
86bbfaee-2dcf-487f-b09f-28be0fdde0fc,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,57.5,2025-01-22 08:43:30+00:00,3,2,13
ac2109a6-ba9e-4cc5-97c9-99b922e92b0d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,55.0,2025-01-29 11:36:08+00:00,3,2,14
1dde93cc-07f3-48ae-9998-4efd88fdd92c,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,47.5,2025-02-06 02:03:56+00:00,3,2,15
8b240b74-938f-4ba1-b88b-a05e7a2e58f8,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,52.0,2025-02-13 01:23:36+00:00,3,2,16
b9e71618-540c-4e55-a11e-924e5a9fc6ab,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Quiz,57.5,2024-11-14 03:11:17+00:00,3,2,3
205fb4b6-5c1e-4065-b1aa-3e0d838b36b1,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Final,56.0,2024-11-20 05:49:39+00:00,3,2,4
3d2a62c3-31b9-4de4-b72c-875ba9291f74,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Quiz,60.0,2024-12-04 18:01:47+00:00,3,2,6
345c1bab-a19d-4253-bd02-c965a371c273,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Assignment,50.5,2024-12-25 12:12:54+00:00,3,2,9
34481ca4-17ef-4d50-8212-5e6d0bae696b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Final,60.0,2025-01-01 23:48:08+00:00,3,2,10
a5728682-b393-4099-af3d-0ae3fba756a2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Assignment,57.5,2025-01-23 02:46:30+00:00,3,2,13
8ff0b75e-6892-440f-b5cd-b30068b48281,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Assignment,53.5,2025-02-05 10:14:31+00:00,3,2,15
5ba75496-cfcc-4660-91d7-1229fcfea18e,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Midterm,59.5,2024-10-30 18:03:55+00:00,3,2,1
09012c9a-6398-40c0-b719-0597e7f313df,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Quiz,59.0,2024-11-07 01:12:09+00:00,3,2,2
4e1d4f7a-ea79-4c92-b0e1-fc5b878d7f35,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Midterm,57.5,2024-11-14 00:40:47+00:00,3,2,3
e3a38d3a-8c8d-48c7-ac7e-f6899d485c5e,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Final,60.0,2024-12-04 14:50:15+00:00,3,2,6
699996d4-2c6e-4ad1-b289-4cc89451b9dc,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Midterm,57.5,2024-12-11 10:36:17+00:00,3,2,7
977bd48c-41ad-4803-a5a8-9b712ccab81d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Assignment,53.5,2024-12-25 18:57:22+00:00,3,2,9
d3e0dc77-1185-47a2-969e-cfea9c68f266,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Quiz,58.5,2025-01-08 18:34:37+00:00,3,2,11
9dcfa3ff-3f33-463e-9862-d5fe4c9db7bd,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Final,57.5,2025-01-23 03:35:34+00:00,3,2,13
5615b2c7-36e1-4d69-95ac-3eb3f4e197c3,2d943e4a-13c9-4324-90fc-4977145bdf1d,C107,Computer Networks,Final,53.5,2025-02-05 16:08:39+00:00,3,2,15
34c00877-6584-47d4-99a7-e2a250e91e80,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Quiz,58.5,2024-10-30 12:05:00+00:00,3,2,1
226481bd-b6f4-4c97-a916-2900549bc8c7,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Assignment,52.5,2024-11-27 21:42:15+00:00,3,2,5
aac81516-490c-435c-b923-1902b784c4ec,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Midterm,55.5,2024-12-11 13:55:07+00:00,3,2,7
0193cfa9-eac2-4315-a0f9-93d4f674c63a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Quiz,60.0,2025-01-01 18:22:42+00:00,3,2,10
6b8b0aec-4c3e-411d-a55f-e960e4a34bd4,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Midterm,56.5,2025-01-09 02:37:02+00:00,3,2,11
8120c0df-4101-48ca-8a9c-2320bc0b53d4,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Midterm,49.0,2025-01-16 02:45:36+00:00,3,2,12
0c47cb68-e9d1-45ce-bb70-5487a9c24bdf,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Quiz,53.5,2025-02-05 04:13:06+00:00,3,2,15
ee5ac545-da69-453e-bb82-81271937302d,52dbd570-530a-45e1-a2ee-6ce2520216e2,C100,Intro to Programming,Quiz,48.0,2025-02-12 09:04:20+00:00,3,2,16
59760c35-db78-4300-9319-133b621496d4,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Assignment,61.0,2024-11-06 10:40:04+00:00,3,2,2
621f101e-0c1c-4a58-b4fd-3300cfc50a09,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Quiz,63.5,2024-11-14 00:45:47+00:00,3,2,3
a317710b-4950-48ce-abd1-ab6fbadd3596,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,58.0,2024-12-05 02:37:50+00:00,3,2,6
20798af8-2358-4d35-9114-0a45fc669bca,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,54.0,2024-12-18 14:14:53+00:00,3,2,8
961618b4-9d2c-41ce-87be-7ffc1a3b2695,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Midterm,57.5,2024-12-25 06:02:29+00:00,3,2,9
f1203e0d-ff89-47b8-a265-4e779dc073bf,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,55.5,2025-01-08 17:43:08+00:00,3,2,11
98358ef7-92ef-401e-a60f-c09d8fb89778,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Midterm,58.0,2025-01-15 05:37:32+00:00,3,2,12
6eff690e-77e4-42a5-912c-cbafa6a09ff9,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Midterm,48.5,2025-01-22 21:25:51+00:00,3,2,13
cbfa3d05-b339-4ce3-a40e-65020bf66517,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Quiz,52.5,2025-02-05 21:58:23+00:00,3,2,15
f539b201-9739-4f2e-bc3d-a9830d41ed22,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Quiz,48.0,2025-02-13 00:47:16+00:00,3,2,16
70d18183-c6bf-4a91-b211-92f5f29d6e57,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Final,53.5,2024-11-13 14:27:54+00:00,3,2,3
0c7f5f60-4e6b-40fc-9087-9ad92844c6f7,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,52.5,2024-11-27 23:50:57+00:00,3,2,5
716456f7-74e4-4dbb-b6e6-2a7929e6e6b8,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Midterm,62.0,2024-12-04 11:09:34+00:00,3,2,6
7123ee74-4c46-4ec6-9908-c35350a192ed,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Assignment,59.0,2024-12-18 11:41:24+00:00,3,2,8
65fa5fb9-c016-4e38-bbad-29b3a458324c,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,50.5,2024-12-25 23:32:20+00:00,3,2,9
71bf8cde-03ca-47d9-aed3-a145d73783be,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Assignment,53.0,2025-01-01 23:56:41+00:00,3,2,10
85353678-7502-4486-a4ba-607214fdc4a6,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Assignment,57.0,2025-01-16 02:58:15+00:00,3,2,12
8e408b37-2e31-4173-8b09-3e940f625272,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Midterm,48.5,2025-01-23 02:29:31+00:00,3,2,13
8f7b34a9-7cef-4fc2-8f22-75e5d01886a8,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Final,55.0,2025-01-29 19:44:08+00:00,3,2,14
8e44ac87-6427-4bad-904d-2ffbf5b25663,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Midterm,52.5,2025-02-05 05:08:51+00:00,3,2,15
59c4cdd4-6d2d-4311-bfb2-6455b71713bc,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,58.5,2024-10-30 05:52:55+00:00,3,2,1
03ad0b2b-3b6e-4f0f-af69-367185c6d92b,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Quiz,55.0,2024-11-06 14:25:19+00:00,3,2,2
1afb6868-cc12-4dce-9bfc-3fc65fe1ee51,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Midterm,58.0,2024-11-21 01:18:20+00:00,3,2,4
39dbc0c3-d871-445b-bf31-6431c1932be0,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Midterm,58.5,2024-11-27 20:17:55+00:00,3,2,5
e015a7c2-07e5-4b90-8db5-936da0d16234,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,58.0,2024-12-04 09:34:09+00:00,3,2,6
aaed0df2-4976-47de-a546-cc36e39933ba,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Quiz,60.5,2024-12-12 02:44:04+00:00,3,2,7
18aef1e5-ac84-487e-ae05-eebd33d23b03,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Assignment,56.5,2024-12-25 12:45:05+00:00,3,2,9
aafd863f-ef1c-4fc0-bcf4-96bbb02b2813,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Assignment,53.0,2025-01-01 19:18:25+00:00,3,2,10
d92e855a-ca09-46c4-93d6-c8cc1c04e291,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,55.0,2025-01-15 17:28:20+00:00,3,2,12
ad024050-5b1c-4340-8f72-d7ecae58f0ef,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Quiz,54.0,2025-01-29 13:41:51+00:00,3,2,14
3421b233-487c-4c0a-b2f1-13b7c0226a33,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Quiz,56.0,2025-02-12 09:53:47+00:00,3,2,16
ef32f3d1-44b6-466f-8a47-96a985bac506,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Midterm,60.5,2024-11-13 20:52:45+00:00,3,2,3
31f326bd-2cbf-4b22-b732-b9b87bda51ff,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,55.0,2024-11-20 11:19:32+00:00,3,2,4
ccb4a13b-56c5-449f-8cb4-2539b9880d99,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,59.5,2024-11-27 06:23:49+00:00,3,2,5
4e8d86dd-1abd-4710-8222-db1295eed0e9,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,60.0,2024-12-04 10:07:36+00:00,3,2,6
b92e12a8-40e6-44b0-9126-ac2bbb0067cd,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Final,54.5,2024-12-11 06:26:45+00:00,3,2,7
7e0ef457-19d2-425b-a724-df936aedfd81,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Quiz,56.0,2025-01-01 21:44:23+00:00,3,2,10
a831621a-d0f1-4903-bd58-8ffb18c71b26,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Final,48.5,2025-01-22 08:22:10+00:00,3,2,13
257886e5-2e22-4d1a-b094-ec0fd5c56390,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Final,48.0,2025-01-29 09:36:24+00:00,3,2,14
284d9e76-a8d2-4845-94d0-d0a593291270,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,47.0,2025-02-12 04:51:22+00:00,3,2,16
d534da8c-1589-4c13-8932-ca85e103cceb,d4341dc6-04e1-498c-8d4b-abb221969162,C100,Intro to Programming,Quiz,62.5,2024-10-30 23:15:57+00:00,3,2,1
c17606ce-c356-4689-820f-3a143b58589a,d4341dc6-04e1-498c-8d4b-abb221969162,C100,Intro to Programming,Quiz,62.0,2024-11-06 18:43:21+00:00,3,2,2
dfac9071-56a8-4375-9b70-513c107e8506,d4341dc6-04e1-498c-8d4b-abb221969162,C100,Intro to Programming,Quiz,55.5,2024-11-13 12:35:34+00:00,3,2,3
dc2a4c79-e271-4a91-9bcb-dc70f23e0bb8,d4341dc6-04e1-498c-8d4b-abb221969162,C100,Intro to Programming,Midterm,57.0,2024-11-20 15:36:39+00:00,3,2,4
0c49fb24-f834-4c8a-acf0-95e48241c6a4,d4341dc6-04e1-498c-8d4b-abb221969162,C100,Intro to Programming,Midterm,57.5,2024-11-27 03:57:18+00:00,3,2,5
e7dceec9-2f07-45ce-870d-1584799cf10d,d4341dc6-04e1-498c-8d4b-abb221969162,C100,Intro to Programming,Midterm,60.0,2025-01-01 04:14:52+00:00,3,2,10
1af4c7b3-8a2b-4be0-bca8-cedbf7f2b5a9,d4341dc6-04e1-498c-8d4b-abb221969162,C100,Intro to Programming,Midterm,57.5,2025-01-08 05:52:36+00:00,3,2,11
19842da9-2036-4984-bf51-0086f2b5e419,d4341dc6-04e1-498c-8d4b-abb221969162,C100,Intro to Programming,Assignment,55.0,2025-01-15 16:13:25+00:00,3,2,12
31c17556-1dd4-49c1-8c9d-4bcbf5b9d474,d4341dc6-04e1-498c-8d4b-abb221969162,C100,Intro to Programming,Midterm,53.0,2025-01-29 20:54:28+00:00,3,2,14
b82c9e91-c200-44ec-aaef-f8679b1885c2,d4341dc6-04e1-498c-8d4b-abb221969162,C100,Intro to Programming,Quiz,50.0,2025-02-12 07:34:02+00:00,3,2,16
c2d28ab8-daa0-4aa4-9efb-ceddeb4237cc,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,61.5,2024-10-30 07:35:35+00:00,3,2,1
35af7782-5f30-4cad-8e7d-42431d771ae7,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Quiz,58.0,2024-11-06 20:59:58+00:00,3,2,2
f5259de6-1251-44d2-b3b0-4f9b655fa34b,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Quiz,56.5,2024-11-13 20:27:44+00:00,3,2,3
a33b595a-ba1d-466d-92f7-d1061fe7a03d,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Quiz,59.5,2024-11-27 09:57:36+00:00,3,2,5
86f1fd8e-5783-4e40-842a-7744d8550aaa,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,54.0,2024-12-04 15:22:43+00:00,3,2,6
c7f33998-532b-43db-a529-1d30f6943566,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,58.5,2024-12-12 01:51:17+00:00,3,2,7
5a118ccd-5a14-41b4-a096-ef1eadada339,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,57.0,2024-12-18 09:51:36+00:00,3,2,8
c821d0c7-1058-4627-8416-fb672ab768a2,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,59.0,2025-01-01 19:43:34+00:00,3,2,10
e8c4e67b-b2ac-4f95-848c-2ebf54f99f2b,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,55.0,2025-01-15 20:39:33+00:00,3,2,12
377586ea-16eb-4ae9-a5ca-7a50c290eda6,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,49.5,2025-01-22 23:42:57+00:00,3,2,13
8e96510d-027a-4218-a130-7bae4e89b342,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,48.0,2025-01-29 08:58:12+00:00,3,2,14
ddc009f4-b4c7-4755-9713-418ae4fc3271,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,56.5,2025-02-05 07:57:03+00:00,3,2,15
418d388d-c751-459c-8911-2f48322efd7e,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,53.0,2025-02-13 01:50:01+00:00,3,2,16
909a5c5a-9e59-4aee-a176-46ee431a2e58,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Midterm,54.0,2024-11-20 10:07:52+00:00,3,2,4
f2fc9bc0-70d1-41bd-a1e6-6de5cf5a8ec2,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Assignment,59.5,2024-11-27 14:09:04+00:00,3,2,5
95374810-5c00-457d-8212-75bb2d2d6ae6,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Assignment,54.5,2024-12-11 15:02:27+00:00,3,2,7
59bbee5f-8504-4420-a944-a2c817366edc,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Quiz,52.5,2024-12-25 21:40:24+00:00,3,2,9
ebc8c069-e59a-4ca1-8693-460d79a14c12,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Midterm,50.0,2025-01-02 01:28:58+00:00,3,2,10
998e9d81-b821-45e7-9967-b0a319d2cd7e,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Quiz,51.5,2025-01-08 16:38:46+00:00,3,2,11
e89f5bd8-95fd-44ae-96cf-d094eb24400b,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Assignment,58.0,2025-01-15 23:52:18+00:00,3,2,12
703994bb-4568-4c63-bc9f-989af0ecd03d,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Quiz,58.0,2025-01-29 07:41:09+00:00,3,2,14
b12549a9-f06d-4cb6-a3de-7e3733e75a3c,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Midterm,47.5,2025-02-05 17:21:10+00:00,3,2,15
75e1e5e1-824a-4684-820d-9427c1257e43,f37e112a-f649-4321-a042-ae5dff11d297,C103,Database Systems,Final,52.0,2025-02-12 17:37:52+00:00,3,2,16
c801fbf8-16bc-492c-9f94-346ef959fc2f,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,64.5,2024-10-30 11:10:19+00:00,3,2,1
1748bf7a-8812-4568-9d54-501ba952bb52,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,63.5,2024-11-13 23:10:45+00:00,3,2,3
50fd32e1-f3c3-41f5-9302-2b4862bf2361,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,58.0,2024-11-20 17:01:11+00:00,3,2,4
2e31ea27-c763-4be0-b784-dbbabdfb7609,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,62.5,2024-11-27 14:56:41+00:00,3,2,5
3e69654f-293b-474d-a5b9-768bcfdec366,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,57.0,2024-12-18 23:50:33+00:00,3,2,8
fd673ad2-5ffa-4bd2-92b8-aa103d2b370d,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,53.0,2025-01-16 00:20:11+00:00,3,2,12
e71c3100-0ecb-42e8-bcf2-53ac828bd0a4,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,49.5,2025-01-23 01:15:21+00:00,3,2,13
38d85eea-ea25-4ecf-9c2d-74b5955b762b,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,57.0,2025-02-12 20:05:06+00:00,3,2,16
59708313-82bd-4cce-84d4-d7a04e1ef7d6,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,64.0,2024-11-06 13:59:02+00:00,3,2,2
37ef9e94-f547-44c7-833b-af1d1d70f504,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,56.0,2024-11-21 00:18:40+00:00,3,2,4
9591fc02-fb6c-4c09-b449-5161ada40ee2,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,62.5,2024-11-27 18:37:50+00:00,3,2,5
f98cb230-9f7f-4416-a97a-ad37405b8700,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Quiz,56.0,2024-12-05 02:13:05+00:00,3,2,6
f803a6c0-48de-4e4c-a425-33b44df973bb,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,56.0,2024-12-18 16:00:22+00:00,3,2,8
2d4131b7-74ea-40ce-bc3d-460d5539b852,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,53.5,2024-12-26 02:10:46+00:00,3,2,9
3e86cb03-978f-461f-accb-56d71ed15aa2,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,51.0,2025-01-01 06:56:14+00:00,3,2,10
f721b04b-8f61-4466-8ea8-291b633d493f,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,55.0,2025-01-15 14:54:31+00:00,3,2,12
23e565a5-564b-4c4f-a107-3a437967a2eb,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Quiz,54.0,2025-01-30 03:43:36+00:00,3,2,14
ac4224c4-6bf9-48c1-adc0-2c6f2ada2a06,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,57.5,2025-02-05 12:09:55+00:00,3,2,15
2e475bdc-7b75-4e25-bbde-e96b8ec5f7bc,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,50.0,2025-02-13 01:15:23+00:00,3,2,16
c8457dff-a2ce-4a91-91cb-f1c6fecaa179,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,62.0,2024-11-07 02:29:42+00:00,3,2,2
ddc1fb63-2112-4b5e-9c7a-b127be1f5cb5,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,56.0,2024-11-20 05:34:28+00:00,3,2,4
0e29df1e-9418-474a-8d80-c410e694888f,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,56.0,2024-12-04 12:57:38+00:00,3,2,6
d5928c62-1996-4cb9-a0a4-f160effc5fb2,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,53.5,2024-12-11 10:49:21+00:00,3,2,7
03ada5e5-c3fb-4c5b-9d14-dc5a3196607b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,53.0,2024-12-18 20:40:28+00:00,3,2,8
f475d074-ccdf-4562-b4f8-af886d379dc0,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,52.0,2025-01-01 18:23:05+00:00,3,2,10
446d64e8-d584-47a0-a31d-a54e95a2fd5a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,51.5,2025-01-09 02:56:31+00:00,3,2,11
3b1a605e-aa52-4086-a790-914c26b22576,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,49.0,2025-01-15 23:25:12+00:00,3,2,12
ba5de800-c22c-4a62-bf0c-b5f0fe714792,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,53.5,2025-01-22 17:43:49+00:00,3,2,13
8d408bfb-a3ef-45dd-a40e-035ecf636f2d,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,53.0,2025-01-29 05:22:58+00:00,3,2,14
11cfa5c5-7eba-4de5-ad68-0317a17940b2,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,55.5,2025-02-05 12:46:28+00:00,3,2,15
99ed8a72-b8f8-4515-a5c1-fd562c227121,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Quiz,54.0,2024-11-07 01:55:04+00:00,3,2,2
8734d039-ff60-4385-ad1a-911a9a373dd6,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Midterm,58.0,2024-11-20 17:36:24+00:00,3,2,4
1e317408-2ce1-4929-8839-d7ba3a862c41,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Midterm,60.0,2024-12-05 02:58:10+00:00,3,2,6
f8a06a20-c710-46ae-9564-d71cd00ac06c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Assignment,55.5,2025-01-08 17:32:27+00:00,3,2,11
a9d4cb0d-94be-49b0-8239-0a4cc63aed89,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Midterm,49.0,2025-01-29 04:42:32+00:00,3,2,14
a9f35587-2bc4-4951-b61a-f323bd43b445,c3e25355-5f44-456e-b452-18efaf9cf6e5,C109,Cybersecurity,Quiz,55.0,2025-02-12 07:51:11+00:00,3,2,16
52ddcc28-4951-409b-a9f3-c7bb1f92edc9,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,57.5,2024-10-30 04:30:38+00:00,3,2,1
3bff0dc8-3845-4bc0-8512-83dc134c1c1a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Assignment,53.5,2024-11-13 04:13:43+00:00,3,2,3
5f8fd3c2-b3dc-4e4d-a753-98b1c2435bd6,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Final,54.0,2024-11-20 23:31:03+00:00,3,2,4
24f721a1-3f26-4be9-99fe-238aefb3e58f,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Final,59.5,2024-11-27 12:31:23+00:00,3,2,5
8ef36b44-4b75-49eb-9f05-0939eab2552d,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Quiz,57.5,2024-12-11 21:56:12+00:00,3,2,7
bf2a1d31-3cca-4279-afea-bf4793156bba,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Assignment,58.0,2024-12-18 18:51:05+00:00,3,2,8
a67ac860-35b6-4a16-a357-61a79c3a7665,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Assignment,54.5,2024-12-25 14:53:08+00:00,3,2,9
f284bc51-f177-4612-9e6a-697d9f2bd3ee,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,55.0,2025-01-02 00:40:27+00:00,3,2,10
c1227a07-83c2-43af-a442-bb9e1fc52c5d,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Assignment,53.5,2025-01-09 02:41:14+00:00,3,2,11
b4cf410b-c283-4845-b1dd-23aa3948f0f7,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Assignment,59.0,2025-01-15 06:17:35+00:00,3,2,12
2a8fbad3-519f-4276-836a-35882f07f7b8,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Final,55.5,2025-01-22 21:32:24+00:00,3,2,13
f2c74f9b-24f4-4d9f-a388-4d61b8bc8b62,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,48.5,2025-02-06 03:27:03+00:00,3,2,15
f566b817-ffaf-4a6c-a577-b406568a49c9,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Final,55.0,2025-02-12 21:35:26+00:00,3,2,16
15330553-8ee0-4aac-91a4-44124c28ab8e,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Assignment,53.0,2025-05-05 13:40:21+00:00,4,1,2
00abacd5-6bab-4e7f-a95c-0d63a10902aa,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Assignment,53.5,2025-05-12 07:45:16+00:00,4,1,3
99eb59db-d507-4071-b6f2-876b0d7ad634,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Assignment,52.0,2025-05-20 03:30:21+00:00,4,1,4
5fc0f55e-a048-479a-938f-4f524253810a,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Quiz,44.0,2025-06-02 04:17:59+00:00,4,1,6
7d9922d5-7b45-4cb7-9df1-c7a3766c225e,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Assignment,44.5,2025-06-09 21:48:05+00:00,4,1,7
8332e623-5698-4eeb-9e6d-79f9453dcd92,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Assignment,40.0,2025-06-30 14:16:39+00:00,4,1,10
d62128e8-1fe2-4245-81f4-5db4aafa4dac,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Quiz,44.5,2025-07-07 23:06:56+00:00,4,1,11
ccbf8ea3-7b99-4ca5-94f0-5a40d86cc0d9,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Final,47.5,2025-07-21 04:37:07+00:00,4,1,13
a8b7b969-e001-4363-ba95-6e270e643371,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Midterm,44.0,2025-07-28 22:53:20+00:00,4,1,14
845d9e29-cfbf-4adb-9762-1a86a16fee7f,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Assignment,45.5,2025-08-04 23:47:50+00:00,4,1,15
7d09bb28-c60e-4da5-8c88-7be9979013d0,2d943e4a-13c9-4324-90fc-4977145bdf1d,C108,Artificial Intelligence,Quiz,37.0,2025-08-11 23:09:01+00:00,4,1,16
d6bbdd25-cdae-4642-9564-b0c765b33a85,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Midterm,51.5,2025-05-12 12:02:16+00:00,4,1,3
4958ad3d-b0b0-42b0-b4e3-729fb2ea5d67,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Final,46.0,2025-05-20 03:23:37+00:00,4,1,4
15d91149-b3c2-4ee2-b260-28b377be3405,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Assignment,48.5,2025-06-09 22:47:30+00:00,4,1,7
37a712bc-996b-428b-9bc6-d6782d5ed086,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Final,50.0,2025-06-16 18:32:00+00:00,4,1,8
b4d0c288-d1fb-413c-a0cf-cf493770dfec,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Assignment,47.5,2025-06-23 08:04:26+00:00,4,1,9
2cde16fa-ee55-4340-b89b-8c030e8f30ad,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Midterm,49.0,2025-07-15 02:37:16+00:00,4,1,12
664c0c0d-20d5-4a61-83cc-798f8de12ebb,2d943e4a-13c9-4324-90fc-4977145bdf1d,C109,Cybersecurity,Quiz,40.0,2025-08-11 20:11:47+00:00,4,1,16
cd2a49ef-feb1-4ca9-8b7e-9a0478686b2f,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Quiz,47.5,2025-04-28 06:57:03+00:00,4,1,1
78ca7135-df83-4c50-9b69-4595c3ca94d5,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Midterm,51.0,2025-05-05 09:40:00+00:00,4,1,2
30097bad-ceb0-4c70-99e7-1472c9421e6b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Assignment,45.5,2025-05-12 04:58:53+00:00,4,1,3
ae2428a0-33c7-40c0-b2bd-03adabe8f001,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Final,47.0,2025-05-19 08:51:55+00:00,4,1,4
32a1e119-f18c-41a2-80d5-cf8b7965c951,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Midterm,49.5,2025-05-26 08:22:46+00:00,4,1,5
89f6d446-f9a3-467d-a060-82caf080fb0b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Final,47.0,2025-06-02 04:40:22+00:00,4,1,6
b3d78e80-76a4-45a4-af66-e9242ee6e292,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Quiz,45.5,2025-06-23 06:27:34+00:00,4,1,9
d1fd5a59-0b16-4e2c-8ac9-babbdfcdf030,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Quiz,45.5,2025-08-04 13:31:01+00:00,4,1,15
566f3ee0-76c1-49e6-b384-ca73f1da766b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Quiz,47.0,2025-08-11 19:53:53+00:00,4,1,16
d1e1de23-49fa-4490-9930-27dacb45f3ea,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Assignment,46.5,2025-05-26 21:53:12+00:00,4,1,5
f73c96ba-d12f-4183-9c2a-346e052bb8e6,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,47.0,2025-06-02 14:44:06+00:00,4,1,6
fe795fb8-179b-4a81-8dd4-65c5c1703c99,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,44.5,2025-06-23 05:09:57+00:00,4,1,9
0b03d050-3307-4fd2-a5af-85be78255eaa,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,48.0,2025-06-30 23:24:36+00:00,4,1,10
0dd8b923-e6ad-49ad-9e77-c44eaef0b7af,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,42.5,2025-07-07 04:48:11+00:00,4,1,11
8685733f-938f-4983-bcc4-2fe38fe7f582,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,45.0,2025-07-15 01:00:42+00:00,4,1,12
06bcc44c-397d-4f76-8db7-bff654550fc5,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Assignment,43.0,2025-07-29 02:49:00+00:00,4,1,14
8e4d4ea1-45ae-4343-bef0-4fe7a2605d72,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,47.0,2025-05-06 00:23:27+00:00,4,1,2
85f0c418-5e9b-4247-ad03-719b95acc8f6,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,49.5,2025-05-12 07:16:17+00:00,4,1,3
d199198a-d0f2-4fc4-9e66-26828cddd945,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,48.0,2025-05-20 03:43:42+00:00,4,1,4
ea4daf17-4cd8-4174-854a-713151294c29,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Midterm,44.0,2025-06-03 00:05:47+00:00,4,1,6
2b69de32-e507-4b83-b41e-faf74137ceed,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Assignment,50.0,2025-06-16 08:14:45+00:00,4,1,8
67741f95-f644-4543-9faa-1a2491fae614,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Quiz,48.5,2025-06-23 16:09:09+00:00,4,1,9
b8d2dba4-3f2f-4880-b0e8-62a77083c8a6,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Quiz,48.0,2025-06-30 13:38:19+00:00,4,1,10
e2de5d8e-39e7-428d-9f76-2fbef23628a8,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Midterm,44.5,2025-07-07 20:46:57+00:00,4,1,11
28d79255-29d2-4bac-a681-3907d54f6d05,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Midterm,39.5,2025-07-21 22:54:03+00:00,4,1,13
17449fdd-6c5d-4506-ac51-401bd463ac39,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,44.0,2025-07-28 04:19:13+00:00,4,1,14
14cc43f3-f56b-4fb0-8248-b0de1d6f7b10,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Quiz,43.0,2025-08-11 15:58:24+00:00,4,1,16
756fb7e7-905e-4831-ae76-d47c9e0ad2da,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Assignment,48.5,2025-05-12 21:16:22+00:00,4,1,3
cd5c3817-c0e0-45ab-b612-3a66c77c185d,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,47.5,2025-05-26 19:23:38+00:00,4,1,5
a77a0cd5-9ed8-4250-a177-1160ad0803cf,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,46.0,2025-06-02 12:18:20+00:00,4,1,6
f9b548ab-d62e-4015-92fb-3babf763fc5a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Midterm,48.5,2025-06-09 13:51:09+00:00,4,1,7
1d37c333-5d45-4ce9-80be-cf347f36c43a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,42.0,2025-06-16 07:18:26+00:00,4,1,8
1293ad5c-031c-4ffa-97d0-ca46f4a7b2f6,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Assignment,49.5,2025-06-23 04:57:55+00:00,4,1,9
f2a94fd7-1aa7-40bf-8a87-23b39d34e1e6,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,48.5,2025-07-07 15:34:15+00:00,4,1,11
8b1be710-8b97-442b-9e54-16478b39b4f2,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,40.0,2025-07-15 01:21:31+00:00,4,1,12
416df1ed-d769-4d6e-8f56-59d535b42bc3,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Final,46.5,2025-08-04 04:15:25+00:00,4,1,15
bfb0ee4a-8ae5-4adc-8e61-ee2c0ca48f9f,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,49.5,2025-04-28 05:44:39+00:00,4,1,1
584a2615-abf9-4d1e-98f1-7586aa9ff3ea,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Assignment,44.0,2025-05-06 01:17:02+00:00,4,1,2
eb696ab7-b74a-44bc-80a2-4e50f43d09c3,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,44.5,2025-05-12 20:35:36+00:00,4,1,3
6adc79c6-f024-4cb4-8533-6f36d1081a77,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Assignment,44.0,2025-06-02 20:25:04+00:00,4,1,6
5d817f00-a692-40d8-806e-08fc62138705,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Final,48.0,2025-06-16 21:22:30+00:00,4,1,8
0b44f8c8-da6e-4078-a188-56ea24f652e4,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Quiz,44.5,2025-06-23 19:04:02+00:00,4,1,9
ba34bc92-35af-4989-a715-8fe1eff13086,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Midterm,46.5,2025-07-07 10:36:42+00:00,4,1,11
a8415586-1737-47b2-bdc4-c03ba13e7a70,52dbd570-530a-45e1-a2ee-6ce2520216e2,C107,Computer Networks,Assignment,39.5,2025-08-04 13:45:55+00:00,4,1,15
cb86cc5e-6e9a-4385-850a-24eb224bd0a1,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,53.5,2025-04-28 17:30:42+00:00,4,1,1
b3dae6d3-b773-44a2-acfa-efd0c4039a39,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Assignment,51.5,2025-05-12 23:01:31+00:00,4,1,3
6042c97c-525b-4584-b37a-b70fb9bc1ede,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,45.5,2025-05-26 10:52:40+00:00,4,1,5
ebdae092-09c2-4ee4-acf9-e059984288d2,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,45.0,2025-06-02 04:08:40+00:00,4,1,6
e2c7f88c-261c-498e-a266-45079ab5cb77,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Final,41.5,2025-06-10 00:39:50+00:00,4,1,7
9d0c6e7c-b638-4173-9df7-004a13494d09,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,50.0,2025-07-01 02:06:58+00:00,4,1,10
21207be9-ac4e-4402-8eae-86c8d40e23d1,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,45.5,2025-07-07 17:24:28+00:00,4,1,11
9132da9e-283b-4754-ae48-a301a659a8e5,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Final,47.0,2025-07-14 07:39:11+00:00,4,1,12
71578feb-edef-414a-89f8-32437785d48d,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,42.5,2025-07-21 04:49:00+00:00,4,1,13
1940bf05-c361-4946-b527-d5cf98fe210d,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,45.0,2025-07-28 08:56:00+00:00,4,1,14
fa62b043-bef6-4063-8e9f-004000ebfd43,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,40.5,2025-08-04 14:45:55+00:00,4,1,15
2c5229d7-ef4e-4769-930b-a5d5da2b17c3,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,38.0,2025-08-11 21:43:04+00:00,4,1,16
73c7eaca-466a-4e7e-a20a-6388e4791b26,d4341dc6-04e1-498c-8d4b-abb221969162,C107,Computer Networks,Midterm,47.0,2025-05-05 10:12:08+00:00,4,1,2
716e9c18-62da-4628-9c8d-416ead78e1e4,d4341dc6-04e1-498c-8d4b-abb221969162,C107,Computer Networks,Midterm,43.5,2025-05-12 06:22:06+00:00,4,1,3
fbdca3cc-025d-47d5-bd5d-bf9c9336b7e0,d4341dc6-04e1-498c-8d4b-abb221969162,C107,Computer Networks,Final,46.0,2025-05-19 08:56:14+00:00,4,1,4
af805960-b1c8-462e-8a40-c5b6de5ff99a,d4341dc6-04e1-498c-8d4b-abb221969162,C107,Computer Networks,Midterm,45.0,2025-06-02 07:22:11+00:00,4,1,6
5d5fb31e-efe7-403a-87e9-75beb0b89f2f,d4341dc6-04e1-498c-8d4b-abb221969162,C107,Computer Networks,Quiz,43.5,2025-06-09 21:38:24+00:00,4,1,7
87f53a98-cf5b-4de3-bbcb-4be7aebae450,d4341dc6-04e1-498c-8d4b-abb221969162,C107,Computer Networks,Midterm,51.0,2025-06-16 13:57:57+00:00,4,1,8
ef2addfd-188e-4e0f-bea1-d35f9aeef61c,d4341dc6-04e1-498c-8d4b-abb221969162,C107,Computer Networks,Midterm,49.5,2025-06-23 11:52:38+00:00,4,1,9
c2edaf68-312b-4f16-bd4d-0de3b79626af,d4341dc6-04e1-498c-8d4b-abb221969162,C107,Computer Networks,Assignment,44.5,2025-07-07 06:25:57+00:00,4,1,11
892d3fac-9c2f-4fb3-b2e7-8f373a102640,d4341dc6-04e1-498c-8d4b-abb221969162,C107,Computer Networks,Midterm,44.0,2025-07-14 04:51:21+00:00,4,1,12
fab99f87-bd55-4e71-b5e6-8c09ea8847a1,d4341dc6-04e1-498c-8d4b-abb221969162,C107,Computer Networks,Final,45.5,2025-07-21 15:46:44+00:00,4,1,13
d551830e-88be-4b65-984b-d553df4b1bf4,d4341dc6-04e1-498c-8d4b-abb221969162,C107,Computer Networks,Midterm,47.5,2025-08-04 05:07:45+00:00,4,1,15
9817ceaa-048b-437b-a95b-35ba9b03854a,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,45.5,2025-04-28 23:24:15+00:00,4,1,1
b61c7c98-8ff0-4573-978d-6011bbfd51d7,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Assignment,44.5,2025-05-13 03:18:51+00:00,4,1,3
8fa0cc9a-600f-4000-aafb-f76d23d92c99,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Assignment,44.0,2025-05-19 17:43:25+00:00,4,1,4
cdeccb72-7372-4f87-aaa5-cd358cc16c04,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Assignment,52.5,2025-05-26 23:15:34+00:00,4,1,5
2abc815a-7157-47a6-871c-7e2d0a0a0ac4,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,44.0,2025-06-03 00:39:41+00:00,4,1,6
671d3b05-0836-4856-a983-976127199926,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Assignment,50.5,2025-06-10 01:17:02+00:00,4,1,7
c442c90f-f3d6-43b5-9a24-a7883184442b,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Assignment,43.0,2025-06-16 05:12:22+00:00,4,1,8
55529b22-3359-4fa5-abcf-4455a008d383,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Assignment,50.5,2025-06-23 09:47:57+00:00,4,1,9
16e44db3-d21d-434d-b1cc-b9ef85c51e4a,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,47.5,2025-07-07 08:37:06+00:00,4,1,11
61bcdc34-b0e2-4d37-9d64-ac61bca9bca2,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,43.0,2025-07-14 04:33:31+00:00,4,1,12
717d010b-4ab9-4f4c-91ff-ec99fc3b4411,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Quiz,41.5,2025-07-21 23:43:45+00:00,4,1,13
6daa612a-6441-4bbb-b029-b15eaba6bfa6,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Midterm,38.0,2025-07-29 03:41:15+00:00,4,1,14
d52df43c-6b63-45e8-abe6-ea238e08135f,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Quiz,47.5,2025-08-04 23:03:18+00:00,4,1,15
e0f3183f-775f-48c8-80cc-efa15ee31e26,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,45.0,2025-08-11 21:56:02+00:00,4,1,16
6bb4202c-6f68-41f7-8c74-dc087e95f86e,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,45.5,2025-04-28 20:46:05+00:00,4,1,1
48721b93-06e9-4555-8b20-4c7d26ead0e4,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Midterm,47.5,2025-05-12 19:46:56+00:00,4,1,3
2163ddd2-484a-4a8c-a145-810eeb34a460,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Assignment,47.0,2025-05-19 03:55:53+00:00,4,1,4
cd5abd7a-423f-4777-a3e0-4048d692c480,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Assignment,43.5,2025-05-27 02:46:54+00:00,4,1,5
030beba4-a620-46c3-a785-9012544b7420,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Midterm,44.0,2025-06-16 10:24:38+00:00,4,1,8
eec8bcdb-4518-4d52-872f-0b590cc760d7,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Midterm,49.5,2025-06-24 02:29:52+00:00,4,1,9
84ceeecd-b61e-4f2f-b9e3-6dbcce220bb2,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Quiz,50.0,2025-06-30 04:02:52+00:00,4,1,10
566a07bc-eec3-4955-be97-67a12470d5c0,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,44.5,2025-07-07 11:46:06+00:00,4,1,11
f1912990-f0ca-48f8-ab33-89ac585a02fc,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Assignment,47.0,2025-07-14 11:09:10+00:00,4,1,12
b12160e9-e694-4f3b-b33d-1951bcdc612b,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Final,42.0,2025-07-28 18:59:40+00:00,4,1,14
254542c0-a386-419c-a43f-d11fca9ee88d,d4341dc6-04e1-498c-8d4b-abb221969162,C104,Operating Systems,Midterm,39.0,2025-08-11 17:57:25+00:00,4,1,16
5fe6d857-1605-4a15-bf13-5ee56758a959,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Assignment,49.5,2025-04-28 13:31:21+00:00,4,1,1
315230ac-7a8c-4b97-8585-59b31f8cb460,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Midterm,46.0,2025-05-05 21:47:49+00:00,4,1,2
a41d6571-3000-4cfe-a88f-00ccd8a49ef6,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Assignment,45.0,2025-05-19 14:07:59+00:00,4,1,4
29cc1122-4476-4efc-bbec-1cfcdf0e2b07,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Midterm,43.5,2025-06-09 11:07:58+00:00,4,1,7
4c2309f9-4f88-48f7-abae-ecc82105b7b0,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Final,42.0,2025-06-30 04:04:54+00:00,4,1,10
2b021720-f04a-4de8-ba22-08d0079b2bcf,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Assignment,44.0,2025-07-14 05:07:11+00:00,4,1,12
0cbc37e8-c3fd-497c-a8ff-7d3d823a9224,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Final,40.5,2025-07-22 03:28:12+00:00,4,1,13
e2e95848-037e-46ed-8d87-4c760f8aa1aa,d4341dc6-04e1-498c-8d4b-abb221969162,C109,Cybersecurity,Assignment,43.0,2025-07-28 18:16:16+00:00,4,1,14
0c70d0a2-8e8a-480e-bbc0-a741ac25f869,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Assignment,43.5,2025-05-13 01:40:08+00:00,4,1,3
b00bd927-f7c7-44b8-8ef7-0718d79580c4,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Final,52.5,2025-05-26 09:45:29+00:00,4,1,5
a16f33e3-a00d-4099-a65b-c641267d67e8,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Quiz,44.0,2025-06-02 23:39:44+00:00,4,1,6
aef46d2a-a954-4147-bb22-95931b9e5673,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Final,43.0,2025-06-16 21:14:46+00:00,4,1,8
d8da8048-82fe-45fc-aad2-2c375c61c615,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Quiz,41.0,2025-06-30 08:28:20+00:00,4,1,10
6fecf500-de45-468a-b318-c42a38b386a0,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Midterm,39.5,2025-07-07 10:04:23+00:00,4,1,11
de26ed02-7db2-4cdb-9e4b-4cf397f65150,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Midterm,42.0,2025-07-14 03:53:33+00:00,4,1,12
3ebf6d63-2c4f-4552-8975-248094a3c232,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Midterm,40.0,2025-07-28 08:48:45+00:00,4,1,14
c9427f3f-00b0-4370-ae88-e6347c734ca9,f37e112a-f649-4321-a042-ae5dff11d297,C107,Computer Networks,Midterm,41.0,2025-08-11 07:06:36+00:00,4,1,16
a14252f0-d0d7-4bef-8566-29518368876b,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Assignment,45.0,2025-05-05 04:45:42+00:00,4,1,2
4ed3b5c6-5727-4372-8ace-9d17c3ab9db1,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Midterm,46.0,2025-05-19 22:44:20+00:00,4,1,4
054ee784-2686-4761-9909-f3d01e0b3d4f,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Assignment,45.5,2025-05-26 13:25:19+00:00,4,1,5
d11ca18e-28f7-4209-8f6e-1311aae69187,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Midterm,46.0,2025-06-02 04:43:44+00:00,4,1,6
cef51d6f-9fd9-417f-8e99-a71f838b18ed,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Assignment,49.5,2025-06-10 01:14:33+00:00,4,1,7
61e140e3-447a-4ff1-92fc-767f3f5d35a8,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Final,50.0,2025-06-16 04:08:18+00:00,4,1,8
6b76cd7e-c3ea-4a88-88ef-aade3ba27e2f,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Assignment,44.5,2025-06-23 07:29:55+00:00,4,1,9
3e3539cc-3804-4c58-b360-758c23bc89e7,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Final,42.0,2025-06-30 12:20:36+00:00,4,1,10
a420961d-2c52-4635-957a-4ff41ddd0746,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Assignment,46.5,2025-07-08 00:38:26+00:00,4,1,11
f0a53ae1-8945-45c8-a1b0-deee3ef925ad,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Midterm,40.0,2025-08-11 11:09:33+00:00,4,1,16
7e1c4d7f-6b6c-44e8-b4cf-cef0f12fd96e,f37e112a-f649-4321-a042-ae5dff11d297,C104,Operating Systems,Midterm,54.5,2025-04-28 16:25:45+00:00,4,1,1
a49af4a7-d19b-4928-9f8f-0ab48e8a83d3,f37e112a-f649-4321-a042-ae5dff11d297,C104,Operating Systems,Final,43.0,2025-05-19 10:49:00+00:00,4,1,4
8d51d310-40ec-4230-b8dc-0af63c97d236,f37e112a-f649-4321-a042-ae5dff11d297,C104,Operating Systems,Assignment,48.5,2025-05-27 02:11:01+00:00,4,1,5
73ff65bb-af25-4752-998e-327cac0067e1,f37e112a-f649-4321-a042-ae5dff11d297,C104,Operating Systems,Quiz,50.5,2025-06-10 01:31:23+00:00,4,1,7
dff46ce1-aec7-4443-aa36-fe2ae92a4cc9,f37e112a-f649-4321-a042-ae5dff11d297,C104,Operating Systems,Final,42.0,2025-06-16 09:37:15+00:00,4,1,8
a4f4c734-f739-45db-95e9-667a635e30d5,f37e112a-f649-4321-a042-ae5dff11d297,C104,Operating Systems,Assignment,46.5,2025-06-23 12:24:56+00:00,4,1,9
2ff585d3-0d9e-4fd8-8f66-91e0216f1b43,f37e112a-f649-4321-a042-ae5dff11d297,C104,Operating Systems,Quiz,43.0,2025-06-30 17:45:12+00:00,4,1,10
b3952346-b356-48dd-93ee-d42385eca176,f37e112a-f649-4321-a042-ae5dff11d297,C104,Operating Systems,Quiz,43.5,2025-07-21 13:56:33+00:00,4,1,13
e5673198-48fb-4652-94af-d33b5796b0f9,f37e112a-f649-4321-a042-ae5dff11d297,C104,Operating Systems,Midterm,48.0,2025-07-28 13:33:12+00:00,4,1,14
1619ca8c-e74f-4423-a96d-540eb08b374b,f37e112a-f649-4321-a042-ae5dff11d297,C104,Operating Systems,Midterm,37.5,2025-08-05 00:08:23+00:00,4,1,15
d21c27ae-4537-4e15-bea5-6f78b32fd1b7,f37e112a-f649-4321-a042-ae5dff11d297,C104,Operating Systems,Quiz,39.0,2025-08-11 06:43:58+00:00,4,1,16
191d2f50-b491-4711-b504-297eced25c77,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,45.5,2025-04-28 14:14:24+00:00,4,1,1
1a589f1a-1e68-4910-b291-d28f1e74509c,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,51.0,2025-05-05 13:04:21+00:00,4,1,2
253974d5-6d94-4a97-bf71-18a8d8ac9bc0,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,49.5,2025-05-12 06:02:37+00:00,4,1,3
8b715f62-aa07-4996-9c88-e917e3f43efe,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,48.0,2025-05-19 21:30:24+00:00,4,1,4
713296e5-4138-4ef8-b59a-e3f23e6b0cc4,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,51.5,2025-05-26 06:57:42+00:00,4,1,5
33b085a4-c338-446d-909b-500faf3c4244,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Quiz,52.0,2025-06-03 02:13:38+00:00,4,1,6
339abd01-3fb0-496b-b421-95dff6c8e376,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Quiz,41.0,2025-06-16 06:38:51+00:00,4,1,8
ea458862-f9b0-41e0-938b-454e46e36da2,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Quiz,46.5,2025-06-23 11:53:48+00:00,4,1,9
0d25aae9-ff13-426c-8e36-eb5b5ac16535,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,42.5,2025-07-08 03:42:51+00:00,4,1,11
076fe131-4a54-466a-97ab-ca54734bfded,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,48.0,2025-07-28 19:20:27+00:00,4,1,14
fd5068af-dc42-48f6-801a-c0ac4033f481,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,39.5,2025-08-04 14:56:18+00:00,4,1,15
84d2e456-a872-4e91-8405-a8948a5fbc91,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,46.0,2025-08-11 11:10:33+00:00,4,1,16
e98c7ad1-82c2-4cbf-98c9-01a21527bfa8,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,51.0,2025-06-16 20:33:33+00:00,4,1,8
51a2d077-8e08-453c-8716-efd21f4f2462,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,40.5,2025-06-23 15:46:42+00:00,4,1,9
9e169ed3-8df5-4c28-aa8d-ba05945eddd2,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,50.0,2025-06-30 07:35:06+00:00,4,1,10
18a66a52-1bf1-4b1c-b10a-36f6d7a309a2,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,49.5,2025-07-07 05:46:26+00:00,4,1,11
b36a2ac1-bfc1-4dc3-9128-a1f20c8eabd7,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,43.0,2025-07-14 18:05:56+00:00,4,1,12
44614a5f-32ab-49e4-a62e-41751e8463f9,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,40.5,2025-07-21 21:31:32+00:00,4,1,13
1a6854ff-1e5d-4fb5-b625-ab31faa9053c,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,40.0,2025-07-28 22:57:19+00:00,4,1,14
cbcd0024-075d-4f41-9ffd-8a98657f2363,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,40.5,2025-08-04 11:53:47+00:00,4,1,15
b6d6c7a7-c9cd-4894-886c-9765177e1216,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,50.5,2025-04-28 12:08:58+00:00,4,1,1
a1190f17-c19f-475e-941d-012f9881c3b4,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Quiz,46.0,2025-05-05 17:07:17+00:00,4,1,2
1682f998-c75e-44a7-b15b-43adeb287887,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,47.5,2025-05-12 17:14:26+00:00,4,1,3
1dfa6102-f866-4b00-a35b-2dd53484f0d6,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,47.0,2025-05-19 05:36:15+00:00,4,1,4
e84f30b2-3166-4575-aea8-a0e1c8b9eb1b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,46.5,2025-05-26 15:23:40+00:00,4,1,5
626cf383-ac67-4239-ae12-291fe36c628b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,44.0,2025-06-03 00:33:58+00:00,4,1,6
6fbad616-b2da-47c1-89a4-b4d691770c05,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,44.5,2025-06-09 12:00:29+00:00,4,1,7
74d73c1a-078b-44e5-b624-f30119a3f438,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,39.5,2025-07-07 23:57:24+00:00,4,1,11
88111bd5-61b8-4e65-9d05-12b458c2f915,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,39.0,2025-07-14 15:59:12+00:00,4,1,12
43a40ee6-09b4-4da0-be22-aa31ee77d884,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,38.5,2025-08-04 19:05:54+00:00,4,1,15
3c5ad318-3692-4942-ba45-1e9d00696655,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Midterm,52.5,2025-05-26 20:55:21+00:00,4,1,5
95fcc527-43f3-4ff7-8893-5a9ccd0b2255,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Midterm,43.0,2025-06-02 06:43:31+00:00,4,1,6
59043dd5-1785-4963-8623-23f93c0998f4,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Final,43.5,2025-06-09 12:34:23+00:00,4,1,7
1114ab00-ef8f-4e6d-8868-93cb49524b89,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Quiz,42.5,2025-06-23 08:23:42+00:00,4,1,9
add2bd62-2de8-4c21-9ed5-c408da0a5d7c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Assignment,48.0,2025-06-30 14:15:37+00:00,4,1,10
7b9fd7b4-6195-40d5-8be1-db21afe7a2a3,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Assignment,43.5,2025-07-07 05:58:44+00:00,4,1,11
83755a72-4091-47ca-a751-e43449281381,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Quiz,44.0,2025-07-14 15:47:55+00:00,4,1,12
44ee836f-7979-405f-b266-4b6f33f4524b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Assignment,45.5,2025-07-21 19:45:04+00:00,4,1,13
c3700e9e-48f8-477d-8776-977a2cc0d2ae,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Assignment,38.0,2025-07-28 16:18:26+00:00,4,1,14
bbbcc9be-8d48-479b-bb8f-88f5816a1300,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Final,38.5,2025-08-04 14:16:01+00:00,4,1,15
1aea871b-8d24-46be-a3db-694cbf4cc342,c3e25355-5f44-456e-b452-18efaf9cf6e5,C101,Data Structures,Quiz,45.0,2025-08-11 13:57:11+00:00,4,1,16
d36df9cd-c873-4df8-866e-c893055b5526,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Final,45.5,2025-04-29 03:19:53+00:00,4,1,1
5e5e1707-c1df-4956-a1f5-99d682eeb9a0,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Midterm,53.0,2025-05-05 11:30:50+00:00,4,1,2
0f4ec2df-53c2-414d-8742-2013a93dc8be,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Quiz,49.5,2025-05-27 03:23:48+00:00,4,1,5
a0cb15c8-7847-44ec-9ca1-ba259dd40c2b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Quiz,47.0,2025-06-02 10:23:01+00:00,4,1,6
b0f9f2dd-a320-4e12-826d-fb29da6ec515,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Assignment,47.5,2025-06-09 15:26:12+00:00,4,1,7
819abba7-b720-48f4-b649-69f2df6a46c1,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Final,42.0,2025-06-16 20:04:42+00:00,4,1,8
8342af87-4397-4c66-b6f4-609488eeb072,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Midterm,44.5,2025-06-23 16:30:23+00:00,4,1,9
1ac45e32-04df-423f-aed8-693f27f73dba,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Assignment,50.0,2025-06-30 12:12:49+00:00,4,1,10
85c60fb4-b806-489f-a924-7d338e69c63e,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Final,43.5,2025-07-07 19:58:40+00:00,4,1,11
a60ac97f-e72f-4eec-9c04-e3054d166cdd,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Quiz,38.0,2025-07-28 17:10:28+00:00,4,1,14
3e146875-8649-4c8c-a79c-e10cd6d82a5c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Assignment,43.5,2025-08-04 05:21:44+00:00,4,1,15
230d9851-463e-4add-9922-9a246054c09c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C103,Database Systems,Midterm,44.0,2025-08-11 22:31:20+00:00,4,1,16
35a95228-5358-4db5-9da5-0d7261c3aeea,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Final,45.5,2025-04-28 09:33:45+00:00,4,1,1
a25303c8-18ed-4d08-baa4-cae1d9b9afc3,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Assignment,52.0,2025-05-05 09:28:59+00:00,4,1,2
e2ba5d22-a411-4007-9155-67513cd593aa,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Final,46.5,2025-05-12 23:57:08+00:00,4,1,3
a937b5f5-50e8-4c62-8622-3a0211e42c8c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Midterm,45.0,2025-05-19 10:42:47+00:00,4,1,4
e2884f28-989a-47b9-ad85-d2688cb554d0,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Assignment,50.5,2025-05-26 06:38:27+00:00,4,1,5
33139315-a00a-41d5-8697-5e4f9df95bd7,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Final,42.5,2025-06-09 07:42:04+00:00,4,1,7
c55f0c18-3736-4814-8045-2ea650270089,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Final,46.0,2025-06-16 04:57:00+00:00,4,1,8
6b49cab7-f9b2-4f9e-a009-21fb37843365,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Assignment,40.5,2025-06-23 05:06:30+00:00,4,1,9
3a206183-34fe-4bb6-80df-df57674f8bd0,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Final,40.0,2025-06-30 23:47:35+00:00,4,1,10
8aa3c5fa-7917-4055-9445-f793ab5013a1,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Assignment,45.0,2025-07-14 04:43:51+00:00,4,1,12
f3ab4d1c-cf3c-4e27-a031-7ed055bacdbf,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Assignment,44.5,2025-08-04 07:00:57+00:00,4,1,15
2758ae1f-52cb-4f7c-addd-46f2078a9121,c3e25355-5f44-456e-b452-18efaf9cf6e5,C104,Operating Systems,Assignment,46.0,2025-08-11 04:31:26+00:00,4,1,16
db63c7d7-8406-465e-9ac2-783751f0dcbd,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Midterm,53.5,2025-05-12 23:38:00+00:00,4,1,3
d0d9e52a-92cf-4c19-b4ce-6acbabb93a8e,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,49.0,2025-05-19 13:17:32+00:00,4,1,4
b85f89e4-534e-48ee-8e21-113d436cf50b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,46.0,2025-06-02 19:10:43+00:00,4,1,6
4d2444dc-7027-4da2-9846-89190c3e6704,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,48.5,2025-06-09 16:33:23+00:00,4,1,7
8c410ab2-4b1a-4e1e-b658-57d49ee4dbc0,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,42.0,2025-06-16 21:34:11+00:00,4,1,8
a4fd1465-4c79-4e5f-848e-f409ad6aa41a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,46.5,2025-06-23 18:43:48+00:00,4,1,9
892a2b30-0dc4-4551-bc8d-18da46de491e,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,47.0,2025-07-01 00:06:03+00:00,4,1,10
efe873d3-dbb5-4374-9049-a4c5ff79788e,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,40.5,2025-07-07 11:07:03+00:00,4,1,11
6b130d84-3cc5-4665-80c9-5fb5afeb19ab,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,45.0,2025-07-15 03:04:45+00:00,4,1,12
254fa027-f0ac-4fe2-a4e9-54772b29fcf5,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,43.5,2025-07-21 16:58:51+00:00,4,1,13
78dd24db-935c-40a8-8724-b7c85c3a2b1c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Quiz,47.0,2025-07-28 09:55:09+00:00,4,1,14
551c6cdd-ab17-485d-9861-2985f5776a7a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Assignment,46.5,2025-08-04 09:06:49+00:00,4,1,15
4bf103d5-3338-44c6-872f-69706ea18cf6,c3e25355-5f44-456e-b452-18efaf9cf6e5,C108,Artificial Intelligence,Final,42.0,2025-08-11 04:07:18+00:00,4,1,16
fe263eb8-860b-41c7-872b-5d5dc7f1e228,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Final,46.0,2025-11-01 07:42:12+00:00,4,2,2
2d1a79df-ba27-4f49-a1fd-f2c069d11752,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Quiz,46.5,2025-11-08 20:21:39+00:00,4,2,3
c17c756b-3bc6-40c6-9366-92fa6e50119b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Assignment,50.5,2025-11-23 01:25:32+00:00,4,2,5
9bfc9293-64c4-488f-a314-caca03a19019,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Quiz,47.0,2025-12-13 08:10:11+00:00,4,2,8
c7bc672e-8d76-4b24-81fe-06476f79e1dd,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Quiz,40.5,2025-12-20 04:13:03+00:00,4,2,9
ba4613da-8b28-47e6-866c-a881732432d5,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Final,45.0,2025-12-27 22:38:29+00:00,4,2,10
8a526bd3-c10c-4196-8478-ead18a9c2a6c,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Assignment,46.5,2026-01-03 06:59:29+00:00,4,2,11
78639735-6825-4183-a3c7-5b18394cea6c,2d943e4a-13c9-4324-90fc-4977145bdf1d,C100,Intro to Programming,Quiz,46.0,2026-02-07 17:07:53+00:00,4,2,16
ad55c3d3-2a64-46cb-acb8-e584a7f0091f,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Quiz,46.5,2025-10-25 18:30:21+00:00,4,2,1
49fcad74-ad1c-4c7e-9496-ef0ad6663b83,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Midterm,46.0,2025-11-02 03:04:30+00:00,4,2,2
fedbb2e6-c015-404b-8b3f-b55fe64cd5f3,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Assignment,53.5,2025-11-08 09:09:57+00:00,4,2,3
acd6baaa-34e2-4df3-b006-1ee740df185a,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Final,49.5,2025-11-22 19:55:06+00:00,4,2,5
ae34ee9b-6edd-4234-8648-fdc6ef8e1b34,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Assignment,48.0,2025-11-29 13:25:15+00:00,4,2,6
764b1e2a-bf5c-4ba1-ab3f-908f2ddb3d8b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Quiz,45.0,2025-12-14 00:50:14+00:00,4,2,8
17c173e9-4db4-416e-9b01-84bd0064d30a,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Assignment,44.5,2025-12-20 19:38:41+00:00,4,2,9
ad4e07d2-d320-4c2a-ad48-3ee977c8bb9a,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Assignment,44.5,2026-01-17 08:55:02+00:00,4,2,13
4acdcf51-f5cb-4cf2-9a2b-3b2b56ba5cd2,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Assignment,44.0,2026-01-24 19:44:47+00:00,4,2,14
ee3e0559-db24-43e3-8060-6de278843f00,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Final,46.5,2026-01-31 14:21:24+00:00,4,2,15
7242ce15-091d-46b8-80c9-31db5aa16f7f,2d943e4a-13c9-4324-90fc-4977145bdf1d,C105,Machine Learning,Final,47.0,2026-02-07 12:46:10+00:00,4,2,16
55fda200-a4df-4f8e-9d19-6361290a0b3b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,50.0,2025-11-02 01:33:05+00:00,4,2,2
b76060ce-1899-4e6e-8d8d-c62909b68d18,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Midterm,50.5,2025-11-08 20:13:16+00:00,4,2,3
2f9a7d81-68a8-4d3d-a715-ff51088751fd,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,51.0,2025-11-15 17:33:31+00:00,4,2,4
96370f58-ca6c-48f5-9009-7a1389c83568,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,48.5,2025-11-22 20:42:33+00:00,4,2,5
b80c6961-f513-4363-8ef6-bb8d2d27022d,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,50.0,2025-11-30 01:20:17+00:00,4,2,6
c2b9a166-6e1e-4850-bea2-daf183678b50,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,44.0,2025-12-13 09:39:01+00:00,4,2,8
e98f3012-d4b5-44a9-9a67-026bc6386ce0,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Final,49.0,2025-12-27 16:24:10+00:00,4,2,10
66e97406-c2a7-4482-8b04-72493b0c26aa,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Assignment,49.5,2026-01-03 13:19:58+00:00,4,2,11
e3a3467d-8fce-4703-82a6-53f00110c659,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,40.0,2026-01-10 14:40:41+00:00,4,2,12
a287e119-b2a5-4910-85ef-e8ea626f1225,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,42.5,2026-01-17 16:43:07+00:00,4,2,13
3098bafc-88aa-456f-a7c9-4f412a9e1491,2d943e4a-13c9-4324-90fc-4977145bdf1d,C106,Software Engineering,Quiz,38.0,2026-01-24 15:49:58+00:00,4,2,14
ba6b3348-29d4-4407-b431-b0406ba1ab21,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,47.5,2025-10-25 07:28:51+00:00,4,2,1
2de0c5c3-f489-4963-94c1-c4472cda4c7b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,52.5,2025-11-08 17:58:42+00:00,4,2,3
79367c7e-53ec-4431-bd78-943d01af2777,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,53.0,2025-11-15 23:33:28+00:00,4,2,4
310fbb55-e1f2-40d6-a0ce-60d9980d2806,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,51.5,2025-11-22 20:05:11+00:00,4,2,5
ca5afa0c-a8bf-42bf-83cb-b764af8fd7dd,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,50.0,2025-11-29 14:25:29+00:00,4,2,6
6e20cede-e776-44a7-af3f-3baea36abbfa,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Quiz,44.5,2025-12-06 07:26:41+00:00,4,2,7
138f80b5-b614-46b9-b403-f50a94b7ffec,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,43.0,2025-12-13 23:41:45+00:00,4,2,8
a8994b80-f822-49d7-bd75-cda5bc023be8,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Assignment,42.0,2025-12-27 07:25:03+00:00,4,2,10
1b13050e-fbef-4f57-9ad5-4625a4707c92,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,41.5,2026-01-03 23:05:26+00:00,4,2,11
48277bcd-87f3-4031-8bbe-52e2338640df,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,48.0,2026-01-10 19:47:52+00:00,4,2,12
83764aef-4dd2-47f7-b8ea-d6eb28bf063f,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Midterm,43.5,2026-01-18 01:24:54+00:00,4,2,13
70d50b59-dcb1-441e-8240-92b1dcceef64,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,47.5,2026-01-31 19:55:15+00:00,4,2,15
a4fe778e-af95-4222-b933-f7e3425b2d83,2d943e4a-13c9-4324-90fc-4977145bdf1d,C101,Data Structures,Final,37.0,2026-02-07 05:56:48+00:00,4,2,16
b8f16e55-d58f-410a-8c54-0f30fdc241fa,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Midterm,47.0,2025-11-01 17:19:44+00:00,4,2,2
ad5caec1-af80-4e35-aecb-8408eb3e8a4c,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Final,48.5,2025-11-08 05:04:28+00:00,4,2,3
f5b6b790-d330-4193-aa15-1cf4208206e3,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Assignment,47.0,2025-11-15 16:07:21+00:00,4,2,4
6442e4b0-9b7e-4946-9cdb-b704a3af10b0,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Assignment,44.0,2025-11-29 22:54:47+00:00,4,2,6
b2247e93-a815-4324-a31e-7bf451b98d5b,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Quiz,46.5,2025-12-06 22:42:44+00:00,4,2,7
c2384734-c00a-4dd3-b029-b6940227ac06,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Quiz,41.0,2025-12-13 16:35:42+00:00,4,2,8
d5ea5f73-2b00-45a1-b8f8-f352042d9469,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Quiz,45.0,2025-12-28 02:51:10+00:00,4,2,10
3c2b1277-1c6a-4470-b8ab-cab84e848dfc,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Midterm,41.5,2026-01-03 20:29:06+00:00,4,2,11
016d026d-6ca0-43e6-9ef7-f895552e804e,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Midterm,48.5,2026-01-17 14:08:33+00:00,4,2,13
49f67f4f-cbdd-4a26-bb3f-40089fe61cb0,2d943e4a-13c9-4324-90fc-4977145bdf1d,C104,Operating Systems,Midterm,44.0,2026-02-07 19:10:52+00:00,4,2,16
82c6cba5-542b-40cb-903d-140f53cb778e,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Quiz,44.5,2025-10-26 02:06:09+00:00,4,2,1
2e7741cb-b6a4-4b49-86a8-edc7072863b0,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Assignment,45.0,2025-11-15 15:06:34+00:00,4,2,4
2b9ced1c-9b19-4efd-82c5-4ab71bfc91db,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Quiz,50.5,2025-11-22 23:57:24+00:00,4,2,5
c9402e89-da26-403c-8bc6-c325681c73c7,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,43.0,2025-11-29 20:39:15+00:00,4,2,6
8edf7a2c-7fa3-4ec6-92c9-a4a636648cbd,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,51.5,2025-12-06 20:46:32+00:00,4,2,7
d809fa64-e65a-46ef-ac9e-d123699fc963,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Assignment,44.0,2025-12-13 11:30:56+00:00,4,2,8
834477a7-3831-4d91-aeed-6e334c128f8a,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,46.5,2025-12-20 04:48:30+00:00,4,2,9
c242eb68-b7f3-484e-93bd-0b22e82e9fd6,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,40.0,2025-12-27 11:49:00+00:00,4,2,10
f835b134-180f-4f48-b500-a0a463f7079b,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,47.5,2026-01-04 00:15:41+00:00,4,2,11
ae5fffb4-aa52-4a5b-a8c7-b6a2f2d6b109,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Midterm,40.5,2026-01-31 13:11:55+00:00,4,2,15
d0ab5e4b-c85e-4629-8d91-7e4b556086ab,52dbd570-530a-45e1-a2ee-6ce2520216e2,C102,Algorithms,Final,40.0,2026-02-07 09:13:14+00:00,4,2,16
ced5a98e-c5b1-4759-a68f-f25a63fcb9de,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Quiz,53.0,2025-11-01 14:31:38+00:00,4,2,2
d23fce3d-3559-455c-879e-a83767e6e586,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Midterm,49.5,2025-11-23 03:37:37+00:00,4,2,5
ce5ed9d9-8986-4c20-94c2-e0959c7858f8,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Midterm,50.0,2025-11-29 21:24:51+00:00,4,2,6
1f65f117-d304-4527-a502-8239785fe1ac,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Quiz,45.5,2025-12-06 20:09:02+00:00,4,2,7
2767d8e3-7e35-4e00-a8d8-e01447500d1e,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Midterm,45.0,2025-12-13 22:50:11+00:00,4,2,8
088fa02f-5dba-48e9-9fa5-3055b1e6773e,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Final,43.0,2025-12-27 13:32:44+00:00,4,2,10
e080b27d-8c69-4d22-b251-ec86ac5ce140,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Final,40.0,2026-01-10 11:37:43+00:00,4,2,12
b1931545-b800-4532-9860-f6a84f6f9e44,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Assignment,39.5,2026-01-17 07:10:38+00:00,4,2,13
7654b012-796c-4489-aacc-4d5f07d8dada,52dbd570-530a-45e1-a2ee-6ce2520216e2,C108,Artificial Intelligence,Quiz,43.0,2026-02-07 09:22:20+00:00,4,2,16
ab766918-05f3-44ef-9e8c-746e1d729d53,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Assignment,53.0,2025-11-15 20:20:44+00:00,4,2,4
a3956eb0-25f9-487d-84cb-e9c8e67d25ae,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,48.5,2025-11-22 19:26:07+00:00,4,2,5
17b96951-a92b-4987-ad1a-dfd3ba8f6b27,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,43.0,2025-11-29 10:47:21+00:00,4,2,6
7b7daa65-df02-4d64-a4f7-8d272b008ba0,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Assignment,48.5,2025-12-06 19:29:20+00:00,4,2,7
4b9d7878-6d2d-460e-893e-2a86f111b4cb,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,41.0,2025-12-13 17:23:24+00:00,4,2,8
1a5667ac-c913-47d8-8e93-b5ef8ed637ff,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Midterm,49.5,2025-12-20 07:17:29+00:00,4,2,9
4fd2f157-aee5-4932-96b5-f026c000da69,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Final,45.0,2025-12-27 08:25:28+00:00,4,2,10
b0232659-78b5-4a7e-a3a9-ac7263d8cd64,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Final,45.0,2026-01-10 13:43:34+00:00,4,2,12
4d24a9e2-9905-4f14-9c63-8be3ea0e0322,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Assignment,45.5,2026-01-17 16:13:12+00:00,4,2,13
ee3e8269-2f88-447c-9c78-13bde20fa878,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Final,42.0,2026-01-24 16:50:12+00:00,4,2,14
dc758214-c3a4-4463-8b76-0fb1654f5ac2,52dbd570-530a-45e1-a2ee-6ce2520216e2,C103,Database Systems,Quiz,47.0,2026-02-07 15:03:03+00:00,4,2,16
314816eb-11bb-4007-8587-457bd3d6a4cc,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,51.0,2025-11-01 23:35:39+00:00,4,2,2
e405d297-e3b7-459e-b9b2-9bebc524a8be,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Assignment,47.5,2025-11-09 02:19:02+00:00,4,2,3
5eca2db1-cdd6-4583-9640-d9e865ac5e88,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Midterm,45.0,2025-11-15 12:06:43+00:00,4,2,4
7f2ac2e5-d74c-44b7-a9a1-f0094dc795e1,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,42.5,2025-11-22 18:27:38+00:00,4,2,5
891df468-60ef-4956-8fdf-ef6f97094a09,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,43.0,2025-11-30 00:06:36+00:00,4,2,6
3f3a272a-c41d-4044-a7e9-9119baf37c40,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,44.5,2025-12-06 22:34:49+00:00,4,2,7
6926eb83-9f8e-4b39-a976-0ad639b6ecae,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Final,41.0,2025-12-13 10:16:27+00:00,4,2,8
b68a4e5b-cda8-4909-950e-327fc9561f19,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,50.5,2025-12-20 14:07:39+00:00,4,2,9
fb6d5dd0-3285-40dd-8e51-4a01e63f00ed,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Quiz,40.5,2026-01-03 12:26:24+00:00,4,2,11
32992645-17b6-4a96-b2c5-6dbb267a4293,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Final,40.5,2026-01-17 16:34:55+00:00,4,2,13
39800919-788d-4459-8c4d-95c0d95a3130,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Midterm,40.0,2026-01-24 04:43:57+00:00,4,2,14
6707fcd4-f919-46c4-b58d-848155ba8568,52dbd570-530a-45e1-a2ee-6ce2520216e2,C101,Data Structures,Midterm,44.5,2026-01-31 15:15:31+00:00,4,2,15
dbf59da7-e8af-4fd8-9290-de3b7f67b9b1,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Midterm,51.5,2025-10-25 16:02:22+00:00,4,2,1
3ec5bdc8-7c43-4a9a-a991-bb64c531e356,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,49.5,2025-11-09 00:13:00+00:00,4,2,3
7f0dc4fa-48c8-4f25-8873-3728d038ec3e,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Assignment,48.0,2025-11-15 18:14:38+00:00,4,2,4
9607c6b8-b37d-4283-9fbb-f5600d51e622,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Midterm,42.5,2025-11-22 16:53:10+00:00,4,2,5
e4f53bdc-97e5-403a-8a59-15e0607193de,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Midterm,49.5,2025-12-20 18:34:50+00:00,4,2,9
cb4a5d06-40b3-43f6-bc79-b70bb63eaf89,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Quiz,42.0,2025-12-27 05:28:24+00:00,4,2,10
4122a4ea-30b6-4ba2-b3cb-819ad1d950c2,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Quiz,40.5,2026-01-03 16:35:02+00:00,4,2,11
ceaf1f69-4858-415e-98fb-b8d37ac09488,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Assignment,45.0,2026-01-10 20:39:50+00:00,4,2,12
9deff927-5ecf-4846-b6f5-6d571a7216ee,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,39.0,2026-01-24 10:30:08+00:00,4,2,14
8cb7ffd4-f3a3-46dd-a65f-8b3ce9dbd419,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Final,46.5,2026-02-01 00:27:12+00:00,4,2,15
5cb93a71-1644-4cc3-8182-a6803af16c4b,d4341dc6-04e1-498c-8d4b-abb221969162,C106,Software Engineering,Quiz,47.0,2026-02-07 19:59:47+00:00,4,2,16
6c3c2614-9132-4f0e-b790-23acd50866c1,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,54.5,2025-10-25 07:57:09+00:00,4,2,1
e81731d1-6120-4e09-928d-f6d9c59e622f,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,53.0,2025-11-01 22:32:17+00:00,4,2,2
80da314e-5b28-4905-9ff1-1ad8d7d41c10,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,44.5,2025-11-08 16:47:50+00:00,4,2,3
d9e537bb-f68a-4a9b-9e22-ceeb850b2b17,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Quiz,48.5,2025-11-23 02:29:14+00:00,4,2,5
8dfa25d0-c37f-491b-84a6-e3ec4ad5b186,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Quiz,52.0,2025-11-29 11:25:16+00:00,4,2,6
e1ed441c-ec65-4131-9327-08c0a86729b1,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Quiz,50.5,2025-12-06 04:32:48+00:00,4,2,7
da81ba13-966e-48c8-86ee-e38e7f2236bf,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,51.0,2025-12-13 05:52:05+00:00,4,2,8
24517467-aa7b-4da3-ad11-5795eb37f11b,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Midterm,46.5,2025-12-20 22:20:25+00:00,4,2,9
fe4db5be-1f3a-4f03-9d98-7591d7878b8c,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Final,46.0,2025-12-28 00:03:17+00:00,4,2,10
f143baaf-55b4-493d-9f50-0d7a6080eaf1,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Midterm,38.5,2026-01-18 00:33:13+00:00,4,2,13
fcde48b1-fbb4-45f1-8bd4-b180ecc1476d,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Final,39.0,2026-01-24 23:40:27+00:00,4,2,14
77c46fac-e642-4604-ab81-aa54e6734869,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,38.5,2026-01-31 14:35:32+00:00,4,2,15
436cea34-ec4c-4b97-a11a-057302c78ad0,d4341dc6-04e1-498c-8d4b-abb221969162,C103,Database Systems,Assignment,41.0,2026-02-08 03:26:59+00:00,4,2,16
4c276b1c-3476-41b8-b48b-469865238ef8,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Quiz,49.5,2025-11-09 02:15:34+00:00,4,2,3
6d4695e1-d17e-474d-99e6-8dbeacb0ff69,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,52.0,2025-11-15 09:03:17+00:00,4,2,4
c4ef803a-ccac-4ca4-b97e-3b5d8d9ac01c,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Quiz,45.5,2025-11-22 22:09:13+00:00,4,2,5
46cc2c8f-0491-47f3-a899-ecc091cb0317,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,40.5,2025-12-20 20:41:59+00:00,4,2,9
f2910035-d24b-4758-8e81-21d531cbe314,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,45.0,2025-12-27 19:25:33+00:00,4,2,10
b3a6db62-6b18-4393-80e4-64394940a8c2,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,41.5,2026-01-03 21:40:27+00:00,4,2,11
e7970dc2-c239-4d17-98cb-45a27876a18a,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Midterm,49.0,2026-01-10 14:25:23+00:00,4,2,12
efd636ef-0e01-4cdb-bfcb-7e70fda8203a,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Quiz,48.0,2026-01-24 11:32:06+00:00,4,2,14
2a7312a7-ea5d-46bc-8043-bc6526c64548,d4341dc6-04e1-498c-8d4b-abb221969162,C102,Algorithms,Assignment,43.5,2026-01-31 17:24:51+00:00,4,2,15
e1439035-3434-40b6-9f4e-826c7c2ac361,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Quiz,53.0,2025-11-01 23:41:55+00:00,4,2,2
4963e5ff-a4d8-4c6e-af10-5e9f9b4b6341,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Quiz,50.5,2025-11-08 11:29:57+00:00,4,2,3
bcc567bf-57b9-4d73-b0b2-dabac2fe0128,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,52.0,2025-11-15 08:37:21+00:00,4,2,4
7714cd15-b4de-4c80-8b74-f1091fd84cc0,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Midterm,48.5,2025-11-22 10:08:22+00:00,4,2,5
7febfe0b-a5a8-4e07-87dc-28e658f87eeb,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Quiz,46.0,2025-11-29 13:50:06+00:00,4,2,6
8dd41c17-451d-44ed-852b-932a8bb76469,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,43.5,2025-12-06 04:50:43+00:00,4,2,7
90b1141b-ff6b-49b3-9cb1-fe76e888759b,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Midterm,49.0,2025-12-13 07:44:42+00:00,4,2,8
5c683c9d-18d8-45b9-a24f-d977d4e54b3a,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Quiz,42.5,2025-12-20 08:51:12+00:00,4,2,9
e375c516-133a-4b9e-9bd7-f97b7d3171a1,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Midterm,49.0,2025-12-27 18:19:30+00:00,4,2,10
81c3f07e-3cad-4af1-903f-b5b1cfeb4450,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Quiz,46.5,2026-01-03 15:51:23+00:00,4,2,11
795f6851-0f68-4b53-b21d-b9cfbd1edf4f,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Assignment,41.0,2026-01-25 01:04:12+00:00,4,2,14
1be606d5-17fd-4f6f-b466-75ccd5cc5f00,d4341dc6-04e1-498c-8d4b-abb221969162,C105,Machine Learning,Quiz,37.0,2026-02-07 23:10:59+00:00,4,2,16
8d2a0d78-ebf3-4333-993f-95a20c7ad3ac,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Quiz,45.5,2025-10-25 14:24:54+00:00,4,2,1
52e90151-48ca-4007-8366-20e27e9bfb66,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Final,43.0,2025-11-15 22:46:39+00:00,4,2,4
14fae381-83ce-4114-b716-80647c38cc3b,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Midterm,49.5,2025-11-23 01:22:18+00:00,4,2,5
1b56f104-e759-4607-a87f-c3a05d875fa1,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Final,45.0,2025-11-29 11:54:13+00:00,4,2,6
90297827-ac33-4243-a715-6dd0c1096d5a,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Midterm,45.5,2025-12-06 08:12:20+00:00,4,2,7
68e228e1-0eb0-4be0-91e4-ede7def18dc5,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Quiz,41.5,2025-12-20 11:26:48+00:00,4,2,9
a165fb13-fdab-459f-99b3-82071cb7558b,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Midterm,43.0,2025-12-28 01:58:23+00:00,4,2,10
6dc1996f-7f2c-4a2c-bd0c-6b487db8e821,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Midterm,39.5,2026-01-03 23:24:42+00:00,4,2,11
d5fa4286-b680-4acc-b72f-1ff40dca0b7e,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Midterm,48.5,2026-01-17 15:23:11+00:00,4,2,13
d7fe6f17-32a1-4e3d-8aaf-af059b1ed6be,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Midterm,44.0,2026-01-24 08:18:19+00:00,4,2,14
d0190f83-4fbc-444e-85d6-7157117b5c0f,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Midterm,41.5,2026-01-31 11:01:58+00:00,4,2,15
5cfab015-6d3d-43aa-866e-1ded1e50d879,f37e112a-f649-4321-a042-ae5dff11d297,C101,Data Structures,Midterm,45.0,2026-02-07 19:11:41+00:00,4,2,16
c1086c05-440d-4b1e-b3e1-dbca45aec64a,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,48.5,2025-10-25 08:34:42+00:00,4,2,1
bb71eda2-e011-40cb-8718-a6dd2ad4da2d,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Assignment,46.0,2025-11-01 20:12:40+00:00,4,2,2
62718d90-7bfc-47ec-9ab0-31ae5a8ca878,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,48.5,2025-11-22 12:14:12+00:00,4,2,5
871007d6-bd6c-4093-8452-744e6836c923,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,47.5,2025-12-06 05:35:49+00:00,4,2,7
386e19c1-6063-42a2-ae4e-a8f758ff4952,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,41.0,2025-12-14 02:40:51+00:00,4,2,8
c2875f24-e7a3-4890-b5c4-1a482db8c3f4,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Midterm,44.5,2025-12-21 01:09:34+00:00,4,2,9
9cf0c85a-7e18-4ed1-bf34-8075cd685853,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Final,46.0,2025-12-27 09:14:22+00:00,4,2,10
ec3c60bf-ade7-4ad9-9259-fd9bcc7d06e1,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,43.0,2026-01-10 18:02:12+00:00,4,2,12
3f7f3404-f46e-445d-85a6-d0d5f1b5c4a0,f37e112a-f649-4321-a042-ae5dff11d297,C108,Artificial Intelligence,Quiz,41.5,2026-01-31 17:35:52+00:00,4,2,15
55704209-7c8e-450b-a229-01ce97235e90,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,44.0,2025-11-01 18:58:17+00:00,4,2,2
ecd4ade7-5d07-4169-b697-16dcb8dbf6f2,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,43.5,2025-11-22 08:02:54+00:00,4,2,5
ca7ccc5c-7ecd-4b7d-894f-d55d294d988d,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Quiz,52.0,2025-11-29 21:43:12+00:00,4,2,6
f4e9412b-62f3-42b3-825e-9c70d62ff54f,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Quiz,45.0,2025-12-13 14:29:52+00:00,4,2,8
31759fb6-67b9-4933-942d-e368a8c1bd05,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Assignment,44.5,2026-01-03 20:01:08+00:00,4,2,11
86f372aa-4d60-4c60-9543-ca38daf7009e,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Midterm,45.0,2026-01-24 19:38:33+00:00,4,2,14
b0817f80-01fd-46f5-9347-6f74042411f4,f37e112a-f649-4321-a042-ae5dff11d297,C106,Software Engineering,Midterm,38.0,2026-02-07 10:32:03+00:00,4,2,16
fbe4ba9d-a9fe-48e0-ab62-195a066b7498,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,48.5,2025-11-09 01:01:30+00:00,4,2,3
5e824445-e9fd-46be-b572-9fc9db470c90,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Assignment,49.0,2025-11-15 07:35:06+00:00,4,2,4
8e78ca24-cb3d-4ff9-8c90-73f6d39ba348,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,42.5,2025-11-22 16:07:21+00:00,4,2,5
c2bdc3dd-d4c9-418f-b6ef-7824c5ea2852,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,45.5,2025-12-06 16:40:59+00:00,4,2,7
bbbc4f1f-9bc6-4bfe-8438-6e088743a2cd,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,50.0,2025-12-13 13:43:11+00:00,4,2,8
30d1c33e-781d-4d56-b646-876ceed13ecf,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,46.0,2025-12-27 12:13:18+00:00,4,2,10
fe17197c-e527-48b7-8a5a-d5172bd63f44,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,43.5,2026-01-03 07:55:39+00:00,4,2,11
a5af79f2-909e-423a-8fbc-2dd4cdfb34f9,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,46.0,2026-01-10 20:03:36+00:00,4,2,12
2eeba538-b503-48d3-a7b8-c4a66c6edbbb,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,40.5,2026-01-17 06:02:44+00:00,4,2,13
a9713470-332c-4204-b309-c8964854e231,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,44.0,2026-01-24 21:27:36+00:00,4,2,14
73353e6e-2abf-41cc-88db-d69cb68a0b1b,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Midterm,43.5,2026-01-31 15:20:04+00:00,4,2,15
3603a145-65f7-435a-995c-540922e869ed,f37e112a-f649-4321-a042-ae5dff11d297,C100,Intro to Programming,Final,39.0,2026-02-08 01:17:35+00:00,4,2,16
069ef4cd-9f1d-4664-9c88-01954433753d,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,46.5,2025-10-25 08:04:08+00:00,4,2,1
527cdf65-a7fd-4512-b978-e2f29bc308e4,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Quiz,46.0,2025-11-01 10:04:43+00:00,4,2,2
03ce3a7d-ad80-4db3-b3df-6aea963a4aed,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Quiz,46.5,2025-11-08 19:30:43+00:00,4,2,3
44924336-704f-46bd-bdaf-99272d679004,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Quiz,46.0,2025-11-15 05:38:57+00:00,4,2,4
18edb0da-e9fc-4a7d-9f15-378baeff2a46,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,50.5,2025-11-22 21:18:27+00:00,4,2,5
b22ef9cc-17f5-4641-8be9-857433d524dd,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Assignment,45.0,2025-11-29 13:50:58+00:00,4,2,6
701e6b80-2843-4b57-9492-108a8578b38c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Assignment,43.5,2025-12-07 01:03:31+00:00,4,2,7
1c9ce5e6-0a2c-45d7-b32b-e4731b40c279,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,43.5,2025-12-21 03:06:18+00:00,4,2,9
43a5ea7d-369a-4796-8466-6e7221de0982,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Final,40.0,2025-12-27 12:30:49+00:00,4,2,10
13059c9c-7e06-4c77-bb71-86007957e1d8,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,44.5,2026-01-03 04:44:18+00:00,4,2,11
70a58eec-93eb-4168-ad6a-afdde48da11a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Final,39.0,2026-01-10 22:45:08+00:00,4,2,12
16f6e41f-8e30-44b7-bd6a-4fc987089242,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,44.0,2026-01-24 08:41:09+00:00,4,2,14
08d08055-7507-41d2-be7b-40b4944a6c49,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Quiz,47.5,2026-01-31 10:03:20+00:00,4,2,15
f5f62c4c-c695-4469-a482-771e3589664c,c3e25355-5f44-456e-b452-18efaf9cf6e5,C102,Algorithms,Midterm,38.0,2026-02-07 04:18:22+00:00,4,2,16
63f590f0-0db2-4c71-908e-772413176b45,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Quiz,46.5,2025-10-25 07:19:09+00:00,4,2,1
2478ffd7-360c-4131-aea1-75527b89bde1,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Assignment,45.0,2025-11-01 10:48:52+00:00,4,2,2
365ee161-bc8d-4cd1-b798-78b69ac00135,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Midterm,43.5,2025-11-22 18:56:16+00:00,4,2,5
49cf4ce4-3114-4eec-8735-f6e1d0044192,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Midterm,45.0,2025-11-29 16:30:56+00:00,4,2,6
48d84696-3f95-4eaa-9322-f7c4a0b50a3d,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Assignment,48.0,2025-12-13 08:47:28+00:00,4,2,8
71d3d5b5-16ae-4223-8555-97da938e5ccb,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Quiz,46.5,2025-12-20 04:53:02+00:00,4,2,9
533aff2b-97a3-4f83-8c4e-f59662833c6a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Final,41.5,2026-01-03 20:12:36+00:00,4,2,11
2eb1535b-5f00-4a0b-a3b7-e16561c1ab3b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Quiz,45.0,2026-01-10 11:18:29+00:00,4,2,12
ffe74a06-d1c4-49a6-8fb7-c4b0aa088f1e,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Assignment,39.5,2026-01-18 00:29:59+00:00,4,2,13
70d4a542-8a39-4011-a683-1a5b4312d671,c3e25355-5f44-456e-b452-18efaf9cf6e5,C105,Machine Learning,Midterm,46.0,2026-02-07 16:38:22+00:00,4,2,16
b608bbe0-9b2e-41dd-9fff-6b9f3cdef029,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,50.5,2025-10-25 04:52:02+00:00,4,2,1
b1bd2ecd-6658-422f-afb5-1afa8cc0e951,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Quiz,50.0,2025-11-01 18:42:51+00:00,4,2,2
3db558b6-9a0a-4401-8094-45cf3a4f8370,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,51.0,2025-11-15 23:44:06+00:00,4,2,4
bb745192-d6b8-4432-9bce-09bc8e257198,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,43.5,2025-11-23 03:13:58+00:00,4,2,5
11bd42ad-840e-41db-8efc-df803e002db8,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Quiz,47.0,2025-11-30 00:07:26+00:00,4,2,6
3bd7db15-7fd2-49a6-a8f6-8ce2b9454748,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,41.0,2025-12-14 01:52:45+00:00,4,2,8
17f0e1f8-7e46-4d0f-9fc7-00de7963f36b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,44.5,2025-12-20 21:48:07+00:00,4,2,9
12fda785-0d18-4964-bd9d-c92aced9cb1b,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Final,46.0,2025-12-27 05:08:06+00:00,4,2,10
ab0e5e01-e754-4f78-8761-35d477a133d8,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,46.5,2026-01-03 12:50:49+00:00,4,2,11
79be54ee-52f6-422c-aa6f-070b00f8619d,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Assignment,47.0,2026-01-11 00:41:31+00:00,4,2,12
a4721c12-6448-409d-bb7a-5a9ba213150a,c3e25355-5f44-456e-b452-18efaf9cf6e5,C100,Intro to Programming,Midterm,42.0,2026-01-24 03:55:45+00:00,4,2,14
`;

export const SIS_SAMPLE_CSV = `
    sid,student_name,email,major,current_risk_status,intervention_status,last_notified_timestamp,last_notified_satisfaction
    2d943e4a-13c9-4324-90fc-4977145bdf1d,Student 9,student_9@university.edu,Computer Science,Normal,none,1970-01-01 00:00:00+00:00,0
    52dbd570-530a-45e1-a2ee-6ce2520216e2,Student 10,student_10@university.edu,Software Engineering,Normal,none,1970-01-01 00:00:00+00:00,0
    d4341dc6-04e1-498c-8d4b-abb221969162,Student 11,student_11@university.edu,Physics,Normal,none,1970-01-01 00:00:00+00:00,0
    f37e112a-f649-4321-a042-ae5dff11d297,Student 40,student_40@university.edu,Data Science,Normal,none,1970-01-01 00:00:00+00:00,0
    c3e25355-5f44-456e-b452-18efaf9cf6e5,Student 88,student_88@university.edu,Mathematics,Normal,none,1970-01-01 00:00:00+00:00,0
`;

/** Concatenate two CSV strings sharing the same header row. */
export function mergeCsv(a: string, b: string): string {
    const trim = (s: string) => s.replace(/^\uFEFF/, "").trim();
    const aTxt = trim(a);
    const bTxt = trim(b);
    if (!aTxt) return bTxt;
    if (!bTxt) return aTxt;

    // Lấy header + body của hai file
    const aFirstNl = aTxt.indexOf("\n");
    const bFirstNl = bTxt.indexOf("\n");
    if (aFirstNl < 0 || bFirstNl < 0) return `${aTxt}\n${bTxt}`;

    const aHeaderLine = aTxt.slice(0, aFirstNl).trim();
    const bHeaderLine = bTxt.slice(0, bFirstNl).trim();
    const aBody = aTxt.slice(aFirstNl + 1);
    const bBody = bTxt.slice(bFirstNl + 1);

    // Nếu header giống nhau thì giữ logic cũ (bỏ header thứ hai)
    if (aHeaderLine === bHeaderLine) return `${aTxt}\n${bBody}`;

    // Tạo danh sách cột (split đơn giản cho header; header hiếm khi có dấu phẩy trong chuỗi)
    const splitHeader = (line: string) =>
        line
            .split(",")
            .map((h) => h.trim())
            .filter(Boolean);

    const aCols = splitHeader(aHeaderLine);
    const bCols = splitHeader(bHeaderLine);

    // Hiệp nhất cột, ưu tiên thứ tự của a rồi thêm cột lạ từ b
    const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");
    const aNorm = aCols.map(norm);
    const union = [...aCols];
    for (const c of bCols) {
        if (!aNorm.includes(norm(c))) union.push(c);
    }

    // Helper để parse dòng CSV đơn (cơ bản, xử lý quotes đơn giản)
    const parseLine = (line: string) => {
        const out: string[] = [];
        let field = "";
        let inQuotes = false;
        for (let i = 0; i < line.length; i++) {
            const ch = line[i];
            if (inQuotes) {
                if (ch === '"') {
                    if (line[i + 1] === '"') {
                        field += '"';
                        i++;
                    } else {
                        inQuotes = false;
                    }
                } else {
                    field += ch;
                }
            } else {
                if (ch === '"') {
                    inQuotes = true;
                } else if (ch === ",") {
                    out.push(field);
                    field = "";
                } else {
                    field += ch;
                }
            }
        }
        out.push(field);
        return out.map((v) => v.trim());
    };

    const renderLine = (fields: string[]) =>
        fields
            .map((f) =>
                f.includes(",") || f.includes('"')
                    ? `"${f.replace(/"/g, '""')}"`
                    : f,
            )
            .join(",");

    // Map body rows của mỗi file thành mảng theo union header
    const mapBody = (body: string, cols: string[]) => {
        const lines = body.split(/\r?\n/).filter((l) => l.trim() !== "");
        const mapped: string[] = [];
        for (const line of lines) {
            // Nếu dòng là header lạ (ví dụ headerB nếu không bị loại đi), bỏ qua
            const p = parseLine(line);
            // Nếu p.length === cols.length và p matches header text, skip
            const maybeHeader = p.map((v) => v.toLowerCase()).join(",");
            if (maybeHeader === cols.map((c) => c.toLowerCase()).join(","))
                continue;

            // Map fields by position (cols order)
            const rowFields: Record<string, string> = {};
            for (let i = 0; i < cols.length; i++) {
                rowFields[cols[i]] = p[i] ?? "";
            }
            // Build array in union order, pulling from rowFields (if missing, empty)
            const outRow = union.map((uc) => {
                // if this file doesn't have uc, try to find a matching column name by normalized form
                if (uc in rowFields) return rowFields[uc];
                const matched = cols.find((c) => norm(c) === norm(uc));
                return matched ? (rowFields[matched] ?? "") : "";
            });
            mapped.push(renderLine(outRow));
        }
        return mapped;
    };

    const mappedA = mapBody(aBody, aCols);
    const mappedB = mapBody(bBody, bCols);

    return `${union.join(",")}\n${[...mappedA, ...mappedB].join("\n")}`;
}

export function analyzeCsv(text: string): ParsedDataset {
    const { headers, rows } = parseCsv(text);

    const col = {
        sid: findCol(headers, ["sid", "studentid", "student_id", "mssv"]),
        name: findCol(headers, [
            "studentname",
            "student_name",
            "name",
            "hoten",
            "fullname",
        ]),
        courseId: findCol(headers, ["courseid", "course_id"]),
        courseName: findCol(headers, ["coursename", "course_name", "course"]),
        testType: findCol(headers, ["testtype", "test_type", "examtype"]),
        email: findCol(headers, ["email"]),
        lastNotifiedTimestamp: findCol(headers, [
            "lastnotifiedtimestamp",
            "last_notified_timestamp",
            "lastsendemail",
            "last_send_email",
        ]),
        lastNotifiedSatisfaction: findCol(headers, [
            "lastnotifiedsatisfaction",
            "last_notified_satisfaction",
        ]),
        score: findCol(headers, ["score", "diem"]),
        timestamp: findCol(headers, ["timestamp", "time"]),
        academicYear: findCol(headers, [
            "academicyear",
            "academic_year",
            "year",
        ]),
        semester: findCol(headers, ["semester", "hocky"]),
    };

    // sid + score are the bare minimum to produce anything useful.
    if (!col.sid || !col.score) {
        return emptyDataset(headers);
    }

    type Accum = {
        id: string;
        name: string;
        email: string;
        academicYear: number;
        lastContactedAt: number | null;
        lastNotifiedSatisfaction: number;
        tests: TestRow[];
    };
    const byId = new Map<string, Accum>();
    let totalTests = 0;
    let scoreSum = 0;

    for (const r of rows) {
        const sid = r[col.sid]?.trim();
        if (!sid) continue;

        const score = toNumber(r[col.score]);
        const hasScore = score !== undefined;

        // Parse other metadata even when score is absent (so SIS-only rows can
        // supply name/email/last contact info).
        const name = (col.name && r[col.name]) || sid;
        const email = (col.email && r[col.email]) || "";
        const lastContactedAt = col.lastNotifiedTimestamp
            ? parseLastNotified(r[col.lastNotifiedTimestamp])
            : null;
        const lastNotifiedSatisfaction =
            (col.lastNotifiedSatisfaction
                ? toNumber(r[col.lastNotifiedSatisfaction])
                : undefined) ?? 0;
        const academicYear =
            (col.academicYear ? toNumber(r[col.academicYear]) : undefined) ?? 0;
        const semester =
            (col.semester ? toNumber(r[col.semester]) : undefined) ?? 0;
        const timestamp =
            (col.timestamp ? toNumber(r[col.timestamp]) : undefined) ?? 0;

        // Build test only if we have a valid score.
        let test: TestRow | null = null;
        if (hasScore) {
            totalTests++;
            scoreSum += score!;
            test = {
                courseId: (col.courseId && r[col.courseId]) || "",
                courseName: (col.courseName && r[col.courseName]) || "",
                testType: normalizeTestType(
                    col.testType ? r[col.testType] : undefined,
                ),
                score: score!,
                timestamp,
                academicYear,
                semester,
            };
        }

        const existing = byId.get(sid);
        if (existing) {
            // Always update metadata from SIS-like rows if available and more recent.
            if (name) existing.name = name;
            if (!existing.email && email) existing.email = email;
            if (
                lastContactedAt !== null &&
                (existing.lastContactedAt === null ||
                    lastContactedAt > existing.lastContactedAt)
            ) {
                existing.lastContactedAt = lastContactedAt;
                existing.lastNotifiedSatisfaction = lastNotifiedSatisfaction;
            }
            if (academicYear > existing.academicYear) {
                existing.academicYear = academicYear;
            }
            if (hasScore && test) {
                existing.tests.push(test);
            }
        } else {
            byId.set(sid, {
                id: sid,
                name,
                email,
                academicYear,
                lastContactedAt,
                lastNotifiedSatisfaction,
                tests: test ? [test] : [],
            });
        }
    }

    const students: StudentRow[] = Array.from(byId.values()).map((s) => {
        const classified = classifyStudent(s.tests);
        return {
            id: s.id,
            name: s.name,
            email: s.email,
            academicYear: s.academicYear,
            lastContactedAt: s.lastContactedAt,
            lastNotifiedSatisfaction: s.lastNotifiedSatisfaction,
            tests: s.tests,
            ...classified,
        };
    });

    let highRisk = 0;
    let mediumRisk = 0;
    let lowRisk = 0;
    const problemCounts: Record<Problem, number> = {
        failed_final: 0,
        failed_midterm: 0,
        low_average: 0,
    };
    const yearRisk: Record<string, number> = {};

    for (const s of students) {
        if (s.severity === "high") {
            highRisk++;
        } else if (s.severity === "medium") {
            mediumRisk++;
        } else {
            lowRisk++;
        }
        for (const p of s.problems) problemCounts[p]++;
        if (s.severity !== "low") {
            const key = s.academicYear > 0 ? String(s.academicYear) : "other";
            yearRisk[key] = (yearRisk[key] || 0) + 1;
        }
    }

    return {
        students,
        totalStudents: students.length,
        totalTests,
        averageScore: totalTests > 0 ? scoreSum / totalTests : 0,
        highRisk,
        mediumRisk,
        lowRisk,
        // "Email cần gửi" = số sinh viên nguy cơ cao (1 email / SV nguy cơ cao).
        draftEmails: highRisk,
        problemCounts,
        yearRisk,
        headers,
    };
}

export function reclassifyStudentsAndStats(students: StudentRow[]) {
    // Re-run classifyStudent on each student's tests (classifyStudent reads
    // the configured high-avg threshold via getConfiguredHighAvg()) and
    // produce updated students + aggregate stats.
    const updated = students.map((s) => {
        const classified = classifyStudent(s.tests);
        return {
            ...s,
            ...classified,
        };
    });

    let highRisk = 0;
    let mediumRisk = 0;
    let lowRisk = 0;
    const problemCounts: Record<Problem, number> = {
        failed_final: 0,
        failed_midterm: 0,
        low_average: 0,
    };
    const yearRisk: Record<string, number> = {};
    let totalTests = 0;
    let scoreSum = 0;

    for (const s of updated) {
        if (s.severity === "high") highRisk++;
        else if (s.severity === "medium") mediumRisk++;
        else lowRisk++;

        for (const p of s.problems)
            problemCounts[p] = (problemCounts[p] || 0) + 1;
        if (s.severity !== "low") {
            const key = s.academicYear > 0 ? String(s.academicYear) : "other";
            yearRisk[key] = (yearRisk[key] || 0) + 1;
        }

        totalTests += s.tests.length;
        scoreSum += s.tests.reduce((a, t) => a + t.score, 0);
    }

    return {
        students: updated,
        totalStudents: updated.length,
        totalTests,
        averageScore: totalTests > 0 ? scoreSum / totalTests : 0,
        highRisk,
        mediumRisk,
        lowRisk,
        draftEmails: highRisk,
        problemCounts,
        yearRisk,
    };
}

function emptyDataset(headers: string[]): ParsedDataset {
    return {
        students: [],
        totalStudents: 0,
        totalTests: 0,
        averageScore: 0,
        highRisk: 0,
        mediumRisk: 0,
        lowRisk: 0,
        draftEmails: 0,
        problemCounts: { failed_final: 0, failed_midterm: 0, low_average: 0 },
        yearRisk: {},
        headers,
    };
}

/* ----------------------------------------------------------------------- */
/*  Display helpers                                                        */
/* ----------------------------------------------------------------------- */

/**
 * Re-parses a CSV text into the canonical LMS record shape.
 */
export function csvToLMSRecords(text: string): Array<{
    activity_id?: string;
    sid: string;
    course_id: string;
    course_name: string;
    test_type: string;
    score: number;
    timestamp: string;
    academic_year: number;
    semester: number;
    week?: number;
}> {
    const { headers, rows } = parseCsv(text);

    const col = {
        activity_id: findCol(headers, ["activity_id", "activityid"]),
        sid: findCol(headers, ["sid", "studentid", "student_id", "mssv"]),
        courseId: findCol(headers, ["courseid", "course_id"]),
        courseName: findCol(headers, ["coursename", "course_name", "course"]),
        testType: findCol(headers, ["testtype", "test_type", "examtype"]),
        score: findCol(headers, ["score", "diem"]),
        timestamp: findCol(headers, ["timestamp", "time"]),
        academicYear: findCol(headers, [
            "academicyear",
            "academic_year",
            "year",
        ]),
        semester: findCol(headers, ["semester", "hocky"]),
        week: findCol(headers, ["week", "tuan"]),
    };

    if (!col.sid || !col.score) return [];

    const out: ReturnType<typeof csvToLMSRecords> = [];
    for (const r of rows) {
        const sid = r[col.sid]?.trim();
        if (!sid) continue;
        const score = toNumber(r[col.score]);
        if (score === undefined) continue;

        const ts = (col.timestamp ? toNumber(r[col.timestamp]) : undefined) ?? 0;

        out.push({
            activity_id: col.activity_id ? r[col.activity_id] : undefined,
            sid,
            course_id: (col.courseId && r[col.courseId]) || "",
            course_name: (col.courseName && r[col.courseName]) || "",
            test_type: col.testType ? r[col.testType] : "other",
            score,
            timestamp: new Date(ts * 1000).toISOString(),
            academic_year:
                (col.academicYear
                    ? toInteger(r[col.academicYear])
                    : undefined) ?? 0,
            semester:
                (col.semester ? toInteger(r[col.semester]) : undefined) ?? 0,
            week: col.week ? toInteger(r[col.week]) : undefined,
        });
    }
    return out;
}

/**
 * Re-parses a CSV text into the canonical SIS record shape.
 */
export function csvToSISRecords(text: string): Array<{
    sid: string;
    student_name: string;
    email: string;
    major?: string;
    current_risk_status?: string;
    intervention_status?: string;
    last_notified_timestamp?: string | null;
    last_notified_satisfaction?: number;
}> {
    const { headers, rows } = parseCsv(text);

    const col = {
        sid: findCol(headers, ["sid", "studentid", "student_id", "mssv"]),
        name: findCol(headers, [
            "studentname",
            "student_name",
            "name",
            "hoten",
            "fullname",
        ]),
        email: findCol(headers, ["email"]),
        major: findCol(headers, ["major", "nganh"]),
        risk: findCol(headers, ["current_risk_status", "risk_status", "risk"]),
        status: findCol(headers, ["intervention_status", "status"]),
        lastNotifiedTimestamp: findCol(headers, [
            "lastnotifiedtimestamp",
            "last_notified_timestamp",
            "lastsendemail",
            "last_send_email",
        ]),
        lastNotifiedSatisfaction: findCol(headers, [
            "lastnotifiedsatisfaction",
            "last_notified_satisfaction",
        ]),
    };

    if (!col.sid) return [];

    const out: ReturnType<typeof csvToSISRecords> = [];
    for (const r of rows) {
        const sid = r[col.sid]?.trim();
        if (!sid) continue;

        const riskStatus = col.risk ? r[col.risk] : undefined;
        let interventionStatus = col.status ? r[col.status] : undefined;

        if (
            riskStatus &&
            (riskStatus.toLowerCase() === "elevated" || riskStatus.toLowerCase() === "critical") &&
            (!interventionStatus || interventionStatus.toLowerCase() === "none")
        ) {
            interventionStatus = "new";
        }

        const lnt = col.lastNotifiedTimestamp
            ? parseLastNotified(r[col.lastNotifiedTimestamp])
            : null;

        out.push({
            sid,
            student_name: (col.name && r[col.name]) || sid,
            email: (col.email && r[col.email]) || "",
            major: col.major ? r[col.major] : undefined,
            current_risk_status: riskStatus,
            intervention_status: interventionStatus,
            last_notified_timestamp: lnt ? new Date(lnt * 1000).toISOString() : null,
            last_notified_satisfaction: col.lastNotifiedSatisfaction
                ? (toInteger(r[col.lastNotifiedSatisfaction]) ?? 0)
                : 0,
        });
    }
    return out;
}

/**
 * Re-parses a CSV text into the canonical Advisor record shape.
 */
export function csvToAdvisorRecords(text: string): Array<{
    advisor_id: string;
    name: string;
    email: string;
}> {
    const { headers, rows } = parseCsv(text);

    const col = {
        id: findCol(headers, ["advisor_id", "advisorid", "id"]),
        name: findCol(headers, ["name", "advisor_name", "hoten"]),
        email: findCol(headers, ["email"]),
    };

    if (!col.id) return [];

    const out: ReturnType<typeof csvToAdvisorRecords> = [];
    for (const r of rows) {
        const id = r[col.id]?.trim();
        if (!id) continue;

        out.push({
            advisor_id: id,
            name: (col.name && r[col.name]) || id,
            email: (col.email && r[col.email]) || "",
        });
    }
    return out;
}

/**
 * Re-parses a CSV text into arbitrary key-value pairs for custom sources.
 */
export function csvToCustomRecords(text: string): Array<Record<string, any>> {
    const { headers, rows } = parseCsv(text);
    return rows.map((r) => {
        const obj: Record<string, any> = {};
        for (const h of headers) {
            const val = r[h];
            const n = toNumber(val);
            obj[h] = n !== undefined ? n : val;
        }
        return obj;
    });
}

/** Human-readable, one-line summary of a student's risk factors. */
export function describeProblem(s: StudentRow): string {
    const parts: string[] = [];
    if (s.hasFailedFinal) parts.push("rớt cuối kỳ");
    if (s.hasFailedMidterm) parts.push("rớt giữa kỳ");
    if (
        !s.hasFailedFinal &&
        !s.hasFailedMidterm &&
        s.problems.includes("low_average")
    ) {
        parts.push(`điểm TB ${s.averageScore.toFixed(1)}`);
    }
    const head =
        parts.length > 0
            ? parts[0].charAt(0).toUpperCase() +
              parts[0].slice(1) +
              (parts.length > 1 ? `, ${parts.slice(1).join(", ")}` : "")
            : `Điểm TB ${s.averageScore.toFixed(1)}`;
    return `${head} · ${s.tests.length} bài KT`;
}
