import type {
  AdminListResponse,
  DeleteResponse,
  IngestResponse,
  PageContractResponse,
  ReindexResponse,
} from "@/lib/api/compat-types";

type CompatRequester = <T>(
  path: string,
  body: Record<string, unknown>,
) => Promise<T>;

export const createCompatGateway = (request: CompatRequester) => ({
  getPageContract(pageName: string) {
    return request<PageContractResponse>("/compat/admin/page-contract", {
      page_name: pageName,
    });
  },

  listDocuments(params: Record<string, unknown>) {
    return request<AdminListResponse>("/compat/admin/query", {
      operation: "list_documents",
      payload: params,
    });
  },

  getDocumentDetail(documentId: string) {
    return request<AdminListResponse>("/compat/admin/query", {
      operation: "get_document_detail",
      payload: { document_id: documentId },
    });
  },

  listDocumentVersions(
    documentId: string,
    params: Record<string, unknown>,
  ) {
    return request<AdminListResponse>("/compat/admin/query", {
      operation: "list_document_versions",
      payload: {
        document_id: documentId,
        ...params,
      },
    });
  },

  listIngestJobs(params: Record<string, unknown>) {
    return request<AdminListResponse>("/compat/admin/query", {
      operation: "list_ingest_jobs",
      payload: params,
    });
  },

  getIngestJobDetail(jobId: string) {
    return request<AdminListResponse>("/compat/admin/query", {
      operation: "get_ingest_job_detail",
      payload: { job_id: jobId },
    });
  },

  listDeleteJobs(params: Record<string, unknown>) {
    return request<AdminListResponse>("/compat/admin/query", {
      operation: "list_delete_jobs",
      payload: params,
    });
  },

  getDeleteJobDetail(jobId: string) {
    return request<AdminListResponse>("/compat/admin/query", {
      operation: "get_delete_job_detail",
      payload: { job_id: jobId },
    });
  },

  ingestDocumentSource(input: Record<string, unknown>) {
    return request<IngestResponse>("/compat/ingest", input);
  },

  deleteDocument(documentId: string) {
    return request<DeleteResponse>("/compat/delete", {
      document_id: documentId,
    });
  },

  reindexDocument(documentId: string) {
    return request<ReindexResponse>("/compat/reindex", {
      document_id: documentId,
    });
  },
});
