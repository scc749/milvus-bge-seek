import { JobsPage } from "@/components/console/jobs-page";
import {
  getServerDeleteJobDetail,
  getServerPageContract,
  listServerDeleteJobs,
} from "@/lib/serverCompatApi";

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

export default async function DeleteJobsRoutePage({
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
    getServerPageContract("delete_job"),
    listServerDeleteJobs({
      page,
      page_size: pageSize,
      status_filter: statusFilter || undefined,
      sort_by: sortBy,
      sort_direction: sortDirection,
    }),
  ]);

  const records = ((listRes.records as any[]) || []) as Array<Record<string, unknown>>;
  const firstJobId = String(records[0]?.job_id || records[0]?.delete_job_id || "");
  const selectedJobId = records.some(
    (record) =>
      String(record.job_id || record.delete_job_id || "") === selectedJobIdFromQuery,
  )
    ? selectedJobIdFromQuery
    : firstJobId;
  const detailRes = selectedJobId
    ? await getServerDeleteJobDetail(selectedJobId)
    : null;

  return (
    <JobsPage
      kind="delete"
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
