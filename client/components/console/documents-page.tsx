"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { RefreshCcw, Upload, Link2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  ErrorNotice,
  Panel,
  PanelTitle,
  PaginationControls,
  SectionTitle,
  StatusBadge,
  DataTable,
  EmptyState,
  LoadingState,
} from "@/components/console/console-ui";
import type {
  ContractField,
  PageContract,
} from "@/lib/contracts/page-contract";
import {
  buildContractTable,
  findContractTable,
  getFilterOptions,
  getSortOptions,
} from "@/lib/contracts/page-contract";
import {
  getPageContract,
  ingestDocumentSource,
  listDocuments,
} from "@/lib/langgraphApi";

type DocumentRecord = {
  document_id: string;
  title?: string;
  status?: string;
  source_type?: string;
  source_uri?: string;
  replay_source_uri?: string;
  updated_at?: string;
  source_storage?: {
    storage_uri?: string;
    effective_backend?: string;
  };
};

const ACTIVE_DOCUMENT_STATUSES = new Set(["created", "pending", "processing", "running"]);

const isActiveDocumentStatus = (value?: string | null) =>
  ACTIVE_DOCUMENT_STATUSES.has(String(value || "").toLowerCase());

const renderDocumentValue = (
  field: ContractField,
  value: unknown,
  record: DocumentRecord,
): ReactNode => {
  if (field.key === "title") {
    return (
      <Link
        className="font-medium text-primary hover:underline"
        href={`/documents/${encodeURIComponent(record.document_id)}`}
      >
        {String(value || record.title || record.document_id)}
      </Link>
    );
  }
  if (field.value_type === "badge") {
    return <StatusBadge value={String(value || "")} />;
  }
  if (field.value_type === "datetime") {
    return value ? new Date(String(value)).toLocaleString() : "-";
  }
  if (field.key === "source_uri" || field.key === "source_storage_uri") {
    return <div className="max-w-[320px] break-all text-xs">{String(value || "-")}</div>;
  }
  return String(value || "-");
};

const toBase64 = async (file: File) => {
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
  return dataUrl.split(",")[1] || "";
};

