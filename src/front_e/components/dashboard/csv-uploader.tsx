"use client";

import * as React from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  Sparkles,
  ShieldCheck,
  Rows3,
  X,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { cn } from "@/lib/utils";
import { useDataset } from "@/hooks/use-dataset";
import { analyzeCsv, type ParsedDataset } from "@/lib/csv";

type Stage = "idle" | "uploading" | "analyzing" | "done" | "error";

// Matches the fixed schema used by NexusEDU.
const SAMPLE_CSV = `sid,student_name,course_id,course_name,test_type,email,last_send_email,score,timestamp,academic_year,semester
550e8400-e29b-41d4-a716-446655440000,Nguyen Van An,a1b2c3d4,Machine Learning,middle_semester,an.nv21@student.edu.vn,None,4.5,1776844800,3,2
661f9511-f30c-52e5-b827-557766551111,Tran Thi Binh,a1b2c3d4,Machine Learning,middle_semester,binh.tt21@student.edu.vn,2026-04-10 08:30:00,8.5,1776844800,3,2
772g0622-g41d-63f6-c938-668877662222,Le Hoang Nam,b2c3d4e5,Deep Learning,middle_semester,nam.lh22@student.edu.vn,None,3.0,1776852000,4,1
883h1733-h52e-74g7-d049-779988773333,Pham Minh Duc,b2c3d4e5,Deep Learning,final_semester,duc.pm22@student.edu.vn,2026-03-20 14:00:00,9.0,1776855600,4,1
994i2844-i63f-85h8-e150-880099884444,Vo Hoang Yen,c3d4e5f6,Computer Vision,middle_semester,yen.vh23@student.edu.vn,None,2.5,1776859200,2,2
aa5j3955-j74g-96i9-f261-991100995555,Dang Thu Thao,c3d4e5f6,Computer Vision,final_semester,thao.dt23@student.edu.vn,None,7.5,1776862800,2,2
bb6k4066-k85h-07j0-a372-002211006666,Bui Gia Bao,d4e5f6g7,Linear Algebra,middle_semester,bao.bg24@student.edu.vn,2026-04-15 09:15:00,5.5,1776866400,1,1
cc7l5177-l96i-18k1-b483-113322117777,Ho Sy Minh Ha,d4e5f6g7,Linear Algebra,middle_semester,ha.hsm24@student.edu.vn,None,9.5,1776870000,1,1
dd8m6288-m07j-29l2-c594-224433228888,Nguyen Thi Huong,e5f6g7h8,Data Structures,final_semester,huong.nt@student.edu.vn,None,4.0,1776873600,2,1
ee9n7399-n18k-30m3-d605-335544339999,Phan Van Khai,e5f6g7h8,Data Structures,middle_semester,khai.pv@student.edu.vn,2026-04-01 10:00:00,6.0,1776877200,2,1
`;

