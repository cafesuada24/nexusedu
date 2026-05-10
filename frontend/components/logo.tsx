"use client"

import Image from "next/image"
import Link from "next/link"
import { cn } from "@/lib/utils"

type LogoProps = {
  className?: string
  size?: "sm" | "md" | "lg" | "xl" | "xxl"
  href?: string | null
  priority?: boolean
  showText?: boolean
}

const sizeMap = {
  sm: "h-10 md:h-14", // 40px -> 56px
  md: "h-12 md:h-16", // 48px -> 64px
  lg: "h-14 md:h-16", // 56px -> 64px
  xl: "h-16 md:h-20", // 64px -> 80px
  xxl: "h-20 md:h-24", // 80px -> 96px
}

const textMap = {
  sm: "text-lg md:text-xl",
  md: "text-xl md:text-2xl",
  lg: "text-xl md:text-2xl",
  xl: "text-2xl md:text-3xl",
  xxl: "text-3xl md:text-4xl",
}

export function Logo({
  className,
  size = "md",
  href = "/",
  priority = false,
  showText = true,
  onClick,
}: LogoProps & { onClick?: () => void }) {
  const heightClass = sizeMap[size]
  const textSizeClass = textMap[size]
  
  const innerContent = (
    <div 
      className="flex flex-none flex-nowrap items-center justify-start w-fit p-0 m-0 overflow-hidden"
      style={{ gap: '4px' }}
    >
      <Image
        src="/logos/logo.png"
        alt="NexusEdu Logo"
        width={300}
        height={100}
        priority={priority}
        className={cn(
          heightClass,
          "w-auto flex-none object-contain transition-all duration-300",
          size === "sm" && "group-data-[collapsible=icon]:h-8"
        )}
      />
      {showText && (
        <span
          className={cn(
            "font-sans font-bold tracking-tighter transition-all duration-300 flex-none m-0 p-0 leading-none group-data-[collapsible=icon]:hidden whitespace-nowrap",
            textSizeClass
          )}
          style={{
            backgroundImage: 'linear-gradient(to right, #2563eb, #f97316)',
            WebkitBackgroundClip: 'text',
            backgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            display: 'inline-block'
          }}
        >
          NexusEdu
        </span>
      )}
    </div>
  )

  if (href === null) {
    return (
      <div className={cn("flex flex-none items-center justify-start w-fit p-0", className)}>
        {innerContent}
      </div>
    )
  }
  
  const containerClasses = cn(
    "flex flex-none items-center justify-start w-fit p-0 rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer",
    className
  )

  if (href) {
    return (
      <Link
        href={href}
        onClick={onClick}
        className={containerClasses}
        aria-label="NexusEdu, trang chủ"
      >
        {innerContent}
      </Link>
    )
  }

  return (
    <button
      onClick={(e) => {
        if (onClick) {
          e.preventDefault()
          onClick()
        }
      }}
      className={containerClasses}
      aria-label="NexusEdu, trang chủ"
    >
      {innerContent}
    </button>
  )
}
