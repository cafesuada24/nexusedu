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

// Matches the fixed schema used by NexusEDU (scores 0–100).
export const SAMPLE_CSV = `sid,student_name,course_id,course_name,test_type,email,last_notified_timestamp,last_notified_satisfaction,score,timestamp,academic_year,semester
550e8400-e29b-41d4-a716-446655440000,Nguyen Van An,a1b2c3d4,Machine Learning,middle_semester,an.nv21@student.edu.vn,0,0,45.0,1776844800,3,2
550e8400-e29b-41d4-a716-446655440000,Nguyen Van An,a1b2c3d4,Machine Learning,final_semester,an.nv21@student.edu.vn,0,0,38.0,1776931200,3,2
661f9511-f30c-52e5-b827-557766551111,Tran Thi Binh,a1b2c3d4,Machine Learning,middle_semester,binh.tt21@student.edu.vn,1776240000,1,85.0,1776844800,3,2
661f9511-f30c-52e5-b827-557766551111,Tran Thi Binh,a1b2c3d4,Machine Learning,final_semester,binh.tt21@student.edu.vn,1776240000,1,88.0,1776931200,3,2
772e0622-041d-43f6-8938-668877662222,Le Hoang Nam,b2c3d4e5,Deep Learning,middle_semester,nam.lh22@student.edu.vn,0,0,30.0,1776852000,4,1
772e0622-041d-43f6-8938-668877662222,Le Hoang Nam,b2c3d4e5,Deep Learning,final_semester,nam.lh22@student.edu.vn,0,0,42.0,1776938400,4,1
883e1733-152e-44e7-9049-779988773333,Pham Minh Duc,b2c3d4e5,Deep Learning,final_semester,duc.pm22@student.edu.vn,1775808000,1,90.0,1776855600,4,1
994e2844-263f-45f8-a150-880099884444,Vo Hoang Yen,c3d4e5f6,Computer Vision,middle_semester,yen.vh23@student.edu.vn,0,0,25.0,1776859200,2,2
994e2844-263f-45f8-a150-880099884444,Vo Hoang Yen,c3d4e5f6,Computer Vision,final_semester,yen.vh23@student.edu.vn,0,0,48.0,1776945600,2,2
aa5e3955-374f-46f9-b261-991100995555,Dang Thu Thao,c3d4e5f6,Computer Vision,final_semester,thao.dt23@student.edu.vn,1775635200,0,72.0,1776862800,2,2
bb6e4066-485f-470a-b372-002211006666,Bui Gia Bao,d4e5f6f7,Linear Algebra,middle_semester,bao.bg24@student.edu.vn,1775462400,1,58.0,1776866400,1,1
bb6e4066-485f-470a-b372-002211006666,Bui Gia Bao,d4e5f6f7,Linear Algebra,final_semester,bao.bg24@student.edu.vn,1775462400,1,62.0,1776952800,1,1
cc7e5177-586f-481b-b483-113322117777,Ho Sy Minh Ha,d4e5f6f7,Linear Algebra,middle_semester,ha.hsm24@student.edu.vn,0,0,95.0,1776870000,1,1
dd8e6288-697f-492c-b594-224433228888,Nguyen Thi Huong,e5f6f7f8,Data Structures,final_semester,huong.nt@student.edu.vn,0,0,40.0,1776873600,2,1
ee9e7399-708f-4a3d-b605-335544339999,Phan Van Khai,e5f6f7f8,Data Structures,middle_semester,khai.pv@student.edu.vn,1775289600,1,60.0,1776877200,2,1
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
        f.includes(",") || f.includes('"') ? `"${f.replace(/"/g, '""')}"` : f,
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
      if (maybeHeader === cols.map((c) => c.toLowerCase()).join(",")) continue;

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
 * Re-parses a CSV text into the canonical LMS record shape.
 */
export function csvToLMSRecords(text: string): Array<{
  activity_id?: string;
  sid: string;
  course_id: string;
  course_name: string;
  test_type: string;
  score: number;
  timestamp: number;
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
    academicYear: findCol(headers, ["academicyear", "academic_year", "year"]),
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

    out.push({
      activity_id: col.activity_id ? r[col.activity_id] : undefined,
      sid,
      course_id: (col.courseId && r[col.courseId]) || "",
      course_name: (col.courseName && r[col.courseName]) || "",
      test_type: col.testType ? r[col.testType] : "other",
      score,
      timestamp: (col.timestamp ? toNumber(r[col.timestamp]) : undefined) ?? 0,
      academic_year:
        (col.academicYear ? toInteger(r[col.academicYear]) : undefined) ?? 0,
      semester: (col.semester ? toInteger(r[col.semester]) : undefined) ?? 0,
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
  last_notified_timestamp?: number;
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

    out.push({
      sid,
      student_name: (col.name && r[col.name]) || sid,
      email: (col.email && r[col.email]) || "",
      major: col.major ? r[col.major] : undefined,
      current_risk_status: col.risk ? r[col.risk] : undefined,
      intervention_status: col.status ? r[col.status] : undefined,
      last_notified_timestamp: col.lastNotifiedTimestamp
        ? parseLastNotified(r[col.lastNotifiedTimestamp]) ?? 0
        : 0,
      last_notified_satisfaction: col.lastNotifiedSatisfaction
        ? toInteger(r[col.lastNotifiedSatisfaction]) ?? 0
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
