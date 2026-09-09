import { MoreHorizontal, PanelLeftClose, Plus, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import type { Application, ThreadStatus } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Orb } from "./Orb";
import {
  matchesApplicationSearch,
  readApplicationHeadline,
} from "./applicationSummary";
import { readRelativeTime } from "./relativeTime";

/** What the rail needs to know about one application beyond its record. */
export interface RailThreadState {
  /** The live thread status when this application is open; null otherwise. */
  status: ThreadStatus | null;
  /** Open items needing attention, for the count pill. */
  openCount: number;
  /** When this application was last opened, for the relative time. */
  openedAt: number | null;
  /** An officer's rename, kept in the client as the prototype does. */
  title: string | null;
}

interface ThreadRailProps {
  applications: Application[];
  selectedApplicationId: string | null;
  onSelectApplication: (applicationId: string) => void;
  onCollapse: () => void;
  loading: boolean;
  /** Per-application UI state, keyed by applicationId. */
  threadState: Record<string, RailThreadState>;
  onRename: (applicationId: string, title: string) => void;
  onDelete: (applicationId: string) => void;
  /** Opens the picker, which is the only way an application reaches this list. */
  onNewScrutiny: () => void;
}

const DOT_TONES: Record<ThreadStatus, string> = {
  new: "bg-pending",
  running: "ai-gradient animate-[pulse_1.4s_ease-in-out_infinite]",
  attention: "bg-warn",
  clear: "bg-pass",
};

export function ThreadRail({
  applications,
  selectedApplicationId,
  onSelectApplication,
  onCollapse,
  loading,
  threadState,
  onRename,
  onDelete,
  onNewScrutiny,
}: ThreadRailProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [menuFor, setMenuFor] = useState<string | null>(null);

  const visible = useMemo(
    () =>
      applications.filter((application) =>
        matchesApplicationSearch(application, searchTerm),
      ),
    [applications, searchTerm],
  );

  return (
    <aside
      aria-label="Scrutiny threads"
      className="flex h-full w-(--rail-w) shrink-0 flex-col gap-2.5 border-r border-line bg-surface p-2.5"
    >
      <div className="flex items-center gap-2.5 px-1 pt-1 pb-2">
        <Orb size={26} className="shrink-0" />
        <div className="flex min-w-0 flex-col leading-tight">
          <span className="truncate text-[14px] font-semibold text-ink">
            Document Intelligence
          </span>
          <span className="truncate text-[12px] text-ink-3">UrbanFloww AI</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto"
          onClick={onCollapse}
          title="Collapse threads"
          aria-label="Collapse threads"
        >
          <PanelLeftClose />
        </Button>
      </div>

      <Button variant="primary" className="w-full" onClick={onNewScrutiny}>
        <Plus />
        New scrutiny
      </Button>

      <label className="relative block">
        <span className="sr-only">Search applications</span>
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-ink-3"
        />
        <Input
          type="search"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          placeholder="Search applications"
          className="pl-8"
        />
      </label>

      <ul
        role="list"
        className="-mr-1 flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto pr-1"
      >
        {loading ? (
          <li className="px-2 py-3 text-[13px] text-ink-3">Loading applications…</li>
        ) : null}
        {!loading && visible.length === 0 ? (
          <li className="px-2 py-3 text-[13px] text-ink-3">
            {applications.length === 0
              ? "No scrutiny open. Press New scrutiny to take up an application."
              : "No application matches that search."}
          </li>
        ) : null}
        {visible.map((application) => (
          <ThreadRow
            key={application.applicationId}
            application={application}
            state={threadState[application.applicationId]}
            selected={application.applicationId === selectedApplicationId}
            menuOpen={menuFor === application.applicationId}
            onOpen={() => onSelectApplication(application.applicationId)}
            onToggleMenu={() =>
              setMenuFor((current) =>
                current === application.applicationId
                  ? null
                  : application.applicationId,
              )
            }
            onCloseMenu={() => setMenuFor(null)}
            onRename={(title) => {
              onRename(application.applicationId, title);
              setMenuFor(null);
            }}
            onDelete={() => {
              onDelete(application.applicationId);
              setMenuFor(null);
            }}
          />
        ))}
      </ul>
    </aside>
  );
}

