import { LogOut } from "lucide-react";
import { Button, Chip, Popover } from "../../components/ui";
import { prettyRole } from "../../constants";
import type { Session } from "../../types";

interface AccountPopoverProps {
  open: boolean;
  onClose: () => void;
  session: Session;
  onLogout: () => void;
}

export function AccountPopover({ open, onClose, session, onLogout }: AccountPopoverProps) {
  return (
    <Popover open={open} onClose={onClose} title="Account">
      <div className="mt-3 flex flex-col gap-3">
        <p className="font-mono text-14 text-cream">{session.username}</p>
        <Chip>{prettyRole(session.role)}</Chip>
        <p className="text-13 text-muted-on-navy">
          {session.role === "citizen"
            ? "You can see only the plots you own."
            : "You can see every plot, its passport, and the summary counts."}
        </p>
        <Button variant="secondary" onClick={onLogout}>
          <LogOut className="size-4" aria-hidden="true" />
          Log out
        </Button>
      </div>
    </Popover>
  );
}