export function CsvUploader() {
  const { dataset, setDataset, clearDataset } = useDataset();
  const [stage, setStage] = React.useState<Stage>("idle");
  const [fileName, setFileName] = React.useState<string | null>(null);
  const [fileSizeKB, setFileSizeKB] = React.useState<number>(0);
  const [progress, setProgress] = React.useState(0);
  const [dragging, setDragging] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [parsed, setParsed] = React.useState<ParsedDataset | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Restore the "done" view when a dataset already exists (e.g. after
  // navigating away and coming back to the Import page).
  React.useEffect(() => {
    if (dataset && stage === "idle") {
      setStage("done");
      setFileName(dataset.fileName ?? null);
      setFileSizeKB(dataset.sizeKB ?? 0);
      setParsed({
        students: dataset.students ?? [],
        totalStudents: dataset.totalStudents ?? 0,
        totalTests: dataset.totalTests ?? 0,
        averageScore: dataset.averageScore ?? 0,
        highRisk: dataset.highRisk ?? 0,
        mediumRisk: dataset.mediumRisk ?? 0,
        lowRisk: dataset.lowRisk ?? 0,
        draftEmails: dataset.draftEmails ?? 0,
        problemCounts: dataset.problemCounts ?? {
          failed_final: 0,
          failed_midterm: 0,
          low_average: 0,
        },
        yearRisk: dataset.yearRisk ?? {},
        headers: dataset.headers ?? [],
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset]);

  const reset = () => {
    setStage("idle");
    setFileName(null);
    setFileSizeKB(0);
    setProgress(0);
    setErrorMessage(null);
    setParsed(null);
    clearDataset();
  };

  const finishWithText = React.useCallback(
    (text: string, meta: { fileName: string; sizeKB: number }) => {
      try {
        const result = analyzeCsv(text);
        if (result.totalStudents === 0) {
          setErrorMessage(
            "Không đọc được dòng dữ liệu nào. Hãy kiểm tra lại header (cần có cột sid và score) và nội dung file.",
          );
          setStage("error");
          toast.error("File CSV không có dữ liệu hợp lệ");
          return;
        }

        setParsed(result);
        setStage("done");
        setDataset({
          fileName: meta.fileName,
          sizeKB: meta.sizeKB,
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
        toast.success(
          `Phân tích hoàn tất — phát hiện ${result.highRisk} sinh viên nguy cơ cao`,
          {
            description: `${result.totalStudents.toLocaleString("vi-VN")} sinh viên · ${result.totalTests.toLocaleString("vi-VN")} bài kiểm tra.`,
          },
        );
      } catch (err) {
        console.error("[v0] CSV analyze failed", err);
        setErrorMessage(
          "Không thể phân tích file này. Hãy đảm bảo đúng định dạng CSV.",
        );
        setStage("error");
        toast.error("Phân tích thất bại");
      }
    },
    [setDataset],
  );

  const handleFile = (f: File) => {
    if (!f.name.toLowerCase().endsWith(".csv")) {
      toast.error("Vui lòng tải file .CSV");
      return;
    }
    setErrorMessage(null);
    setFileName(f.name);
    const sizeKB = Number((f.size / 1024).toFixed(1));
    setFileSizeKB(sizeKB);
    setStage("uploading");
    setProgress(0);

    const reader = new FileReader();
    reader.onerror = () => {
      setErrorMessage("Không đọc được file. Vui lòng thử lại.");
      setStage("error");
    };
    reader.onload = () => {
      const text = typeof reader.result === "string" ? reader.result : "";

      // Give the UI a short, visible "upload + analyze" beat so the
      // transition doesn't feel instantaneous.
      const tick = setInterval(() => {
        setProgress((p) => {
          if (p >= 100) {
            clearInterval(tick);
            setStage("analyzing");
            setTimeout(() => {
              finishWithText(text, { fileName: f.name, sizeKB });
            }, 600);
            return 100;
          }
          return p + 12;
        });
      }, 80);
    };
    reader.readAsText(f);
  };

  const loadSample = () => {
    const blob = new Blob([SAMPLE_CSV], { type: "text/csv" });
    const file = new File([blob], "nexusedu-sample.csv", { type: "text/csv" });
    handleFile(file);
  };

  if (stage === "idle") {
    return (
      <Card className="rounded-2xl border-border/60">
        <CardContent className="p-0">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              const f = e.dataTransfer.files?.[0];
              if (f) handleFile(f);
            }}
            className={cn(
              "relative overflow-hidden rounded-2xl border-2 border-dashed p-8 transition-colors md:p-12",
              dragging
                ? "border-primary bg-primary/5"
                : "border-border/70 bg-muted/30",
            )}
          >
            <Empty className="border-0 bg-transparent">
              <EmptyHeader>
                <EmptyMedia
                  variant="icon"
                  className="bg-primary/10 text-primary"
                >
                  <UploadCloud className="size-7" />
                </EmptyMedia>
                <EmptyTitle className="font-serif text-xl">
                  Kéo thả file CSV vào đây
                </EmptyTitle>
                <EmptyDescription className="max-w-md">
                  Hỗ trợ file CSV theo schema NexusEDU:{" "}
                  <span className="font-mono text-xs">
                    sid, student_name, course_name, test_type, score,
                    last_send_email, academic_year, semester…
                  </span>
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="sr-only"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleFile(f);
                  }}
                />
                <Button
                  size="lg"
                  className="rounded-xl"
                  onClick={() => inputRef.current?.click()}
                >
                  <UploadCloud className="size-4" />
                  Tải lên danh sách điểm (.CSV)
                </Button>
                <p className="text-xs text-muted-foreground">
                  Hoặc dùng{" "}
                  <button
                    className="font-medium text-primary hover:underline"
                    onClick={loadSample}
                  >
                    mẫu CSV của chúng tôi
                  </button>
                </p>
              </EmptyContent>
            </Empty>
          </div>

          <div className="grid gap-4 border-t border-border/60 p-6 md:grid-cols-3 md:p-8">
            <Tip
              icon={<ShieldCheck className="size-4" />}
              title="Bảo mật"
              desc="Mã hoá end-to-end. Dữ liệu không rời khỏi máy chủ trường."
            />
            <Tip
              icon={<Rows3 className="size-4" />}
              title="Schema cố định"
              desc="Nhận dạng sid, student_name, score, test_type, last_send_email."
            />
            <Tip
              icon={<Sparkles className="size-4" />}
              title="Phân tích AI"
              desc="Gom điểm theo sinh viên, phát hiện rớt môn chỉ trong vài giây."
            />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="rounded-2xl border-border/60">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span
              className={cn(
                "grid size-11 place-items-center rounded-xl",
                stage === "error"
                  ? "bg-destructive/10 text-destructive"
                  : "bg-primary/10 text-primary",
              )}
            >
              {stage === "error" ? (
                <AlertCircle className="size-5" />
              ) : (
                <FileSpreadsheet className="size-5" />
              )}
            </span>
            <div>
              <CardTitle className="font-serif">
                {fileName ?? "students.csv"}
              </CardTitle>
              <CardDescription>
                {stage === "uploading" && "Đang tải lên..."}
                {stage === "analyzing" && "AI đang phân tích nguy cơ..."}
                {stage === "done" && parsed && (
                  <>
                    Hoàn tất — đã phát hiện{" "}
                    <span className="font-semibold text-destructive">
                      {(parsed.highRisk ?? 0).toLocaleString("vi-VN")}
                    </span>{" "}
                    sinh viên nguy cơ cao trên{" "}
                    {(parsed.totalStudents ?? 0).toLocaleString("vi-VN")} sinh
                    viên ({(parsed.totalTests ?? 0).toLocaleString("vi-VN")} bài
                    kiểm tra).
                  </>
                )}
                {stage === "error" && (errorMessage ?? "Có lỗi xảy ra.")}
              </CardDescription>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="rounded-lg"
            onClick={reset}
            aria-label="Huỷ"
          >
            <X className="size-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {(stage === "uploading" || stage === "analyzing") && (
          <>
            <Progress value={stage === "analyzing" ? 100 : progress} />
            <p className="text-xs text-muted-foreground">
              {stage === "analyzing"
                ? "Đang gom điểm theo sinh viên..."
                : `${progress}% · ${fileSizeKB.toFixed(1)} KB`}
            </p>
          </>
        )}

        {stage === "done" && parsed && (
          <div className="grid gap-3 rounded-xl border border-success/30 bg-success/10 p-4 sm:grid-cols-4">
            <Stat
              label="Sinh viên"
              value={(parsed.totalStudents ?? 0).toLocaleString("vi-VN")}
            />
            <Stat
              label="Điểm TB"
              value={(parsed.averageScore ?? 0).toFixed(2)}
            />
            <Stat
              label="Nguy cơ cao"
              value={(parsed.highRisk ?? 0).toLocaleString("vi-VN")}
              tone="destructive"
            />
            <Stat
              label="Email cần gửi"
              value={(parsed.draftEmails ?? 0).toLocaleString("vi-VN")}
              tone="primary"
            />
          </div>
        )}

        {stage === "error" && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            {errorMessage ?? "Không xử lý được file. Vui lòng thử lại."}
          </div>
        )}

        <div className="flex flex-wrap gap-2 pt-2">
          <Button disabled={stage !== "done"} className="rounded-xl" asChild>
            <a href="/dashboard/alerts">
              <CheckCircle2 className="size-4" />
              Tới Alert Center
            </a>
          </Button>
          <Button variant="outline" className="rounded-xl" onClick={reset}>
            Tải file khác
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function Tip({
  icon,
  title,
  desc,
}: {
  icon: React.ReactNode;
  title: string;
  desc: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 grid size-8 place-items-center rounded-lg bg-primary/10 text-primary">
        {icon}
      </span>
      <div>
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-xs text-muted-foreground">{desc}</p>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "destructive" | "primary";
}) {
  const colorMap = {
    destructive: "text-destructive",
    primary: "text-primary",
  };
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p
        className={cn(
          "font-serif text-2xl font-bold",
          tone ? colorMap[tone] : "text-foreground",
        )}
      >
        {value}
      </p>
    </div>
  );
}
