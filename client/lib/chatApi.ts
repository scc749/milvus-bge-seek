import {
  LangChainMessage,
  LangGraphCommand,
} from "@assistant-ui/react-langgraph";
import { requestBrowserCompat } from "@/lib/api/browser-compat-transport";

type CompatStoredMessage = {
  id?: string;
  role?: "user" | "assistant" | "system";
  type?: "human" | "ai" | "system" | "tool";
  content: string | Array<Record<string, unknown>>;
  additional_kwargs?: Record<string, unknown>;
  response_metadata?: Record<string, unknown>;
};

type CompatThreadResponse = {
  thread_id: string;
  title?: string;
  status?: "regular" | "archived";
  messages?: CompatStoredMessage[];
};

export type CompatThreadSummary = {
  thread_id: string;
  title?: string;
  status?: "regular" | "archived";
  updated_at?: string;
  last_message?: string;
};

export type RetrievalTraceItem = {
  document_id?: string;
  chunk_id?: string;
  title?: string;
  source_uri?: string;
  score?: number;
  snippet?: string;
};

export type ChatTurnTrace = {
  analysis?: {
    status: "running" | "completed";
    label: string;
    intent?: string;
    top_k?: number;
    need_rewrite?: boolean;
    need_rerank?: boolean;
    rewritten_query?: string;
  };
  retrieval?: {
    status: "running" | "completed";
    label: string;
    query?: string;
    total_hits?: number;
    matched_documents?: number;
    items: RetrievalTraceItem[];
  };
  generation?: {
    status: "running" | "completed";
    label: string;
  };
};

const buildAssistantUiMetadata = (
  responseMetadata?: Record<string, unknown>,
): { custom: { citations: Array<Record<string, unknown>>; turn_trace?: ChatTurnTrace } } => {
  const citations = Array.isArray(responseMetadata?.citations)
    ? (responseMetadata?.citations as Array<Record<string, unknown>>)
    : [];
  const turnTrace =
    responseMetadata?.turn_trace &&
    typeof responseMetadata.turn_trace === "object"
      ? (responseMetadata.turn_trace as ChatTurnTrace)
      : undefined;

  return {
    custom: {
      citations,
      turn_trace: turnTrace,
    },
  };
};

export type ChatProgressEvent =
  | {
      type: "stage";
      stage: "analysis" | "retrieval" | "generation";
      status: "running" | "completed";
      label: string;
      query?: string;
    }
  | {
      type: "analysis";
      stage: "analysis";
      status: "completed";
      label: string;
      intent: string;
      top_k: number;
      need_rewrite: boolean;
      need_rerank: boolean;
      rewritten_query?: string;
    }
  | {
      type: "retrieval";
      stage: "retrieval";
      status: "completed";
      label: string;
      query: string;
      total_hits?: number;
      matched_documents?: number;
      items: RetrievalTraceItem[];
    };

export const applyProgressEventToTrace = (
  trace: ChatTurnTrace,
  event: ChatProgressEvent,
): ChatTurnTrace => {
  if (event.type === "stage") {
    return {
      ...trace,
      [event.stage]: {
        ...(trace[event.stage] || {}),
        status: event.status,
        label: event.label,
        ...(event.stage === "retrieval" ? { items: trace.retrieval?.items || [] } : {}),
      },
    };
  }

  if (event.type === "analysis") {
    return {
      ...trace,
      analysis: {
        status: event.status,
        label: event.label,
        intent: event.intent,
        top_k: event.top_k,
        need_rewrite: event.need_rewrite,
        need_rerank: event.need_rerank,
        rewritten_query: event.rewritten_query,
      },
    };
  }

  return {
    ...trace,
    retrieval: {
      status: event.status,
      label: event.label,
      query: event.query,
      total_hits: event.total_hits ?? event.items.length,
      matched_documents: event.matched_documents,
      items: event.items,
    },
  };
};

