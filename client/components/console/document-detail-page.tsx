"use client";

import Link from "next/link";
import { ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, RefreshCcw, Trash2 } from "lucide-react";

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
} from "@/lib/contracts/page-contract";
import {
  deleteDocument,
  getDocumentDetail,
  getPageContract,
  listDocumentVersions,
  reindexDocument,
} from "@/lib/langgraphApi";

type DetailRecord = {
  document_id: string;
  title?: string;
  source_uri?: string;
  source_type?: string;
  status?: string;
  current_version_number?: number;
  current_chunk_count?: number;
  updated_at?: string;
  replay_source_uri?: string;
  source_storage?: Record<string, unknown>;
  stats?: Record<string, number>;
  recent_versions?: Array<Record<string, unknown>>;
};

const ACTIVE_DETAIL_STATUSES = new Set([
  "created",
  "queued",
  "pending",
  "processing",
  "running",
]);

const isActiveDetailStatus = (value?: string | null) =>
  ACTIVE_DETAIL_STATUSES.has(String(value || "").toLowerCase());

const normalizeDocumentId = (value: string) => {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
};

const renderDetailValue = (field: ContractField, value: unknown): ReactNode => {
  if (field.value_type === "badge") {
    return <StatusBadge value={String(value || "")} />;
  }
  if (field.value_type === "datetime") {
    return value ? new Date(String(value)).toLocaleString() : "-";
  }
  return String(value || "-");
};

