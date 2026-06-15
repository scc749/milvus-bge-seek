"use client";

import { usePathname } from "next/navigation";
import { ReactNode, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  DataTable,
  EmptyState,
  ErrorNotice,
  InlineLink,
  KeyValueList,
  LoadingState,
  Panel,
  PanelTitle,
  PaginationControls,
  SectionTitle,
  StatGrid,
  StatusBadge,
} from "@/components/console/console-ui";
import type {
  ContractField,
  PageContract,
} from "@/lib/contracts/page-contract";
import {
  buildContractFields,
  buildContractStats,
  buildContractTable,
  findContractSection,
  findContractTable,
  getFilterOptions,
  getSortOptions,
} from "@/lib/contracts/page-contract";
import {
  getDeleteJobDetail,
  getIngestJobDetail,
  getPageContract,
  listDeleteJobs,
  listIngestJobs,
} from "@/lib/langgraphApi";

type JobKind = "ingest" | "delete";

type JobRecord = {
  job_id?: string;
  delete_job_id?: string;
  ingest_job_id?: string;
  status?: string;
  source_uri?: string;
  reason?: string;
  chunk_count?: number;
  deleted_chunk_count?: number;
  upserted_count?: number;
  created_at?: string;
  updated_at?: string;
};

const ACTIVE_JOB_STATUSES = new Set([
  "created",
  "queued",
  "pending",
  "processing",
  "running",
]);

const isActiveJobStatus = (value?: string | null) =>
  ACTIVE_JOB_STATUSES.has(String(value || "").toLowerCase());

const getJobRecordId = (record: JobRecord) =>
  String(record.job_id || record.ingest_job_id || record.delete_job_id || "");

const renderJobValue = (
  field: ContractField,
  value: unknown,
  options?: {
    onSelectJob?: () => void;
  },
): ReactNode => {
  if (field.key === "job_id" && options?.onSelectJob) {
    return (
      <button
        className="font-medium text-left text-primary hover:underline"
        onClick={options.onSelectJob}
        type="button"
      >
        {String(value || "-")}
      </button>
    );
  }
  if (field.value_type === "badge") {
    return <StatusBadge value={String(value || "")} />;
  }
  if (field.value_type === "datetime") {
    return value ? new Date(String(value)).toLocaleString() : "-";
  }
  return String(value || "-");
};

