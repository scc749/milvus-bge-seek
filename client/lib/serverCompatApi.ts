import { createCompatGateway } from "@/lib/api/compat-gateway";
import type { AdminListResponse } from "@/lib/api/compat-types";
import { postServerCompat } from "@/lib/api/server-compat-transport";

const compatGateway = createCompatGateway(postServerCompat);

export const {
  getPageContract: getServerPageContract,
  getDocumentDetail: getServerDocumentDetail,
  listDocumentVersions: listServerDocumentVersions,
  listDeleteJobs: listServerDeleteJobs,
  getDeleteJobDetail: getServerDeleteJobDetail,
  listIngestJobs: listServerIngestJobs,
  getIngestJobDetail: getServerIngestJobDetail,
} = compatGateway;

export const queryServerAdmin = (
  operation: string,
  payload: Record<string, unknown>,
) =>
  postServerCompat<AdminListResponse>("/compat/admin/query", {
    operation,
    payload,
  });
