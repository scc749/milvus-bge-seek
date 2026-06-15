"use client";

import { Inbox, Loader2, Settings2 } from "lucide-react";
import Link from "next/link";
import { ReactNode, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

export const SectionTitle = ({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) => (
  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
    <div className="space-y-1">
      <h1 className="font-semibold text-2xl tracking-tight">{title}</h1>
      {description ? (
        <p className="max-w-3xl text-muted-foreground text-sm">{description}</p>
      ) : null}
    </div>
    {action ? <div className="shrink-0">{action}</div> : null}
  </div>
);

export const Panel = ({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) => (
  <section
    className={cn(
      "min-w-0 rounded-2xl border bg-card p-5 text-card-foreground shadow-sm",
      className,
    )}
  >
    {children}
  </section>
);

export const PanelTitle = ({
  title,
  description,
}: {
  title: string;
  description?: string;
}) => (
  <div className="mb-4 space-y-1">
    <h2 className="font-medium text-base">{title}</h2>
    {description ? (
      <p className="text-muted-foreground text-sm">{description}</p>
    ) : null}
  </div>
);

export const StatusBadge = ({
  value,
}: {
  value?: string | null;
}) => {
  const normalized = (value || "unknown").toLowerCase();
  const tone =
    normalized === "completed"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800/30 dark:bg-emerald-500/10 dark:text-emerald-400"
      : normalized === "processing" || normalized === "running"
        ? "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800/30 dark:bg-blue-500/10 dark:text-blue-400"
        : normalized === "failed"
          ? "border-red-200 bg-red-50 text-red-700 dark:border-red-800/30 dark:bg-red-500/10 dark:text-red-400"
          : normalized === "pending" || normalized === "created"
            ? "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800/30 dark:bg-amber-500/10 dark:text-amber-400"
            : normalized === "deleted" || normalized === "superseded"
              ? "border-zinc-200 bg-zinc-50 text-zinc-700 dark:border-zinc-800/30 dark:bg-zinc-500/10 dark:text-zinc-400"
              : "border-zinc-200 bg-zinc-50 text-zinc-700 dark:border-zinc-800/30 dark:bg-zinc-500/10 dark:text-zinc-400";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 font-medium text-xs shadow-sm transition-colors",
        tone,
      )}
    >
      {normalized === "processing" || normalized === "running" ? (
        <span className="mr-1.5 size-1.5 rounded-full bg-blue-500"></span>
      ) : normalized === "completed" ? (
        <span className="mr-1.5 size-1.5 rounded-full bg-emerald-500"></span>
      ) : normalized === "failed" ? (
        <span className="mr-1.5 size-1.5 rounded-full bg-red-500"></span>
      ) : normalized === "pending" || normalized === "created" ? (
        <span className="mr-1.5 size-1.5 rounded-full bg-amber-500"></span>
      ) : null}
      {value || "unknown"}
    </span>
  );
};

export const StatGrid = ({
  items,
}: {
  items: Array<{ label: string; value: ReactNode; hint?: string }>;
}) => (
  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
    {items.map((item) => (
      <Panel key={item.label} className="p-4">
        <div className="text-muted-foreground text-xs">{item.label}</div>
        <div className="mt-2 font-semibold text-2xl">{item.value}</div>
        {item.hint ? (
          <div className="mt-1 text-muted-foreground text-xs">{item.hint}</div>
        ) : null}
      </Panel>
    ))}
  </div>
);

export const EmptyState = ({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon?: ReactNode;
}) => (
  <Panel className="flex min-h-[200px] flex-col items-center justify-center border-dashed bg-muted/20 text-center">
    <div className="mb-4 rounded-full bg-muted/50 p-3">
      {icon || <Inbox className="size-6 text-muted-foreground" />}
    </div>
    <h3 className="font-medium text-lg">{title}</h3>
    <p className="mt-1 max-w-sm text-muted-foreground text-sm">{description}</p>
  </Panel>
);

export const LoadingState = ({ title = "加载中..." }: { title?: string }) => (
  <Panel className="flex min-h-[200px] flex-col items-center justify-center border-dashed bg-muted/10 text-center">
    <Loader2 className="mb-4 size-6 animate-spin text-muted-foreground" />
    <p className="text-muted-foreground text-sm">{title}</p>
  </Panel>
);

export const ErrorNotice = ({ message }: { message?: string | null }) =>
  message ? (
    <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-red-600 text-sm">
      {message}
    </div>
  ) : null;

