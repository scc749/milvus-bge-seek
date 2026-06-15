"use client";

import type { CompatEnvelope } from "@/lib/api/compat-types";

const getBrowserCompatBaseUrl = () => {
  if (process.env["NEXT_PUBLIC_LANGGRAPH_API_URL"]) {
    return process.env["NEXT_PUBLIC_LANGGRAPH_API_URL"];
  }
  if (typeof window === "undefined") {
    return "/api";
  }
  return new URL("/api", window.location.href).href;
};

export const requestBrowserCompat = async <T>(
  path: string,
  init?: RequestInit,
): Promise<CompatEnvelope<T>> => {
  const response = await fetch(`${getBrowserCompatBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });

  const rawText = await response.text();
  let payload: CompatEnvelope<T>;
  try {
    payload = rawText
      ? (JSON.parse(rawText) as CompatEnvelope<T>)
      : ({} as CompatEnvelope<T>);
  } catch {
    payload = {
      error: rawText || response.statusText || "请求失败",
    } as CompatEnvelope<T>;
  }
  if (!response.ok) {
    throw new Error(payload.error || payload.detail || "请求失败");
  }

  return payload;
};
