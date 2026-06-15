"use client";

import { createCompatGateway } from "@/lib/api/compat-gateway";
import { requestBrowserCompat } from "@/lib/api/browser-compat-transport";
import type {
  AdminListResponse,
  PageContractResponse,
} from "@/lib/api/compat-types";

const requestBrowserPost = <T>(path: string, body: Record<string, unknown>) =>
  requestBrowserCompat<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });

const compatGateway = createCompatGateway(requestBrowserPost);

export const {
  getPageContract,
  listDocuments,
  getDocumentDetail,
  listDocumentVersions,
  listIngestJobs,
  getIngestJobDetail,
  listDeleteJobs,
  getDeleteJobDetail,
  ingestDocumentSource,
  deleteDocument,
  reindexDocument,
} = compatGateway;

export type { AdminListResponse, PageContractResponse };