export const DocumentDetailPage = ({
  documentId,
  initialRecord = null,
  initialVersions = [],
  initialContract = null,
  initialError = null,
}: {
  documentId: string;
  initialRecord?: DetailRecord | null;
  initialVersions?: Array<Record<string, unknown>>;
  initialContract?: PageContract | null;
  initialError?: string | null;
}) => {
  const normalizedDocumentId = normalizeDocumentId(documentId);
  const [record, setRecord] = useState<DetailRecord | null>(initialRecord);
  const [versions, setVersions] = useState<Array<Record<string, unknown>>>(
    initialVersions,
  );
  const [loading, setLoading] = useState(
    !initialRecord && !initialVersions.length && !initialError,
  );
  const [error, setError] = useState<string | null>(initialError);
  const [contract, setContract] = useState<PageContract | null>(initialContract);
  const skipInitialLoadRef = useRef(
    Boolean(initialRecord || initialVersions.length || initialError || initialContract),
  );
  const [actionState, setActionState] = useState<{
    message?: string;
    error?: string;
    pending?: "delete" | "reindex" | null;
  }>({ pending: null });

  const loadDetail = async ({ background = false }: { background?: boolean } = {}) => {
    if (!background) {
      setLoading(true);
      setError(null);
    }
    try {
      const contractRes = await getPageContract("document_detail");
      setContract(contractRes.page_contract || null);
      const [detailRes, versionRes] = await Promise.all([
        getDocumentDetail(normalizedDocumentId),
        listDocumentVersions(normalizedDocumentId, {
          page: 1,
          page_size: 20,
          sort_by: "version_number",
          sort_direction: "desc",
        }),
      ]);
      if (detailRes.error) {
        setError(detailRes.error);
      }
      setRecord((detailRes.records?.[0] as DetailRecord) || null);
      setVersions((versionRes.records as Array<Record<string, unknown>>) || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "详情加载失败");
    } finally {
      if (!background) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    if (skipInitialLoadRef.current) {
      skipInitialLoadRef.current = false;
      return;
    }
    void loadDetail();
  }, [normalizedDocumentId]);

  const runAction = async (action: "delete" | "reindex") => {
    setActionState({ pending: action });
    try {
      if (action === "delete") {
        const result = await deleteDocument(normalizedDocumentId);
        if (result.error || result.status === "failed") {
          setActionState({
            pending: null,
            error: result.error || "delete 执行失败",
          });
          return;
        }
        setActionState({
          pending: null,
          message: `删除任务已完成：${result.delete_job_id || "-"}`,
        });
      } else {
        const result = await reindexDocument(normalizedDocumentId);
        if (result.error || result.status === "failed") {
          setActionState({
            pending: null,
            error: result.error || "reindex 执行失败",
          });
          return;
        }
        setActionState({
          pending: null,
          message: `重建任务已提交：${result.ingest_job_id || "-"}`,
        });
      }
      await loadDetail();
    } catch (err) {
      setActionState({
        pending: null,
        error: err instanceof Error ? err.message : `${action} 执行失败`,
      });
    }
  };

  const detailSource = useMemo(
    () => ({ records: record ? [record] : [] }),
    [record],
  );
  const versionSource = useMemo(() => ({ records: versions }), [versions]);
  const summarySection = useMemo(
    () => findContractSection(contract, "summary"),
    [contract],
  );
  const statsSection = useMemo(
    () => findContractSection(contract, "stats"),
    [contract],
  );
  const recentVersionsSection = useMemo(
    () => findContractSection(contract, "recent_versions"),
    [contract],
  );
  const versionsSection = useMemo(
    () => findContractSection(contract, "versions_table"),
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
  const recentVersionsTable = useMemo(
    () => buildContractTable(recentVersionsSection?.tables?.[0] || null, detailSource),
    [detailSource, recentVersionsSection],
  );
  const versionsTable = useMemo(
    () => buildContractTable(versionsSection?.tables?.[0] || null, versionSource),
    [versionSource, versionsSection],
  );
  const shouldAutoRefresh = useMemo(
    () =>
      isActiveDetailStatus(record?.status) ||
      versions.some((item) => isActiveDetailStatus(String(item.status || ""))),
    [record?.status, versions],
  );

  useEffect(() => {
    if (!shouldAutoRefresh) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadDetail({ background: true });
    }, 5000);
    return () => window.clearInterval(timer);
  }, [normalizedDocumentId, shouldAutoRefresh]);

  const tabs = useMemo(() => contract?.tabs || [], [contract]);
  const [activeTabKey, setActiveTabKey] = useState<string>(
    () => tabs[0]?.key || "overview",
  );
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
      const table = buildContractTable(section.tables?.[0] || null, key === "versions_table" ? versionSource : detailSource);
      return (
        <Panel>
          <PanelTitle title={section.label} />
          <DataTable
            columns={table.columns.map((column) => ({
              key: column.key,
              title: column.label,
              headerClassName:
                column.key === "title" ? "min-w-56" : undefined,
            }))}
            defaultHiddenColumns={["content_hash"]}
            emptyText="暂无数据"
            rows={table.rows.map((row) =>
              Object.fromEntries(
                table.columns.map((column) => [
                  column.key,
                  renderDetailValue(column, row[column.key]),
                ]),
              ),
            )}
          />
        </Panel>
      );
    }
    const items = buildContractFields(section.fields, detailSource);
    return (
      <Panel>
        <PanelTitle title={section.label} />
        <KeyValueList
          items={items.map((item) => ({
            label: item.label,
            value: renderDetailValue(
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
      </Panel>
    );
  };

  return (
    <div className="space-y-6">
      <SectionTitle
        title="文档详情"
        description="查看当前文档的来源、受控存储位置、版本历史，以及删除和重建操作结果。"
        action={
          <div className="flex flex-wrap gap-2">
            <Button asChild size="sm" variant="outline">
              <Link href="/documents">
                <ArrowLeft className="size-4" />
                返回文档列表
              </Link>
            </Button>
            <Button
              disabled={actionState.pending === "reindex"}
              onClick={() => void runAction("reindex")}
              size="sm"
              variant="outline"
            >
              <RefreshCcw className="size-4" />
              重建索引
            </Button>
            <Button
              disabled={actionState.pending === "delete"}
              onClick={() => void runAction("delete")}
              size="sm"
              variant="destructive"
            >
              <Trash2 className="size-4" />
              删除文档
            </Button>
          </div>
        }
      />

      <ErrorNotice message={error || actionState.error} />
      {actionState.message ? (
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 text-emerald-600 text-sm">
          {actionState.message}
        </div>
      ) : null}

      {loading ? (
        <LoadingState />
      ) : !record ? (
        <EmptyState
          description="请确认 document_id 是否正确，或检查后端文档中心查询是否可用。"
          title="未找到文档"
        />
      ) : (
        <>
          {tabs.length ? (
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
          ) : null}

          {activeTab
            ? activeTab.section_keys.map((k) => <div key={k}>{renderSection(k)}</div>)
            : (
              <>
                <StatGrid
                  items={statItems.map((item) => ({
                    label: item.label,
                    value: String(item.value || 0),
                  }))}
                />
                <Panel>
                  <PanelTitle title={summarySection?.label || record.title || normalizedDocumentId} />
                  <div className="mb-4">
                    <StatusBadge value={record.status} />
                  </div>
                  <KeyValueList
                    items={summaryItems.map((item) => ({
                      label: item.label,
                      value: renderDetailValue(
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
                </Panel>
                {recentVersionsTable.columns.length ? (
                  <Panel>
                    <PanelTitle
                      title={recentVersionsSection?.label || "最近版本"}
                      description="展示文档详情返回的最近版本摘要。"
                    />
                    <DataTable
                      columns={recentVersionsTable.columns.map((column) => ({
                        key: column.key,
                        title: column.label,
                        headerClassName:
                          column.key === "title" ? "min-w-56" : undefined,
                      }))}
                      emptyText="暂无最近版本"
                      rows={recentVersionsTable.rows.map((row) =>
                        Object.fromEntries(
                          recentVersionsTable.columns.map((column) => [
                            column.key,
                            renderDetailValue(column, row[column.key]),
                          ]),
                        ),
                      )}
                    />
                  </Panel>
                ) : null}
                <Panel>
                  <PanelTitle
                    title={versionsSection?.label || "版本列表"}
                    description="展示当前文档的版本、状态和 chunk 数，便于观察重建和替换过程。"
                  />
                  <DataTable
                    columns={versionsTable.columns.map((column) => ({
                      key: column.key,
                      title: column.label,
                      headerClassName:
                        column.key === "title" ? "min-w-56" : undefined,
                    }))}
                    emptyText="暂无版本记录"
                    rows={versionsTable.rows.map((row) =>
                      Object.fromEntries(
                        versionsTable.columns.map((column) => [
                          column.key,
                          renderDetailValue(column, row[column.key]),
                        ]),
                      ),
                    )}
                  />
                </Panel>
              </>
            )}

        </>
      )}
    </div>
  );
};
