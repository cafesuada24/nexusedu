"use client";

import { useState } from "react";
import { Check, Copy, Download } from "lucide-react";

interface SampleCSVBlockProps {
  title: string;
  data: string;
  filename: string;
}

export function SampleCSVBlock({ title, data, filename }: SampleCSVBlockProps) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(data);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadCSV = () => {
    const blob = new Blob([data], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mt-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-950 overflow-hidden shadow-sm">
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800">
        <span className="text-xs font-medium text-slate-400">{title}</span>
        <div className="flex gap-2">
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-1 text-xs px-2 py-1 text-slate-300 hover:bg-slate-800 rounded transition"
          >
            {copied ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
            {copied ? "Đã chép" : "Sao chép mẫu"}
          </button>
          <button
            onClick={downloadCSV}
            className="flex items-center gap-1 text-xs px-2 py-1 text-slate-300 hover:bg-slate-800 rounded transition"
          >
            <Download size={14} />
            Tải file (.csv)
          </button>
        </div>
      </div>
      <pre className="p-4 text-xs font-mono overflow-x-auto text-slate-300 whitespace-pre-wrap">
        {data}
      </pre>
    </div>
  );
}
