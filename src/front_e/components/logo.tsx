import { GraduationCap } from "lucide-react";
import { cn } from "@/lib/utils";

type LogoProps = {
  className?: string;
  size?: "sm" | "md" | "lg";
  href?: string | null;
  showMark?: boolean;
};

const sizeMap = {
  sm: { text: "text-lg", mark: "size-7", icon: "size-4" },
  md: { text: "text-xl", mark: "size-9", icon: "size-5" },
  lg: { text: "text-3xl", mark: "size-11", icon: "size-6" },
};

export function Logo({
  className,
  size = "md",
  href = "/",
  showMark = true,
}: LogoProps) {
  const s = sizeMap[size];
  const content = (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      {showMark && (
        <span
          className={cn(
            "grid place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm ring-1 ring-primary/20",
            s.mark,
          )}
          aria-hidden="true"
        >
          <GraduationCap className={s.icon} />
        </span>
      )}
      <span
        className={cn(
          "font-serif font-black tracking-tight text-foreground",
          s.text,
        )}
      >
        NexusEdu
      </span>
    </span>
  );

  // Important: do not render an <a> or Next.js <Link> inside the Logo component.
  // This avoids nested anchor (<a>) elements when parent components wrap the logo with a link.
  // The `href` prop is intentionally ignored here so callers can decide how to wrap/link the logo.
  return content;
}
