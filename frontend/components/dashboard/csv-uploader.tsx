"use client";

import * as React from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  GraduationCap,
  BookCopy,
  Plus,
  Trash2,
  ArrowRight,
  Loader2,
  Link2,
  X,
  FileText,
  Info,
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useDataset } from "@/hooks/use-dataset";
import {
  useUploads,
  type SourceKey,
  type UploadItem,
  type UploadStatus,
} from "@/hooks/use-uploads";
import { analyzeCsv, csvToIngestRows } from "@/lib/csv";
import { ingestRows } from "@/lib/api";

const SOURCE_META: Record<
  SourceKey,
  {
    label: string;
    description: string;
    icon: typeof GraduationCap;
    iconClass: string;
    badgeClass: string;
    accentRing: string;
  }
> = {
  LMS: {
    label: "LMS",
    description: "Điểm · Bài tập",
    icon: GraduationCap,
    iconClass: "bg-primary/10 text-primary ring-1 ring-primary/20",
    badgeClass:
      "border-transparent bg-primary/10 text-primary ring-1 ring-primary/20",
    accentRing: "ring-primary/30",
  },
  SIS: {
    label: "SIS",
    description: "Học phí · Hồ sơ",
    icon: BookCopy,
    iconClass: "bg-warning/15 text-warning ring-1 ring-warning/25",
    badgeClass:
      "border-transparent bg-warning/15 text-warning ring-1 ring-warning/25",
    accentRing: "ring-warning/30",
  },
};

