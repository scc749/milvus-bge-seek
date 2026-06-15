export type ContractFilter = {
  key: string;
  label: string;
  value_type: string;
  options?: string[];
};

export type ContractSort = {
  field: string;
  label: string;
  default_direction?: string;
};

export type ContractField = {
  key: string;
  label: string;
  source_path: string;
  value_type?: string;
  emphasized?: boolean;
  description?: string;
};

export type ContractStatCard = {
  key: string;
  label: string;
  source_path: string;
  tone?: string;
};

export type ContractTable = {
  key: string;
  label: string;
  source_operation: string;
  columns: ContractField[];
};

export type ContractSection = {
  key: string;
  label: string;
  kind?: string;
  fields?: ContractField[];
  stat_cards?: ContractStatCard[];
  tables?: ContractTable[];
};

export type ContractTab = {
  key: string;
  label: string;
  section_keys: string[];
};

export type PageContract = {
  page_name: string;
  title: string;
  primary_operation: string;
  secondary_operations?: string[];
  default_page_size?: number;
  filters?: ContractFilter[];
  sorts?: ContractSort[];
  list_item_fields?: ContractField[];
  stat_cards?: ContractStatCard[];
  tables?: ContractTable[];
  sections?: ContractSection[];
  tabs?: ContractTab[];
};

export type ContractFieldValue = {
  key: string;
  label: string;
  value: unknown;
  valueType: string;
  emphasized: boolean;
  description?: string;
};

export type ContractStatValue = {
  key: string;
  label: string;
  value: unknown;
  tone: string;
};

type PathSegment = {
  key: string;
  mode: "value" | "index" | "array";
  index?: number;
};

const PATH_SEGMENT_PATTERN = /^([A-Za-z0-9_]+)(?:\[(\d*)\])?$/;

const parsePath = (path: string): PathSegment[] =>
  path
    .split(".")
    .filter(Boolean)
    .map((segment) => {
      const match = PATH_SEGMENT_PATTERN.exec(segment);
      if (!match) {
        return { key: segment, mode: "value" as const };
      }
      const [, key, indexToken] = match;
      if (indexToken === "") {
        return { key, mode: "array" as const };
      }
      if (indexToken !== undefined) {
        return { key, mode: "index" as const, index: Number(indexToken) };
      }
      return { key, mode: "value" as const };
    });

export const resolveContractPath = (source: unknown, path: string): unknown => {
  if (!path) {
    return source;
  }
  let current: unknown = source;
  for (const segment of parsePath(path)) {
    if (current == null || typeof current !== "object") {
      return undefined;
    }
    const value = (current as Record<string, unknown>)[segment.key];
    if (segment.mode === "value") {
      current = value;
      continue;
    }
    if (!Array.isArray(value)) {
      return segment.mode === "array" ? [] : undefined;
    }
    current =
      segment.mode === "array"
        ? value
        : value.at(segment.index ?? 0);
  }
  return current;
};

const getCollectionPath = (path: string): string => {
  const segments = parsePath(path);
  const arrayIndex = segments.findLastIndex((segment) => segment.mode === "array");
  if (arrayIndex === -1) {
    return "";
  }
  return segments
    .slice(0, arrayIndex + 1)
    .map((segment) => {
      if (segment.mode === "array") {
        return `${segment.key}[]`;
      }
      if (segment.mode === "index") {
        return `${segment.key}[${segment.index ?? 0}]`;
      }
      return segment.key;
    })
    .join(".");
};

const stripBasePath = (path: string, basePath: string): string => {
  if (!basePath) {
    return path;
  }
  if (path === basePath) {
    return "";
  }
  return path.startsWith(`${basePath}.`) ? path.slice(basePath.length + 1) : path;
};

export const getFilterOptions = (
  contract: PageContract | null | undefined,
  key: string,
): string[] =>
  contract?.filters?.find((item) => item.key === key)?.options || [];

export const getSortOptions = (
  contract: PageContract | null | undefined,
): Array<{ value: string; label: string; defaultDirection: string }> =>
  (contract?.sorts || []).map((item) => ({
    value: item.field,
    label: item.label,
    defaultDirection: item.default_direction || "desc",
  }));

export const findContractTable = (
  contract: PageContract | null | undefined,
  key?: string,
): ContractTable | null => {
  if (!contract) {
    return null;
  }
  const tables = contract.tables || [];
  if (!tables.length) {
    return null;
  }
  if (!key) {
    return tables[0];
  }
  return tables.find((item) => item.key === key) || null;
};

export const findContractSection = (
  contract: PageContract | null | undefined,
  key: string,
): ContractSection | null =>
  contract?.sections?.find((item) => item.key === key) || null;

export const buildContractFields = (
  fields: ContractField[] | undefined,
  source: unknown,
): ContractFieldValue[] =>
  (fields || []).map((field) => ({
    key: field.key,
    label: field.label,
    value: resolveContractPath(source, field.source_path),
    valueType: field.value_type || "text",
    emphasized: Boolean(field.emphasized),
    description: field.description,
  }));

export const buildContractStats = (
  cards: ContractStatCard[] | undefined,
  source: unknown,
): ContractStatValue[] =>
  (cards || []).map((card) => ({
    key: card.key,
    label: card.label,
    value: resolveContractPath(source, card.source_path),
    tone: card.tone || "default",
  }));

export const buildContractTable = (
  table: ContractTable | null | undefined,
  source: unknown,
): {
  columns: ContractField[];
  rows: Record<string, unknown>[];
} => {
  if (!table || !table.columns.length) {
    return { columns: [], rows: [] };
  }
  const rowPath = getCollectionPath(table.columns[0].source_path);
  const rowItems = resolveContractPath(source, rowPath);
  const rows = Array.isArray(rowItems)
    ? rowItems.map((item) => {
        const record: Record<string, unknown> = {};
        for (const column of table.columns) {
          const relativePath = stripBasePath(column.source_path, rowPath);
          record[column.key] = relativePath ? resolveContractPath(item, relativePath) : item;
        }
        return record;
      })
    : [];
  return {
    columns: table.columns,
    rows,
  };
};
