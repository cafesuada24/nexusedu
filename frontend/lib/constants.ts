import { GraduationCap, BookCopy } from "lucide-react";

export type SourceKey = "LMS" | "SIS";

export const SOURCE_META: Record<
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
