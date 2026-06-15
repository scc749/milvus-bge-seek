import { DocumentsPage } from "@/components/console/documents-page";
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

export default async function DocumentsRoutePage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const resolvedSearchParams = (await searchParams) || {};
  const page = getPositiveNumber(resolvedSearchParams.page, 1);
  const pageSize = getPositiveNumber(resolvedSearchParams.page_size, 20);
  const query = getSingleSearchParam(resolvedSearchParams.query);
  const statusFilter = getSingleSearchParam(resolvedSearchParams.status_filter);
  const sourceTypeFilter = getSingleSearchParam(
    resolvedSearchParams.source_type_filter,
  );
  const sortBy =
    getSingleSearchParam(resolvedSearchParams.sort_by, "updated_at") || "updated_at";
  const sortDirection =
    getSingleSearchParam(resolvedSearchParams.sort_direction, "desc") === "asc"
      ? "asc"
      : "desc";

  const [contractRes, listRes] = await Promise.all([
    getServerPageContract("document_list"),
    queryServerAdmin("list_documents", {
      page,
      page_size: pageSize,
      query: query || undefined,
      status_filter: statusFilter || undefined,
      source_type_filter: sourceTypeFilter || undefined,
      sort_by: sortBy,
      sort_direction: sortDirection,
    }),
  ]);

  return (
    <DocumentsPage
      initialContract={contractRes.page_contract || null}
      initialError={contractRes.error || listRes.error || null}
      initialPage={page}
      initialPageSize={pageSize}
      initialQuery={query}
      initialRecords={(listRes.records as any[]) || []}
      initialSortBy={sortBy}
      initialSortDirection={sortDirection}
      initialSourceTypeFilter={sourceTypeFilter}
      initialStatusFilter={statusFilter}
      initialTotal={Number(listRes.total || 0)}
    />
  );
}