export const DocumentsPage = ({
  initialRecords = [],
  initialContract = null,
  initialError = null,
  initialPage = 1,
  initialPageSize = 20,
  initialTotal = initialRecords.length,
  initialQuery = "",
  initialStatusFilter = "",
  initialSourceTypeFilter = "",
  initialSortBy = "updated_at",
  initialSortDirection = "desc",
}: {
  initialRecords?: DocumentRecord[];
  initialContract?: PageContract | null;
  initialError?: string | null;
  initialPage?: number;
  initialPageSize?: number;
  initialTotal?: number;
  initialQuery?: string;
  initialStatusFilter?: string;
  initialSourceTypeFilter?: string;
  initialSortBy?: string;
  initialSortDirection?: "asc" | "desc";
}) => {
  const pathname = usePathname();
  const [records, setRecords] = useState<DocumentRecord[]>(initialRecords);
  const [contract, setContract] = useState<PageContract | null>(initialContract);
  const [query, setQuery] = useState(initialQuery);
  const [statusFilter, setStatusFilter] = useState(initialStatusFilter);
  const [sourceTypeFilter, setSourceTypeFilter] = useState(initialSourceTypeFilter);
  const [sortBy, setSortBy] = useState(initialSortBy);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">(initialSortDirection);
  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [total, setTotal] = useState(initialTotal);
  const [loading, setLoading] = useState(
    !initialContract && !initialRecords.length && !initialError,
  );
  const [error, setError] = useState<string | null>(initialError);
  const skipInitialLoadRef = useRef(
    Boolean(initialContract || initialRecords.length || initialError),
  );

  const [uploadMode, setUploadMode] = useState<"file" | "url">("file");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sourceUrl, setSourceUrl] = useState("");
  const [recursiveUrl, setRecursiveUrl] = useState(true);
  const [recursiveMaxDepth, setRecursiveMaxDepth] = useState(2);
  const [submitting, setSubmitting] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [latestSubmissionAt, setLatestSubmissionAt] = useState<number | null>(null);

  const loadPage = async ({ background = false }: { background?: boolean } = {}) => {
    if (!background) {
      setLoading(true);
      setError(null);
    }
    try {
      const [contractRes, listRes] = await Promise.all([
        getPageContract("document_list"),
        listDocuments({
          page,
          page_size: pageSize,
          query,
          status_filter: statusFilter || undefined,
          source_type_filter: sourceTypeFilter || undefined,
          sort_by: sortBy,
          sort_direction: sortDirection,
        }),
      ]);
      setContract(contractRes.page_contract || null);
      setRecords((listRes.records as DocumentRecord[]) || []);
      setTotal(Number(listRes.total || 0));
      if (listRes.error) {
        setError(listRes.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "文档列表加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (skipInitialLoadRef.current) {
      skipInitialLoadRef.current = false;
      return;
    }
    void loadPage();
  }, [page, pageSize, query, statusFilter, sourceTypeFilter, sortBy, sortDirection]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (query) {
      params.set("query", query);
    }
    if (statusFilter) {
      params.set("status_filter", statusFilter);
    }
    if (sourceTypeFilter) {
      params.set("source_type_filter", sourceTypeFilter);
    }
    if (sortBy !== "updated_at") {
      params.set("sort_by", sortBy);
    }
    if (sortDirection !== "desc") {
      params.set("sort_direction", sortDirection);
    }
    if (page !== 1) {
      params.set("page", String(page));
    }
    if (pageSize !== 20) {
      params.set("page_size", String(pageSize));
    }
    const queryString = params.toString();
    const nextUrl = queryString ? `${pathname}?${queryString}` : pathname;
    window.history.replaceState(null, "", nextUrl);
  }, [pathname, page, pageSize, query, sortBy, sortDirection, sourceTypeFilter, statusFilter]);

  const statusOptions = useMemo<string[]>(() => {
    return getFilterOptions(contract, "status_filter");
  }, [contract]);

  const sourceTypeOptions = useMemo<string[]>(() => {
    return getFilterOptions(contract, "source_type_filter");
  }, [contract]);

  const sortOptions = useMemo<Array<{ value: string; label: string }>>(() => {
    return getSortOptions(contract).map((item) => ({
      value: item.value,
      label: item.label,
    }));
  }, [contract]);

  const documentTable = useMemo(
    () => buildContractTable(findContractTable(contract, "document_table"), { records }),
    [contract, records],
  );

  const handleIngest = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setActionMessage(null);
    setActionError(null);
    try {
      const input =
        uploadMode === "file"
          ? selectedFile
            ? {
                source_name: selectedFile.name,
                source_mime_type:
                  selectedFile.type || "application/octet-stream",
                source_content_b64: await toBase64(selectedFile),
                backup_source: true,
              }
            : null
          : sourceUrl
            ? {
                source_uri: sourceUrl,
                backup_source: true,
                recursive_url: recursiveUrl,
                recursive_max_depth: recursiveUrl ? recursiveMaxDepth : 0,
                recursive_prevent_outside: true,
              }
            : null;

      if (!input) {
        setActionError("请先选择文件或填写 URL。");
        return;
      }

      const result = await ingestDocumentSource(input);
      if (result.error || result.status === "failed") {
        setActionError(result.error || "入库失败");
        return;
      }

      setActionMessage(
        result.message ||
          `入库任务已提交：job=${result.ingest_job_id || "-"}。请前往 /jobs/ingest 查看处理进度。${
            uploadMode === "url" && recursiveUrl
              ? ` 当前会按站内递归抓取，最大深度 ${recursiveMaxDepth}。`
              : ""
          }`,
      );
      setLatestSubmissionAt(Date.now());
      setSelectedFile(null);
      setSourceUrl("");
      void loadPage({ background: true });
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "入库失败");
    } finally {
      setSubmitting(false);
    }
  };

  const shouldAutoRefresh = useMemo(() => {
    const hasProcessingRecord = records.some((item) => isActiveDocumentStatus(item.status));
    const withinWarmupWindow =
      latestSubmissionAt != null && Date.now() - latestSubmissionAt < 60_000;
    return hasProcessingRecord || withinWarmupWindow;
  }, [latestSubmissionAt, records]);

  useEffect(() => {
    if (!shouldAutoRefresh) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadPage({ background: true });
    }, 5000);
    return () => window.clearInterval(timer);
  }, [
    shouldAutoRefresh,
    page,
    pageSize,
    query,
    statusFilter,
    sourceTypeFilter,
    sortBy,
    sortDirection,
  ]);

  return (
    <div className="space-y-6">
      <SectionTitle
        title="文档中心"
        description="对接 rag_admin 与 rag_ingest：支持文档列表浏览、URL/文件入库，并可进入详情页查看版本、重建和删除状态。"
        action={
          <Button onClick={() => void loadPage()} size="sm" variant="outline">
            <RefreshCcw className="size-4" />
            刷新
          </Button>
        }
      />

      <Panel>
        <PanelTitle
          title="上传与入库"
          description="支持直接上传文件内容，也支持提交 URL 让后端抓取并异步入库。URL 模式支持站内递归抓取子页面，并按页面分别入库。"
        />
        <form className="space-y-4" onSubmit={handleIngest}>
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => setUploadMode("file")}
              size="sm"
              type="button"
              variant={uploadMode === "file" ? "default" : "outline"}
            >
              <Upload className="size-4" />
              文件入库
            </Button>
            <Button
              onClick={() => setUploadMode("url")}
              size="sm"
              type="button"
              variant={uploadMode === "url" ? "default" : "outline"}
            >
              <Link2 className="size-4" />
              URL 入库
            </Button>
          </div>

          {uploadMode === "file" ? (
            <input
              key="file-source-input"
              className="w-full rounded-xl border bg-background px-3 py-2 text-sm"
              onChange={(event) =>
                setSelectedFile(event.target.files?.[0] || null)
              }
              type="file"
            />
          ) : (
            <div className="space-y-3">
              <input
                key="url-source-input"
                className="w-full rounded-xl border bg-background px-3 py-2 text-sm"
                onChange={(event) => setSourceUrl(event.target.value)}
                placeholder="https://example.com/article"
                value={sourceUrl}
              />
              <div className="grid gap-3 md:grid-cols-[auto_180px]">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    checked={recursiveUrl}
                    onChange={(event) => setRecursiveUrl(event.target.checked)}
                    type="checkbox"
                  />
                  递归抓取站内子页面
                </label>
                <label className="flex items-center gap-2 text-sm">
                  最大深度
                  <input
                    className="w-24 rounded-xl border bg-background px-3 py-2 text-sm"
                    disabled={!recursiveUrl}
                    max={6}
                    min={0}
                    onChange={(event) =>
                      setRecursiveMaxDepth(
                        Math.min(6, Math.max(0, Number(event.target.value) || 0)),
                      )
                    }
                    type="number"
                    value={recursiveMaxDepth}
                  />
                </label>
              </div>
              <div className="text-muted-foreground text-xs">
                递归模式会限制在当前 URL 站内范围，并把每个命中的页面按独立文档记录入库，便于后续检索、详情查看与重建。
              </div>
            </div>
          )}

          <ErrorNotice message={actionError} />
          {actionMessage ? (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 text-emerald-600 text-sm">
              {actionMessage}
            </div>
          ) : null}

          <Button disabled={submitting} type="submit">
            {submitting ? "提交任务中..." : "提交入库任务"}
          </Button>
        </form>
      </Panel>

      <Panel>
        <PanelTitle
          title="筛选与排序"
          description="这些字段与后端页面契约保持一致。"
        />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <input
            className="rounded-xl border bg-background px-3 py-2 text-sm"
            onChange={(event) => {
              setPage(1);
              setQuery(event.target.value);
            }}
            placeholder="搜索文档标题或来源"
            value={query}
          />
          <select
            className="rounded-xl border bg-background px-3 py-2 text-sm"
            onChange={(event) => {
              setPage(1);
              setStatusFilter(event.target.value);
            }}
            value={statusFilter}
          >
            <option value="">全部状态</option>
            {statusOptions.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <select
            className="rounded-xl border bg-background px-3 py-2 text-sm"
            onChange={(event) => {
              setPage(1);
              setSourceTypeFilter(event.target.value);
            }}
            value={sourceTypeFilter}
          >
            <option value="">全部来源</option>
            {sourceTypeOptions.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <select
            className="rounded-xl border bg-background px-3 py-2 text-sm"
            onChange={(event) => {
              setPage(1);
              setSortBy(event.target.value);
            }}
            value={sortBy}
          >
            {sortOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <select
            className="rounded-xl border bg-background px-3 py-2 text-sm"
            onChange={(event) => {
              setPage(1);
              setSortDirection(event.target.value as "asc" | "desc");
            }}
            value={sortDirection}
          >
            <option value="desc">倒序</option>
            <option value="asc">正序</option>
          </select>
        </div>
      </Panel>

      <ErrorNotice message={error} />

      {loading ? (
        <LoadingState />
      ) : records.length ? (
        <Panel>
          <PanelTitle
            title="文档列表"
            description="点击标题进入详情页，可进一步查看版本、来源存储、删除与重建动作。"
          />
          <DataTable
            columns={documentTable.columns.map((column) => ({
              key: column.key,
              title: column.label,
              headerClassName:
                column.key === "title"
                  ? "min-w-64"
                  : column.key === "source_uri"
                    ? "min-w-72"
                    : undefined,
            }))}
            defaultHiddenColumns={["document_id", "source_storage_uri", "current_version_number"]}
            emptyText="暂无文档"
            rows={documentTable.rows.map((row, index) => {
              const record = records[index] || {};
              return Object.fromEntries(
                documentTable.columns.map((column) => [
                  column.key,
                  renderDocumentValue(column, row[column.key], record),
                ]),
              );
            })}
          />
          <PaginationControls
            onPageChange={setPage}
            onPageSizeChange={(nextPageSize) => {
              setPage(1);
              setPageSize(nextPageSize);
            }}
            page={page}
            pageSize={pageSize}
            total={total}
          />
        </Panel>
      ) : (
        <EmptyState
          description="先通过上方的文件或 URL 入库，或者检查筛选条件。"
          title="暂无文档"
        />
      )}
    </div>
  );
};
