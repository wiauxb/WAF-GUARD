import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium transition-colors whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary/10 text-primary",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "text-foreground",
        muted: "border-transparent bg-muted text-muted-foreground",
        // SecRule and friends — the directive types that dominate a WAF config
        rule: "border-transparent bg-blue-100 text-blue-800",
        // SecRuleRemoveById / SecRuleRemoveByTag — removals read as destructive
        removal: "border-transparent bg-amber-100 text-amber-900",
        // ModSecurity processing phase
        phase: "border-transparent bg-violet-100 text-violet-800",
        tag: "border-transparent bg-slate-100 text-slate-700",
      },
      clickable: {
        true: "cursor-pointer hover:brightness-95",
        false: "",
      },
    },
    defaultVariants: { variant: "default", clickable: false },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, clickable, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant, clickable }), className)} {...props} />
  )
}

/** Pick a badge colour from a directive's type, so removals stand out in a list. */
export function directiveVariant(type: string): BadgeProps["variant"] {
  if (type.startsWith("secruleremove")) return "removal"
  if (type.startsWith("sec")) return "rule"
  return "muted"
}

export { Badge, badgeVariants }