export const PaginationControls = ({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 20, 50],
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  pageSizeOptions?: number[];
}) => {
  const normalizedTotal = Math.max(0, total);
  const totalPages = Math.max(1, Math.ceil(normalizedTotal / Math.max(1, pageSize)));
  const currentPage = Math.min(Math.max(1, page), totalPages);
  const start = normalizedTotal ? (currentPage - 1) * pageSize + 1 : 0;
  const end = normalizedTotal
    ? Math.min(normalizedTotal, currentPage * pageSize)
    : 0;

  return (
    <div className="flex flex-col gap-3 border-t pt-4 md:flex-row md:items-center md:justify-between">
      <div className="text-muted-foreground text-sm">
        {normalizedTotal
          ? `显示第 ${start}-${end} 条，共 ${normalizedTotal} 条`
          : "暂无数据"}
      </div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <label className="flex items-center gap-2 text-sm">
          每页
          <select
            className="rounded-lg border bg-background px-2 py-1 text-sm"
            onChange={(event) => onPageSizeChange(Number(event.target.value))}
            value={pageSize}
          >
            {pageSizeOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          条
        </label>
        <div className="flex items-center gap-2">
          <button
            className="rounded-lg border px-3 py-1.5 text-sm transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            disabled={currentPage <= 1}
            onClick={() => onPageChange(currentPage - 1)}
            type="button"
          >
            上一页
          </button>
          <div className="min-w-24 text-center text-sm">
            第 {currentPage} / {totalPages} 页
          </div>
          <button
            className="rounded-lg border px-3 py-1.5 text-sm transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            disabled={currentPage >= totalPages}
            onClick={() => onPageChange(currentPage + 1)}
            type="button"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  );
};

export const DataTable = ({
  columns,
  rows,
  emptyText,
  defaultHiddenColumns = [],
}: {
  columns: Array<{
    key: string;
    title: string;
    className?: string;
    headerClassName?: string;
    cellClassName?: string;
  }>;
  rows: Array<Record<string, ReactNode>>;
  emptyText: string;
  defaultHiddenColumns?: string[];
}) => {
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(
    () => new Set(defaultHiddenColumns),
  );
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const toggleColumn = (key: string) => {
    setHiddenColumns((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const visibleColumns = columns.filter((c) => !hiddenColumns.has(c.key));

  const getColumnClasses = (key: string) => {
    if (
      key === "title" ||
      key.endsWith("_title") ||
      key === "source_uri" ||
      key === "replay_source_uri" ||
      key === "source_storage_uri" ||
      key === "page_url"
    ) {
      return {
        header: "min-w-56",
        cell: "min-w-56 break-words whitespace-normal",
      };
    }
    if (key === "reason" || key === "error" || key.endsWith("_message")) {
      return {
        header: "min-w-64",
        cell: "min-w-64 break-words whitespace-normal",
      };
    }
    if (
      key.endsWith("_id") ||
      key === "document_id" ||
      key === "job_id" ||
      key === "ingest_job_id" ||
      key === "delete_job_id"
    ) {
      return {
        header: "min-w-40 whitespace-nowrap",
        cell: "min-w-40 whitespace-nowrap font-mono text-xs",
      };
    }
    if (key === "status" || key.endsWith("_status") || key === "source_type") {
      return {
        header: "min-w-28 whitespace-nowrap",
        cell: "min-w-28 whitespace-nowrap",
      };
    }
    if (key.endsWith("_at") || key === "created_at" || key === "updated_at") {
      return {
        header: "min-w-44 whitespace-nowrap",
        cell: "min-w-44 whitespace-nowrap",
      };
    }
    if (
      key.includes("count") ||
      key.includes("number") ||
      key.includes("depth")
    ) {
      return {
        header: "min-w-24 whitespace-nowrap",
        cell: "min-w-24 whitespace-nowrap",
      };
    }
    return {
      header: "min-w-32",
      cell: "min-w-32 break-words whitespace-normal",
    };
  };

  return (
    <div className="space-y-3">
      {columns.length > 3 ? (
        <div className="flex justify-end">
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setIsDropdownOpen((prev) => !prev)}
              className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-1.5 text-xs font-medium shadow-sm transition-colors hover:bg-muted"
            >
              <Settings2 className="size-3.5" />
              显示列
            </button>
            {isDropdownOpen ? (
              <div className="absolute right-0 z-10 mt-1 w-48 rounded-md border bg-card p-1 shadow-md">
                {columns.map((c) => (
                  <label
                    key={c.key}
                    className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 hover:bg-muted/50"
                  >
                    <input
                      type="checkbox"
                      className="size-3.5 rounded border-gray-300"
                      checked={!hiddenColumns.has(c.key)}
                      onChange={() => toggleColumn(c.key)}
                    />
                    <span className="truncate text-xs">{c.title}</span>
                  </label>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
      <div className="overflow-x-auto rounded-xl border">
        <table className="w-full min-w-max table-auto text-left text-sm">
        <thead className="bg-muted/80 text-muted-foreground">
          <tr>
            {visibleColumns.map((column) => (
              <th
                key={column.key}
                className={cn(
                  "px-4 py-3 font-semibold align-top",
                  getColumnClasses(column.key).header,
                  column.className,
                  column.headerClassName,
                )}
              >
                {column.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row, index) => (
              <tr key={index} className="border-t align-top transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                {visibleColumns.map((column) => (
                  <td
                    key={column.key}
                    className={cn(
                      "px-4 py-3 text-sm align-top",
                      getColumnClasses(column.key).cell,
                      column.className,
                      column.cellClassName,
                    )}
                  >
                    {row[column.key]}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td
                colSpan={visibleColumns.length}
                className="px-4 py-8 text-center text-muted-foreground text-sm"
              >
                {emptyText}
              </td>
            </tr>
          )}
        </tbody>
        </table>
      </div>
    </div>
  );
};

export const KeyValueList = ({
  items,
}: {
  items: Array<{ label: string; value?: ReactNode }>;
}) => (
  <dl className="grid gap-3 md:grid-cols-2">
    {items.map((item) => (
      <div key={item.label} className="rounded-xl bg-muted/30 px-4 py-3">
        <dt className="text-muted-foreground text-xs">{item.label}</dt>
        <dd className="mt-1 break-all text-sm">{item.value || "-"}</dd>
      </div>
    ))}
  </dl>
);

export const InlineLink = ({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) => (
  <Link className="font-medium text-primary hover:underline" href={href}>
    {children}
  </Link>
);