export const JobsPage = ({
  kind,
  initialRecords = [],
  initialDetail = null,
  initialContract = null,
  initialSelectedJobId = "",
  initialError = null,
  initialPage = 1,
  initialPageSize = 20,
  initialTotal = initialRecords.length,
  initialStatusFilter = "",
  initialSortBy = "updated_at",
  initialSortDirection = "desc",
}: {
  kind: JobKind;
  initialRecords?: JobRecord[];
  initialDetail?: Record<string, any> | null;
  initialContract?: PageContract | null;
  initialSelectedJobId?: string;
  initialError?: string | null;
  initialPage?: number;
  initialPageSize?: number;
  initialTotal?: number;
  initialStatusFilter?: string;
  initialSortBy?: string;
  initialSortDirection?: "asc" | "desc";
}) => {
  const pathname = usePathname();
  const [records, setRecords] = useState<JobRecord[]>(initialRecords);
  const [selectedJobId, setSelectedJobId] = useState<string>(initialSelectedJobId);
  const [detail, setDetail] = useState<Record<string, any> | null>(initialDetail);
  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [total, setTotal] = useState(initialTotal);
  const [loading, setLoading] = useState(
    !initialContract && !initialRecords.length && !initialError,
  );
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(initialError);
  const [statusFilter, setStatusFilter] = useState(initialStatusFilter);
  const [sortBy, setSortBy] = useState(initialSortBy);
  const [sortDirection, setSortDirection] =
    useState<"asc" | "desc">(initialSortDirection);
  const [contract, setContract] = useState<PageContract | null>(initialContract);
  const skipInitialListLoadRef = useRef(
    Boolean(initialContract || initialRecords.length || initialError),
  );
  const skipInitialDetailLoadRef = useRef(
    Boolean(initialSelectedJobId && initialDetail),
  );

  const pageName = kind === "ingest" ? "ingest_job" : "delete_job";

  const loadList = async ({ background = false }: { background?: boolean } = {}) => {
    if (!background) {
      setLoading(true);
      setError(null);
    }
    try {
      const [contractRes, listRes] = await Promise.all([
        getPageContract(pageName),
        kind === "ingest"
          ? listIngestJobs({
              page,
              page_size: pageSize,
              status_filter: statusFilter || undefined,
              sort_by: sortBy,
              sort_direction: sortDirection,
            })
          : listDeleteJobs({
              page,
              page_size: pageSize,
              status_filter: statusFilter || undefined,
              sort_by: sortBy,
              sort_direction: sortDirection,
            }),
      ]);
      setContract(contractRes.page_contract || null);
      const rows = (listRes.records as JobRecord[]) || [];
      setRecords(rows);
      setTotal(Number(listRes.total || 0));
      const firstJobId = getJobRecordId(rows[0] || {});
      setSelectedJobId((current) =>
        rows.some((item) => getJobRecordId(item) === current)
          ? current
          : String(firstJobId || ""),
      );
      if (listRes.error) {
        setError(listRes.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务列表加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (skipInitialListLoadRef.current) {
      skipInitialListLoadRef.current = false;
      return;
    }
    void loadList();
  }, [kind, page, pageSize, statusFilter, sortBy, sortDirection]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (statusFilter) {
      params.set("status_filter", statusFilter);
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
    if (selectedJobId) {
      params.set("job_id", selectedJobId);
    }
    const queryString = params.toString();
    const nextUrl = queryString ? `${pathname}?${queryString}` : pathname;
    window.history.replaceState(null, "", nextUrl);
  }, [pathname, page, pageSize, selectedJobId, sortBy, sortDirection, statusFilter]);

  const loadDetail = async ({ background = false }: { background?: boolean } = {}) => {
    if (!selectedJobId) {
      setDetail(null);
      return;
    }
    if (!background) {
      setDetailLoading(true);
    }
    try {
      const result =
        kind === "ingest"
          ? await getIngestJobDetail(selectedJobId)
          : await getDeleteJobDetail(selectedJobId);
      setDetail((result.records?.[0] as Record<string, any>) || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "任务详情加载失败");
    } finally {
      if (!background) {
        setDetailLoading(false);
      }
    }
  };

  useEffect(() => {
    if (skipInitialDetailLoadRef.current) {
      skipInitialDetailLoadRef.current = false;
      return;
    }
    void loadDetail();
  }, [kind, selectedJobId]);

  const statusOptions = useMemo<string[]>(() => {
    return getFilterOptions(contract, "status_filter");
  }, [contract]);
  const sortOptions = useMemo<Array<{ value: string; label: string }>>(() => {
    return getSortOptions(contract).map((item) => ({
      value: item.value,
      label: item.label,
    }));
  }, [contract]);

  const listTable = useMemo(
    () =>
      buildContractTable(
        findContractTable(
          contract,
          kind === "ingest" ? "ingest_job_table" : "delete_job_table",
        ),
        { records },
      ),
    [contract, kind, records],
  );
  const detailSource = useMemo(() => ({ records: detail ? [detail] : [] }), [detail]);
  const summarySection = useMemo(
    () => findContractSection(contract, "summary"),
    [contract],
  );
  const statsSection = useMemo(
    () => findContractSection(contract, "stats"),
    [contract],
  );
  const documentsSection = useMemo(
    () => findContractSection(contract, "documents"),
    [contract],
  );
  const documentSection = useMemo(
    () => findContractSection(contract, "document"),
    [contract],
  );
  const summaryItems = useMemo(
    () => buildContractFields(summarySection?.fields, detailSource),
    [detailSource, summarySection],
  );
  const statItems = useMemo(
    () => buildContractStats(statsSection?.stat_cards || contract?.stat_cards, detailSource),
    [contract?.stat_cards, detailSource, statsSection],
  );
  const documentsTable = useMemo(
    () => buildContractTable(documentsSection?.tables?.[0] || null, detailSource),
    [detailSource, documentsSection],
  );
  const documentItems = useMemo(
    () => buildContractFields(documentSection?.fields, detailSource),
    [detailSource, documentSection],
  );
  const shouldAutoRefresh = useMemo(
    () =>
      records.some((item) => isActiveJobStatus(item.status)) ||
      isActiveJobStatus(String(detail?.status || "")),
    [detail?.status, records],
  );

  useEffect(() => {
    if (!shouldAutoRefresh) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadList({ background: true });
      if (selectedJobId) {
        void loadDetail({ background: true });
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [
    shouldAutoRefresh,
    selectedJobId,
    kind,
    page,
    pageSize,
    statusFilter,
    sortBy,
    sortDirection,
  ]);

  const tabs = useMemo(() => contract?.tabs || [], [contract]);
  const [activeTabKey, setActiveTabKey] = useState<string>(() => tabs[0]?.key || "overview");
  const activeTab = useMemo(
    () => tabs.find((t) => t.key === activeTabKey) || null,
    [tabs, activeTabKey],
  );
  const renderSection = (key: string) => {
    const section = findContractSection(contract, key);
    if (!section) return null;
    if (section.kind === "stats") {
      const items = buildContractStats(section.stat_cards, detailSource);
      return (
        <StatGrid
          items={items.map((item) => ({
            label: item.label,
            value: String(item.value || 0),
          }))}
        />
      );
    }
    if (section.kind === "table") {
      const table = buildContractTable(section.tables?.[0] || null, detailSource);
      return (
        <DataTable
          columns={table.columns.map((column) => ({
            key: column.key,
            title: column.label,
          }))}
          defaultHiddenColumns={["document_id", "current_version_number", "updated_at"]}
          emptyText="暂无数据"
          rows={table.rows.map((row) =>
            Object.fromEntries(
              table.columns.map((column) => [
                column.key,
                renderJobValue(column, row[column.key]),
              ]),
            ),
          )}
        />
      );
    }
    const items = buildContractFields(section.fields, detailSource);
    return (
      <KeyValueList
        items={items.map((item) => ({
          label: item.label,
          value: renderJobValue(
            {
              key: item.key,
              label: item.label,
              source_path: "",
              value_type: item.valueType,
            },
            item.value,
          ),
        }))}
      />
    );
  };

  return (
    <div className="space-y-6">
      <SectionTitle
        title={kind === "ingest" ? "入库任务" : "删除任务"}
        description={
          kind === "ingest"
            ? "查看 ingest_job 执行状态、关联文档和 chunk 统计。"
            : "查看 delete_job 删除状态、关联文档和被删除 chunk 统计。"
        }
        action={
          <Button onClick={() => void loadList()} size="sm" variant="outline">
            刷新任务
          </Button>
        }
      />

      <Panel>
        <PanelTitle title="筛选与排序" />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
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

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel>
          <PanelTitle title="任务列表" />
          {loading ? (
            <LoadingState />
          ) : records.length ? (
            <>
              <DataTable
                columns={listTable.columns.map((column) => ({
                  key: column.key,
                  title: column.label,
                  headerClassName:
                    column.key === "job_id" ? "min-w-44" : undefined,
                }))}
                defaultHiddenColumns={["updated_at", "chunk_count"]}
                emptyText="暂无任务"
                rows={listTable.rows.map((row) => {
                  const jobId = getJobRecordId(row as JobRecord);
                  return Object.fromEntries(
                    listTable.columns.map((column) => [
                      column.key,
                      renderJobValue(column, row[column.key], {
                        onSelectJob:
                          column.key === "job_id"
                            ? () => setSelectedJobId(jobId)
                            : undefined,
                      }),
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
            </>
          ) : (
            <EmptyState
              description="先执行一次入库或删除操作，再回到这里查看任务详情。"
              title="暂无任务"
            />
          )}
        </Panel>

        <Panel>
          <PanelTitle title="任务详情" />
          {detailLoading ? (
            <LoadingState title="详情加载中..." />
          ) : !detail ? (
            <EmptyState
              description="点击左侧任务 ID 查看详细信息。"
              title="未选择任务"
            />
          ) : (
            <div className="space-y-4">
              {tabs.length ? (
                <>
                  <div className="flex flex-wrap gap-2">
                    {tabs.map((tab) => (
                      <button
                        key={tab.key}
                        className={`rounded-xl border px-3 py-2 text-sm ${activeTabKey === tab.key ? "bg-primary text-primary-foreground" : "bg-background"}`}
                        onClick={() => setActiveTabKey(tab.key)}
                        type="button"
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                  {activeTab?.section_keys.map((k) => (
                    <div key={k}>{renderSection(k)}</div>
                  ))}
                </>
              ) : (
                <>
                  <StatGrid
                    items={statItems.map((item) => ({
                      label: item.label,
                      value: String(item.value || 0),
                    }))}
                  />
                  <KeyValueList
                    items={summaryItems.map((item) => ({
                      label: item.label,
                      value: renderJobValue(
                        {
                          key: item.key,
                          label: item.label,
                          source_path: "",
                          value_type: item.valueType,
                        },
                        item.value,
                      ),
                    }))}
                  />
                  {kind === "ingest" && documentsTable.columns.length ? (
                    <DataTable
                      columns={documentsTable.columns.map((column) => ({
                        key: column.key,
                        title: column.label,
                      }))}
                      defaultHiddenColumns={["document_id", "current_version_number"]}
                      emptyText="暂无关联文档"
                      rows={documentsTable.rows.map((row) =>
                        Object.fromEntries(
                          documentsTable.columns.map((column) => [
                            column.key,
                            renderJobValue(column, row[column.key]),
                          ]),
                        ),
                      )}
                    />
                  ) : null}
                  {kind === "delete" && documentItems.length ? (
                    <KeyValueList
                      items={documentItems.map((item) => ({
                        label: item.label,
                        value: renderJobValue(
                          {
                            key: item.key,
                            label: item.label,
                            source_path: "",
                            value_type: item.valueType,
                          },
                          item.value,
                        ),
                      }))}
                    />
                  ) : null}
                </>
              )}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
};
