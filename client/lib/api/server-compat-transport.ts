import type { CompatEnvelope } from "@/lib/api/compat-types";

const getServerCompatBaseUrl = () => {
  return process.env["LANGGRAPH_API_URL"] || "http://127.0.0.1:2024";
};

export async function postServerCompat<T>(
  path: string,
  body: Record<string, unknown>,
): Promise<CompatEnvelope<T>> {
  try {
    const response = await fetch(`${getServerCompatBaseUrl()}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const payload = (await response.json()) as CompatEnvelope<T>;
    if (!response.ok) {
      return {
        ...payload,
        error: payload.error || payload.detail || "请求失败",
      };
    }

    return payload;
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "请求失败",
    } as CompatEnvelope<T>;
  }
}