// Matches the fixed schema used by NexusEDU (scores 0–100).
const SAMPLE_CSV = `sid,student_name,course_id,course_name,test_type,email,last_notified_timestamp,last_notified_satisfaction,score,timestamp,academic_year,semester
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

/** A file the user has dropped/selected but not yet confirmed. */
type StagedFile = {
  file: File;
  text: string;
  sizeKB: number;
};

type StagedMap = Partial<Record<SourceKey, StagedFile>>;

/** Concatenate two CSV strings sharing the same header row. */

function mergeCsv(a: string, b: string): string {
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
    const colIndex: Record<string, number> = {};
    cols.forEach((c, i) => (colIndex[c] = i));
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

export function CsvUploader() {
  const { dataset, setDataset, clearDataset } = useDataset();
  const { uploads, addUpload, updateUpload, removeUpload } = useUploads();

  const [staged, setStaged] = React.useState<StagedMap>({});
  const [draggingOver, setDraggingOver] = React.useState<SourceKey | null>(
    null,
  );
  const [confirming, setConfirming] = React.useState(false);

  const stageFile = React.useCallback((file: File, source: SourceKey) => {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      toast.error("Vui lòng tải file .CSV");
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => {
      toast.error("Không đọc được file");
    };
    reader.onload = () => {
      const text = typeof reader.result === "string" ? reader.result : "";
      setStaged((prev) => ({
        ...prev,
        [source]: {
          file,
          text,
          sizeKB: Number((file.size / 1024).toFixed(1)),
        },
      }));
      toast.success(`Đã nạp file ${source}`, {
        description: file.name,
      });
    };
    reader.readAsText(file);
  }, []);

  const removeStaged = (source: SourceKey) => {
    setStaged((prev) => {
      const next = { ...prev };
      delete next[source];
      return next;
    });
  };

  const lmsStaged = staged.LMS;
  const sisStaged = staged.SIS;
  const bothReady = Boolean(lmsStaged && sisStaged);

  const handleConfirm = async () => {
    if (!lmsStaged || !sisStaged || confirming) return;
    setConfirming(true);

    const id = `up_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const item: UploadItem = {
      id,
      status: "processing",
      uploadedAt: new Date().toISOString(),
      files: {
        LMS: { fileName: lmsStaged.file.name, sizeKB: lmsStaged.sizeKB },
        SIS: { fileName: sisStaged.file.name, sizeKB: sisStaged.sizeKB },
      },
    };
    addUpload(item);

    // Reset zones immediately so the user can stage the next pair.
    setStaged({});

    // Small delay so the "Đang xử lý" pill is briefly visible.
    await new Promise((r) => setTimeout(r, 800));

    try {
      const merged = mergeCsv(lmsStaged.text, sisStaged.text);
      const result = analyzeCsv(merged);
      if (result.totalStudents === 0) {
        updateUpload(id, {
          status: "error",
          errorMessage:
            "Bộ dữ liệu không có dòng hợp lệ (thiếu cột sid hoặc score).",
        });
        toast.error("Bộ dữ liệu không có dữ liệu hợp lệ");
        setConfirming(false);
        return;
      }
      updateUpload(id, {
        status: "ready",
        totalStudents: result.totalStudents,
        totalTests: result.totalTests,
        highRisk: result.highRisk,
      });
      setDataset({
        fileName: `${lmsStaged.file.name} + ${sisStaged.file.name}`,
        sizeKB: lmsStaged.sizeKB + sisStaged.sizeKB,
        uploadedAt: new Date().toISOString(),
        totalStudents: result.totalStudents,
        totalTests: result.totalTests,
        averageScore: result.averageScore,
        highRisk: result.highRisk,
        mediumRisk: result.mediumRisk,
        lowRisk: result.lowRisk,
        draftEmails: result.draftEmails,
        problemCounts: result.problemCounts,
        yearRisk: result.yearRisk,
        students: result.students,
        headers: result.headers,
      });
      toast.success("Đã phân tích xong bộ hồ sơ", {
        description: `${result.totalStudents.toLocaleString(
          "vi-VN",
        )} sinh viên · ${result.highRisk.toLocaleString("vi-VN")} nguy cơ cao.`,
      });

      // Fire-and-forget: push the raw rows to the backend so /alerts can
      // re-derive the authoritative status server-side. Local UI is already
      // hydrated, so failure here only logs a warning.
      const ingestPayload = csvToIngestRows(merged);
      if (ingestPayload.length > 0) {
        ingestRows(ingestPayload)
          .then(() => {
            toast.message("Đã đồng bộ với máy chủ", {
              description: `${ingestPayload.length.toLocaleString(
                "vi-VN",
              )} dòng dữ liệu đã đẩy lên backend.`,
            });
          })
          .catch((err) => {
            console.warn(
              "[v0] /data/ingest failed, dataset stays local-only",
              err,
            );
            toast.warning("Chưa đồng bộ được với máy chủ", {
              description:
                "Dữ liệu vẫn hoạt động trong phiên này. Có thể thử lại sau.",
            });
          });
      }
    } catch (err) {
      console.error("[v0] CSV analyze failed", err);
      updateUpload(id, {
        status: "error",
        errorMessage: "Không thể phân tích bộ hồ sơ. Hãy kiểm tra định dạng.",
      });
      toast.error("Phân tích thất bại");
    } finally {
      setConfirming(false);
    }
  };

  const handleDelete = (item: UploadItem) => {
    removeUpload(item.id);
    if (
      dataset &&
      dataset.fileName ===
        `${item.files.LMS.fileName} + ${item.files.SIS.fileName}`
    ) {
      clearDataset();
    }
    toast.message("Đã xóa khỏi danh sách", {
      description: `${item.files.LMS.fileName} + ${item.files.SIS.fileName}`,
    });
  };

  const useSampleForBoth = () => {
    const lmsFile = new File([SAMPLE_CSV], "nexusedu-lms-sample.csv", {
      type: "text/csv",
    });
    const sisFile = new File([SAMPLE_CSV], "nexusedu-sis-sample.csv", {
      type: "text/csv",
    });
    stageFile(lmsFile, "LMS");
    stageFile(sisFile, "SIS");
  };

  const ordered = React.useMemo(() => [...uploads].reverse(), [uploads]);

  return (
    <div className="flex flex-col gap-6">
      <div
        aria-hidden
        className="h-px w-full bg-gradient-to-r from-accent-sky/40 via-primary/25 to-transparent"
      />

      {/* Paired LMS + SIS upload */}
      <Card className="stripe-sky rounded-2xl border-accent-sky/15 bg-gradient-to-br from-accent-sky/22 via-accent-sky/10 to-card">
        <CardContent className="p-4 md:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <UploadCloud className="size-4 text-primary" />
              <p className="text-sm font-semibold">LMS + SIS</p>
            </div>
            <button
              type="button"
              onClick={useSampleForBoth}
              className="text-xs font-medium text-primary hover:underline"
            >
              Dữ liệu mẫu
            </button>
          </div>

          {/* Two parallel dropzones with a chained link icon between them */}
          <div className="grid items-stretch gap-3 md:grid-cols-[1fr_auto_1fr]">
            <Dropzone
              source="LMS"
              staged={lmsStaged}
              dragging={draggingOver === "LMS"}
              onDragEnter={() => setDraggingOver("LMS")}
              onDragLeave={() => setDraggingOver(null)}
              onFile={(f) => stageFile(f, "LMS")}
              onClear={() => removeStaged("LMS")}
              disabled={confirming}
            />

            {/* Chain link visual between the two zones */}
            <div className="relative flex items-center justify-center md:px-1">
              <div
                aria-hidden
                className="absolute inset-x-0 top-1/2 hidden h-px -translate-y-1/2 bg-gradient-to-r from-primary/30 via-border to-warning/30 md:block"
              />
              <div
                className={cn(
                  "relative grid size-9 place-items-center rounded-full border bg-card transition-colors",
                  bothReady
                    ? "border-primary/60 text-primary ring-2 ring-primary/20"
                    : "border-border/60 text-muted-foreground",
                )}
                aria-label="LMS và SIS phải đi cùng nhau"
              >
                <Link2 className="size-4" />
              </div>
            </div>

            <Dropzone
              source="SIS"
              staged={sisStaged}
              dragging={draggingOver === "SIS"}
              onDragEnter={() => setDraggingOver("SIS")}
              onDragLeave={() => setDraggingOver(null)}
              onFile={(f) => stageFile(f, "SIS")}
              onClear={() => removeStaged("SIS")}
              disabled={confirming}
            />
          </div>

          {/* Hint + Confirm row */}
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <HintLine staged={staged} />
            <Button
              type="button"
              size="sm"
              onClick={handleConfirm}
              disabled={!bothReady || confirming}
              className={cn(
                "rounded-xl gap-1.5 transition-all",
                bothReady && !confirming
                  ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20 hover:bg-primary/90"
                  : "",
              )}
              aria-label="Xác nhận bộ hồ sơ"
            >
              {confirming ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Plus className="size-4" />
              )}
              Xác nhận bộ hồ sơ
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* File registry */}
      <Card className="stripe-cyan rounded-2xl border-accent-cyan/15 bg-gradient-to-br from-accent-cyan/22 via-accent-cyan/10 to-card">
        <CardContent className="p-0">
          <header className="flex items-center justify-between gap-3 border-b border-border/60 px-4 py-3 md:px-5">
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="size-4 text-muted-foreground" />
              <p className="text-sm font-semibold">Lịch sử</p>
            </div>
            {uploads.length > 0 && (
              <div className="flex items-center gap-2 text-xs">
                <Badge variant="outline" className="rounded-md font-mono">
                  {uploads.length}
                </Badge>
                <Badge
                  variant="secondary"
                  className="rounded-md bg-success/10 font-mono text-success hover:bg-success/10"
                >
                  <CheckCircle2 className="size-3" />
                  {uploads.filter((u) => u.status === "ready").length}
                </Badge>
              </div>
            )}
          </header>

          {uploads.length === 0 ? (
            <div className="px-4 py-8 text-center md:px-6">
              <div className="mx-auto grid size-10 place-items-center rounded-xl bg-muted text-muted-foreground">
                <FileSpreadsheet className="size-4" />
              </div>
            </div>
          ) : (
            <ul className="divide-y divide-border/60">
              {ordered.map((item) => (
                <UploadRow
                  key={item.id}
                  item={item}
                  onDelete={() => handleDelete(item)}
                />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Dropzone({
  source,
  staged,
  dragging,
  onDragEnter,
  onDragLeave,
  onFile,
  onClear,
  disabled,
}: {
  source: SourceKey;
  staged: StagedFile | undefined;
  dragging: boolean;
  onDragEnter: () => void;
  onDragLeave: () => void;
  onFile: (file: File) => void;
  onClear: () => void;
  disabled?: boolean;
}) {
  const meta = SOURCE_META[source];
  const Icon = meta.icon;
  const inputRef = React.useRef<HTMLInputElement>(null);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        onDragEnter();
      }}
      onDragLeave={onDragLeave}
      onDrop={(e) => {
        e.preventDefault();
        onDragLeave();
        const f = e.dataTransfer.files?.[0];
        if (f) onFile(f);
      }}
      className={cn(
        "relative flex min-h-[148px] flex-col rounded-2xl border-2 border-dashed p-4 transition-colors",
        staged
          ? "border-solid border-border/70 bg-card"
          : dragging
            ? `border-primary bg-primary/5 ring-2 ${meta.accentRing}`
            : "border-border/70 bg-muted/30 hover:bg-muted/50",
        disabled && "pointer-events-none opacity-60",
      )}
      aria-label={`Vùng tải lên ${source}`}
    >
      {/* Header strip with the source label always visible */}
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "grid size-9 shrink-0 place-items-center rounded-lg",
              meta.iconClass,
            )}
          >
            <Icon className="size-4" />
          </span>
          <div className="min-w-0">
            <p className="flex items-center gap-1.5 text-sm font-semibold">
              {source}
              <Badge
                variant="outline"
                className={cn(
                  "rounded-md px-1.5 py-0 text-[10px] font-semibold",
                  meta.badgeClass,
                )}
              >
                Bắt buộc
              </Badge>
            </p>
            <p className="truncate text-[11px] text-muted-foreground">
              {meta.description}
            </p>
          </div>
        </div>
      </div>

      {staged ? (
        <div className="flex flex-1 items-center gap-3 rounded-xl border border-border/70 bg-muted/40 p-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-card text-muted-foreground ring-1 ring-border/60">
            <FileText className="size-4" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] font-medium">
              {staged.file.name}
            </p>
            <p className="text-[11px] text-muted-foreground">
              {staged.sizeKB.toFixed(1)} KB · đã sẵn sàng
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-8 shrink-0 rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
            onClick={onClear}
            aria-label={`Bỏ file ${source}`}
          >
            <X className="size-4" />
          </Button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex flex-1 flex-col items-center justify-center gap-1.5 rounded-xl text-center text-muted-foreground transition-colors hover:text-foreground"
        >
          <UploadCloud className="size-6" />
          <p className="text-[13px] font-medium">
            <span className="text-primary">Chọn file</span>
          </p>
          <p className="text-[11px] text-muted-foreground">.csv</p>
        </button>
      )}

      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        className="sr-only"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          e.currentTarget.value = "";
        }}
      />
    </div>
  );
}

