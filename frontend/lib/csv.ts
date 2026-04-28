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
    if (typeof parsed === "number" && Number.isFinite(parsed)) return parsed;
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
    academicYear: findCol(headers, ["academicyear", "academic_year", "year"]),
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
        testType: normalizeTestType(col.testType ? r[col.testType] : undefined),
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

    for (const p of s.problems) problemCounts[p] = (problemCounts[p] || 0) + 1;
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
 * Re-parses a (possibly merged) CSV text into the canonical row shape that
 * the backend `POST /data/ingest` endpoint expects. Unknown columns are
 * preserved as best-effort numeric/string fields. Rows missing `sid` or
 * `score` are dropped.
 */
export function csvToIngestRows(text: string): Array<{
  sid: string;
  student_name: string;
  course_id: string;
  course_name: string;
  test_type: string;
  email: string;
  last_notified_timestamp: number;
  last_notified_satisfaction: number;
  score: number;
  timestamp: number;
  academic_year: number;
  semester: number;
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
    academicYear: findCol(headers, ["academicyear", "academic_year", "year"]),
    semester: findCol(headers, ["semester", "hocky"]),
  };

  if (!col.sid || !col.score) return [];

  const out: ReturnType<typeof csvToIngestRows> = [];
  for (const r of rows) {
    const sid = r[col.sid]?.trim();
    if (!sid) continue;
    const score = toNumber(r[col.score]);
    if (score === undefined) continue;

    const lastNotified = col.lastNotifiedTimestamp
      ? parseLastNotified(r[col.lastNotifiedTimestamp])
      : null;

    out.push({
      sid,
      student_name: (col.name && r[col.name]) || sid,
      course_id: (col.courseId && r[col.courseId]) || "",
      course_name: (col.courseName && r[col.courseName]) || "",
      test_type: col.testType ? normalizeTestType(r[col.testType]) : "other",
      email: (col.email && r[col.email]) || "",
      last_notified_timestamp: lastNotified ?? 0,
      last_notified_satisfaction:
        (col.lastNotifiedSatisfaction
          ? toNumber(r[col.lastNotifiedSatisfaction])
          : undefined) ?? 0,
      score,
      timestamp: (col.timestamp ? toNumber(r[col.timestamp]) : undefined) ?? 0,
      academic_year:
        (col.academicYear ? toNumber(r[col.academicYear]) : undefined) ?? 0,
      semester: (col.semester ? toNumber(r[col.semester]) : undefined) ?? 0,
    });
  }
  return out;
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
