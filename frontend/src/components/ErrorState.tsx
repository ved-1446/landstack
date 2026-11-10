import { AlertTriangle } from "lucide-react";
import { Button, EmptyState } from "./ui";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  on?: "navy" | "cream";
  title?: string;
}

/** A plain error with a retry button. Always says what went wrong in words. */
export function ErrorState({ message, onRetry, on = "navy", title = "Something went wrong" }: ErrorStateProps) {
  return (
    <div role="alert">
      <EmptyState
        icon={AlertTriangle}
        title={title}
        description={message}
        on={on}
        action={
          onRetry && (
            <Button variant={on === "cream" ? "paper" : "secondary"} onClick={onRetry}>
              Try again
            </Button>
          )
        }
      />
    </div>
  );
}
