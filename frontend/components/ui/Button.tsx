import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-1.5 font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
          size === "sm" && "px-3 py-1.5 text-xs",
          size === "md" && "px-4 py-2 text-sm",
          variant === "primary" && "bg-zinc-900 text-white hover:bg-zinc-700",
          variant === "secondary" && "bg-zinc-100 text-zinc-800 hover:bg-zinc-200 border border-zinc-200",
          variant === "ghost" && "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900",
          variant === "danger" && "bg-red-50 text-red-600 hover:bg-red-100 border border-red-200",
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

export default Button;