function HintLine({ staged }: { staged: StagedMap }) {
  const lms = Boolean(staged.LMS);
  const sis = Boolean(staged.SIS);

  if (lms && sis) {
    return (
      <p className="flex items-center gap-1.5 text-xs font-medium text-success">
        <CheckCircle2 className="size-3.5" />
        Sẵn sàng
      </p>
    );
  }
  if (!lms && !sis) {
    return (
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Info className="size-3.5" />
        Cần LMS + SIS
      </p>
    );
  }
  const missing: SourceKey = lms ? "SIS" : "LMS";
  return (
    <p className="flex items-center gap-1.5 text-xs text-warning">
      <Info className="size-3.5" />
      Thiếu
      <Badge
        variant="outline"
        className={cn(
          "rounded-md px-1.5 py-0 text-[10.5px] font-semibold",
          SOURCE_META[missing].badgeClass,
        )}
      >
        {missing}
      </Badge>
    </p>
  );
}

function UploadRow({
  item,
  onDelete,
}: {
  item: UploadItem;
  onDelete: () => void;
}) {
  const lms = item.files.LMS;
  const sis = item.files.SIS;
  return (
    <li className="flex flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:px-5">
      <div className="flex min-w-0 flex-1 flex-col gap-2 md:flex-row md:items-center md:gap-4">
        <SourceFilePill source="LMS" file={lms} />
        <Link2
          aria-hidden
          className="hidden size-3.5 shrink-0 text-muted-foreground md:block"
        />
        <SourceFilePill source="SIS" file={sis} />
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-2 self-end md:self-center">
        <p className="text-[11px] text-muted-foreground">
          {new Date(item.uploadedAt).toLocaleString("vi-VN", {
            hour12: false,
          })}
          {item.status === "ready" && item.totalStudents
            ? ` · ${item.totalStudents.toLocaleString("vi-VN")} SV · ${
                item.highRisk ?? 0
              } nguy cơ cao`
            : null}
          {item.status === "error" && item.errorMessage
            ? ` · ${item.errorMessage}`
            : null}
        </p>
        <StatusBadge status={item.status} />
        {item.status === "ready" ? (
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="rounded-lg text-xs"
          >
            <a href="/dashboard/alerts">
              Tới Trung tâm cảnh báo
              <ArrowRight className="size-3.5" />
            </a>
          </Button>
        ) : null}
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-8 rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
          onClick={onDelete}
          aria-label="Xóa bộ hồ sơ"
        >
          <Trash2 className="size-4" />
        </Button>
      </div>
    </li>
  );
}

