import { JobsPage } from "@/components/console/jobs-page";
import { getServerPageContract, queryServerAdmin } from "@/lib/serverCompatApi";

const getSingleSearchParam = (
  value: string | string[] | undefined,
  fallback = "",
) => (Array.isArray(value) ? value[0] || fallback : value || fallback);

const getPositiveNumber = (
  value: string | string[] | undefined,
  fallback: number,
) => {
  const parsed = Number(getSingleSearchParam(value));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

export default async function IngestJobsRoutePage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const resolvedSearchParams = (await searchParams) || {};
  const page = getPositiveNumber(resolvedSearchParams.page, 1);
  const pageSize = getPositiveNumber(resolvedSearchParams.page_size, 20);
  const statusFilter = getSingleSearchParam(resolvedSearchParams.status_filter);
  const selectedJobIdFromQuery = getSingleSearchParam(resolvedSearchParams.job_id);
  const sortBy =
    getSingleSearchParam(resolvedSearchParams.sort_by, "updated_at") || "updated_at";
  const sortDirection =
    getSingleSearchParam(resolvedSearchParams.sort_direction, "desc") === "asc"
      ? "asc"
      : "desc";

  const [contractRes, listRes] = await Promise.all([
    getServerPageContract("ingest_job"),
    queryServerAdmin("list_ingest_jobs", {
      page,
      page_size: pageSize,
      status_filter: statusFilter || undefined,
      sort_by: sortBy,
      sort_direction: sortDirection,
    }),
  ]);

  const records = ((listRes.records as any[]) || []) as Array<Record<string, any>>;
  const firstJobId = String(records[0]?.job_id || records[0]?.ingest_job_id || "");
  const selectedJobId = records.some(
    (record) =>
      String(record.job_id || record.ingest_job_id || "") === selectedJobIdFromQuery,
  )
    ? selectedJobIdFromQuery
    : firstJobId;
  const detailRes = selectedJobId
    ? await queryServerAdmin("get_ingest_job_detail", { job_id: selectedJobId })
    : null;

  return (
    <JobsPage
      kind="ingest"
      initialContract={contractRes.page_contract || null}
      initialDetail={(detailRes?.records?.[0] as Record<string, any>) || null}
      initialError={contractRes.error || listRes.error || detailRes?.error || null}
      initialPage={page}
      initialPageSize={pageSize}
      initialRecords={records as any[]}
      initialSelectedJobId={selectedJobId}
      initialSortBy={sortBy}
      initialSortDirection={sortDirection}
      initialStatusFilter={statusFilter}
      initialTotal={Number(listRes.total || 0)}
    />
  );
}
