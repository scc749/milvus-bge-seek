import type { PageContract } from "@/lib/contracts/page-contract";

export type CompatEnvelope<T> = T & {
  error?: string;
  detail?: string;
};

export type AdminListResponse = {
  operation: string;
  count?: number;
  records: Record<string, unknown>[];
  page?: number;
  page_size?: number;
  total?: number;
  sort?: Record<string, unknown>;
  filters?: Record<string, unknown>;
  meta?: Record<string, unknown>;
  error?: string;
};

export type PageContractResponse = {
  operation: "get_page_contract";
  page_contract?: PageContract;
  error?: string;
  available_pages?: string[];
};

export type IngestResponse = {
  source_uri?: string;
  source_name?: string;
  ingest_job_id?: string;
  registered_document_ids?: string[];
  registered_version_ids?: string[];
  chunk_count?: number;
  cleaned_chunk_count?: number;
  upserted_count?: number;
  status?: string;
  message?: string;
  error?: string;
  source_storage?: Record<string, unknown>;
};

export type DeleteResponse = {
  document_id?: string;
  delete_job_id?: string;
  deleted_chunk_count?: number;
  status?: string;
  error?: string;
};

export type ReindexResponse = {
  source_uri?: string;
  ingest_job_id?: string;
  registered_document_ids?: string[];
  status?: string;
  error?: string;
  source_storage?: Record<string, unknown>;
};
