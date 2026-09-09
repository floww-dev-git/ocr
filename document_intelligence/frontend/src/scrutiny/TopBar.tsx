import { Moon, PanelLeftOpen, PanelRightOpen, Sun } from "lucide-react";

import type { AadhaarSpecimenScenario, ScrutinySummary } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/statusBadge";
import { DemoMenu } from "./DemoMenu";
import type { Theme } from "./useTheme";
import { readThreadStatus } from "./statusVocabulary";

interface TopBarProps {
  applicationId: string | null;
  applicantName: string | null;
  summary: ScrutinySummary | null;
  theme: Theme;
  onToggleTheme: () => void;
  railCollapsed: boolean;
  onOpenRail: () => void;
  onToggleSidebar: () => void;
  serviceOverride: string;
  onChooseServiceOverride: (serviceOverrides: Record<string, string>) => void;
  demoDisabled: boolean;
  aadhaarScenarios?: AadhaarSpecimenScenario[];
  onRunScenario?: (scenario: AadhaarSpecimenScenario) => void;
}

export function TopBar({
  applicationId,
  applicantName,
  summary,
  theme,
  onToggleTheme,
  railCollapsed,
  onOpenRail,
  onToggleSidebar,
  serviceOverride,
  onChooseServiceOverride,
  demoDisabled,
  aadhaarScenarios,
  onRunScenario,
}: TopBarProps) {
  const reading = summary === null ? null : readThreadStatus(summary.threadStatus);

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-surface px-3">
      {railCollapsed ? (
        <Button
          variant="ghost"
          size="icon"
          onClick={onOpenRail}
          title="Show threads"
          aria-label="Show threads"
        >
          <PanelLeftOpen />
        </Button>
      ) : null}

      {applicationId === null ? (
        <span className="text-[13px] text-ink-3">
          Pick an application to begin scrutiny
        </span>
      ) : (
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="font-mono text-[13px] text-ink-2">{applicationId}</span>
          {applicantName ? (
            <span className="truncate text-[14px] font-medium text-ink">
              {applicantName}
            </span>
          ) : null}
          {reading ? (
            <StatusBadge tone={reading.tone}>{reading.label}</StatusBadge>
          ) : null}
        </div>
      )}

      <div className="ml-auto flex items-center gap-1">
        {/* Hidden rather than disabled until there is a scrutiny to apply it to,
            the same way the composer is. */}
        {applicationId === null ? null : (
          <DemoMenu
            current={serviceOverride}
            onChoose={onChooseServiceOverride}
            disabled={demoDisabled}
            aadhaarScenarios={aadhaarScenarios}
            onRunScenario={onRunScenario}
          />
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleTheme}
          title="Switch theme"
          aria-label="Switch theme"
        >
          {theme === "dark" ? <Sun /> : <Moon />}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleSidebar}
          title="Toggle the details panel"
          aria-label="Toggle the details panel"
        >
          <PanelRightOpen />
        </Button>
      </div>
    </header>
  );
}