function SourceFilePill({
  source,
  file,
}: {
  source: SourceKey;
  file: { fileName: string; sizeKB: number };
}) {
  const meta = SOURCE_META[source];
  const Icon = meta.icon;
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <span
        className={cn(
          "grid size-9 shrink-0 place-items-center rounded-xl",
          meta.iconClass,
        )}
      >
        <Icon className="size-4" />
      </span>
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <Badge
            variant="outline"
            className={cn(
              "shrink-0 rounded-md px-1.5 py-0 text-[10.5px] font-semibold",
              meta.badgeClass,
            )}
          >
            {source}
          </Badge>
          <p className="truncate text-[13px] font-medium">{file.fileName}</p>
        </div>
        <p className="text-[11px] text-muted-foreground">
          {file.sizeKB.toFixed(1)} KB
        </p>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: UploadStatus }) {
  if (status === "processing") {
    return (
      <Badge className="gap-1 rounded-md border-transparent bg-warning/15 px-1.5 py-0.5 text-[10.5px] font-medium text-warning ring-1 ring-warning/25 hover:bg-warning/15">
        <Loader2 className="size-3 animate-spin" />
        Đang xử lý
      </Badge>
    );
  }
  if (status === "ready") {
    return (
      <Badge className="gap-1 rounded-md border-transparent bg-success/15 px-1.5 py-0.5 text-[10.5px] font-medium text-success ring-1 ring-success/25 hover:bg-success/15">
        <CheckCircle2 className="size-3" />
        Sẵn sàng
      </Badge>
    );
  }
  return (
    <Badge
      variant="destructive"
      className="gap-1 rounded-md px-1.5 py-0.5 text-[10.5px]"
    >
      <AlertCircle className="size-3" />
      Lỗi
    </Badge>
  );
}