interface ThreadRowProps {
  application: Application;
  state: RailThreadState | undefined;
  selected: boolean;
  menuOpen: boolean;
  onOpen: () => void;
  onToggleMenu: () => void;
  onCloseMenu: () => void;
  onRename: (title: string) => void;
  onDelete: () => void;
}

function ThreadRow({
  application,
  state,
  selected,
  menuOpen,
  onOpen,
  onToggleMenu,
  onCloseMenu,
  onRename,
  onDelete,
}: ThreadRowProps) {
  const headline = readApplicationHeadline(application);
  // A not-yet-opened application reads "pending", exactly the prototype's default
  // for an application nothing has been analyzed against.
  const status: ThreadStatus = state?.status ?? "new";
  const openCount = state?.openCount ?? 0;
  const title = state?.title ?? headline.applicationId;
  const time = state?.openedAt !== null && state?.openedAt !== undefined
    ? readRelativeTime(state.openedAt)
    : null;

  return (
    <li className="relative">
      <button
        type="button"
        aria-current={selected ? "true" : undefined}
        onClick={onOpen}
        title={`${headline.applicationId} ${headline.applicantName}`}
        className={cn(
          "group grid w-full grid-cols-[14px_1fr_auto] items-start gap-x-2 rounded-[var(--radius-m)] py-2 pr-2.5 pl-2 text-left transition-colors",
          selected ? "bg-surface-3" : "hover:bg-surface-2",
        )}
      >
        {selected ? (
          <span
            aria-hidden="true"
            className="absolute top-2.5 bottom-2.5 left-0 w-[3px] rounded-full bg-ai"
          />
        ) : null}

        <span
          aria-hidden="true"
          className={cn("mt-[7px] size-2 rounded-full", DOT_TONES[status])}
        />

        <span className="flex min-w-0 flex-col">
          <span
            className={cn(
              "font-mono text-[13px]",
              selected ? "text-ai-text" : "text-ink",
            )}
          >
            {title}
          </span>
          <span className="truncate text-[13px] text-ink-2">
            {headline.applicantName}
          </span>
          {time ? (
            <span className="mt-0.5 text-[11px] text-ink-3">{time}</span>
          ) : null}
        </span>

        <span className="flex flex-col items-end gap-1">
          {openCount > 0 ? (
            <span className="rounded-full bg-warn-soft px-[7px] py-px text-[11px] font-semibold text-warn">
              {openCount}
            </span>
          ) : null}
          <span
            role="button"
            tabIndex={0}
            aria-label="Thread options"
            onClick={(event) => {
              event.stopPropagation();
              onToggleMenu();
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                event.stopPropagation();
                onToggleMenu();
              }
            }}
            className={cn(
              "flex size-6 items-center justify-center rounded-[var(--radius-s)] text-ink-3 transition-opacity hover:bg-surface-3 hover:text-ink",
              menuOpen ? "opacity-100" : "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100",
            )}
          >
            <MoreHorizontal className="size-4" aria-hidden="true" />
          </span>
        </span>
      </button>

      {menuOpen ? (
        <ThreadMenu
          currentTitle={title}
          onRename={onRename}
          onDelete={onDelete}
          onClose={onCloseMenu}
        />
      ) : null}
    </li>
  );
}

function ThreadMenu({
  currentTitle,
  onRename,
  onDelete,
  onClose,
}: {
  currentTitle: string;
  onRename: (title: string) => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const closeOnOutside = (event: MouseEvent) => {
      if (!container.current?.contains(event.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", closeOnOutside);
    return () => document.removeEventListener("mousedown", closeOnOutside);
  }, [onClose]);

  return (
    <div
      ref={container}
      role="menu"
      className="absolute top-9 right-2 z-10 flex min-w-[130px] flex-col rounded-[var(--radius-m)] border border-line bg-surface p-1 shadow-(--shadow-float)"
    >
      <button
        type="button"
        role="menuitem"
        onClick={() => {
          const next = window.prompt("Thread name", currentTitle);
          if (next !== null && next.trim().length > 0) {
            onRename(next.trim());
          }
        }}
        className="rounded-[var(--radius-s)] px-2.5 py-1.5 text-left text-[13px] text-ink hover:bg-surface-3"
      >
        Rename
      </button>
      <button
        type="button"
        role="menuitem"
        onClick={onDelete}
        className="rounded-[var(--radius-s)] px-2.5 py-1.5 text-left text-[13px] text-fail hover:bg-surface-3"
      >
        Delete
      </button>
    </div>
  );
}