const normalizeMessage = (message: CompatStoredMessage): LangChainMessage => {
  if (message.type === "human" || message.role === "user") {
    return {
      id: message.id,
      type: "human",
      content: message.content as any,
      additional_kwargs: message.additional_kwargs,
    } as any;
  }

  if (message.type === "system" || message.role === "system") {
    return {
      id: message.id,
      type: "system",
      content: message.content as any,
      additional_kwargs: message.additional_kwargs,
    } as any;
  }

  const normalizedMetadata = buildAssistantUiMetadata(message.response_metadata);
  return {
    id: message.id,
    type: "ai",
    content: message.content as any,
    additional_kwargs: {
      ...(message.additional_kwargs || {}),
      metadata: {
        ...(((message.additional_kwargs?.metadata as Record<string, unknown>) || {}) as Record<
          string,
          unknown
        >),
        ...normalizedMetadata,
      },
    },
    response_metadata: message.response_metadata,
    metadata: normalizedMetadata,
  } as any;
};

const extractLatestUserText = (messages?: LangChainMessage[]) => {
  const latestHuman = [...(messages || [])]
    .reverse()
    .find((message) => message.type === "human");

  if (!latestHuman) {
    return null;
  }

  if (typeof latestHuman.content === "string") {
    return latestHuman.content.trim();
  }

  const text = latestHuman.content
    .filter((item) => item.type === "text")
    .map((item) => ("text" in item ? item.text : ""))
    .join("")
    .trim();

  return text || null;
};

export const createThread = async () => {
  return requestBrowserCompat<{ thread_id: string }>("/compat/assistant/threads", {
    method: "POST",
    body: JSON.stringify({}),
  });
};

export const listThreads = async (): Promise<CompatThreadSummary[]> => {
  const result = await requestBrowserCompat<{ threads?: CompatThreadSummary[] }>(
    "/compat/assistant/threads",
    { method: "GET" },
  );
  return result.threads || [];
};

export const updateThread = async (
  threadId: string,
  payload: { title?: string; status?: "regular" | "archived" },
) => {
  return requestBrowserCompat<CompatThreadResponse>(
    `/compat/assistant/threads/${threadId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
};

export const deleteThread = async (threadId: string) => {
  return requestBrowserCompat<{ status: string }>(
    `/compat/assistant/threads/${threadId}`,
    {
      method: "DELETE",
    },
  );
};

const parseNdjsonStream = async function* (
  response: Response,
): AsyncGenerator<Record<string, unknown>> {
  if (!response.body) {
    return;
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      yield JSON.parse(trimmed) as Record<string, unknown>;
    }
  }
  const tail = buffer.trim();
  if (tail) {
    yield JSON.parse(tail) as Record<string, unknown>;
  }
};

export const getThreadState = async (
  threadId: string,
): Promise<{ values: { messages: LangChainMessage[] } }> => {
  const result = await requestBrowserCompat<CompatThreadResponse>(
    `/compat/assistant/threads/${threadId}`,
    {
      method: "GET",
    },
  );

  return {
    values: {
      messages: (result.messages || []).map(normalizeMessage),
    },
  };
};

export const sendMessage = async (params: {
  threadId: string;
  messages?: LangChainMessage[];
  command?: LangGraphCommand | undefined;
  onProgressEvent?: (event: ChatProgressEvent) => void;
}) => {
  const message =
    extractLatestUserText(params.messages) || params.command?.resume?.trim();

  if (!message) {
    throw new Error("当前兼容聊天接口只支持文本消息。");
  }

  return (async function* () {
    const response = await fetch("/api/compat/assistant/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        thread_id: params.threadId,
        message,
      }),
    });
    if (!response.ok) {
      throw new Error((await response.text()) || "聊天请求失败");
    }

    for await (const rawEvent of parseNdjsonStream(response)) {
      const event = String(rawEvent.event || "");
      const data = rawEvent.data;
      if (event === "custom" && data && params.onProgressEvent) {
        params.onProgressEvent(data as ChatProgressEvent);
        continue;
      }
      if (event === "metadata" || event === "messages") {
        yield {
          event,
          data,
        };
        continue;
      }
      if (event === "values" && data && typeof data === "object") {
        const values = data as CompatThreadResponse & { citations?: unknown[] };
        yield {
          event: "values",
          data: {
            thread_id: values.thread_id,
            citations: values.citations || [],
            messages: (values.messages || []).map(normalizeMessage),
          },
        };
      }
    }
  })();
};
