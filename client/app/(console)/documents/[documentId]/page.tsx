import { DocumentDetailPage } from "@/components/console/document-detail-page";
import {
  getServerDocumentDetail,
  getServerPageContract,
  listServerDocumentVersions,
} from "@/lib/serverCompatApi";

const normalizeDocumentId = (value: string) => {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
};

export default async function DocumentDetailRoutePage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  const normalizedDocumentId = normalizeDocumentId(documentId);
  const [contractRes, detailRes, versionRes] = await Promise.all([
    getServerPageContract("document_detail"),
    getServerDocumentDetail(normalizedDocumentId),
    listServerDocumentVersions(normalizedDocumentId, {
      page: 1,
      page_size: 20,
      sort_by: "version_number",
      sort_direction: "desc",
    }),
  ]);
  return (
    <DocumentDetailPage
      documentId={normalizedDocumentId}
      initialContract={contractRes.page_contract || null}
      initialError={contractRes.error || detailRes.error || versionRes.error || null}
      initialRecord={(detailRes.records?.[0] as any) || null}
      initialVersions={(versionRes.records as any[]) || []}
    />
  );
}
