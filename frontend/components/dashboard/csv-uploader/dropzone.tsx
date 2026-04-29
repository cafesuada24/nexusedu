"use client";

import * as React from "react";
import { UploadCloud, FileText, X, Info, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { SOURCE_META, type SourceKey } from "@/lib/constants";

export type StagedFile = {
  file: File;
  text: string;
  sizeKB: number;
};

export type StagedMap = Partial<Record<SourceKey, StagedFile>>;

export function Dropzone({
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

export function HintLine({ staged }: { staged: StagedMap }) {
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
