"use client";

import { Button } from "@/components/ui/button";
import {
  AssistantRuntimeProvider,
  useRemoteThreadListRuntime,
} from "@assistant-ui/react";
import { useLangGraphRuntime } from "@assistant-ui/react-langgraph";
import { createAssistantStream } from "assistant-stream";
import {
  ChevronLeft,
  ChevronRight,
  Database,
  MessageSquarePlus,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  applyProgressEventToTrace,
  ChatTurnTrace,
  CompatThreadSummary,
  createThread,
  deleteThread,
  getThreadState,
  listThreads,
  sendMessage,
  updateThread,
} from "@/lib/chatApi";
import { Thread } from "@/components/assistant-ui/thread";

const formatThreadTitle = (rawTitle?: string, fallback?: string) => {
  const normalized = (rawTitle || fallback || "新对话")
    .replace(/\s+/g, " ")
    .trim();
  return normalized.slice(0, 40) || "新对话";
};

const extractThreadTitleFromMessages = (
  messages: readonly { content: unknown }[],
) => {
  for (const message of messages) {
    const text = Array.isArray(message.content)
      ? message.content
          .filter(
            (item): item is { type: string; text?: string } =>
              typeof item === "object" && item !== null && "type" in item,
          )
          .filter((item) => item.type === "text")
          .map((item) => item.text || "")
          .join(" ")
      : typeof message.content === "string"
        ? message.content
        : "";

    const normalized = text.replace(/\s+/g, " ").trim();
    if (normalized) {
      return normalized.slice(0, 60);
    }
  }

  return "新对话";
};

export function Assistant() {
  const [currentThreadId, setCurrentThreadId] = useState<string | undefined>(undefined);
  const [liveTurnTrace, setLiveTurnTrace] = useState<ChatTurnTrace | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isThreadSelectionReady, setIsThreadSelectionReady] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem("rag-assistant-thread-id");
    if (stored) {
      setCurrentThreadId(stored);
    }
    setIsSidebarCollapsed(
      window.localStorage.getItem("rag-assistant-sidebar-collapsed") === "true",
    );
    setIsThreadSelectionReady(true);
  }, []);

  useEffect(() => {
    if (currentThreadId) {
      window.localStorage.setItem("rag-assistant-thread-id", currentThreadId);
    } else {
      window.localStorage.removeItem("rag-assistant-thread-id");
    }
  }, [currentThreadId]);

  const adapter = useMemo(
    () => ({
      list: async () => {
        const threads = await listThreads();
        const uniqueThreads = Array.from(
          new Map(threads.map((thread) => [thread.thread_id, thread])).values(),
        );
        return {
          threads: uniqueThreads.map((thread) => ({
            remoteId: thread.thread_id,
            externalId: thread.thread_id,
            title: formatThreadTitle(thread.title, thread.last_message),
            status: thread.status || "regular",
          })),
        };
      },
      rename: async (remoteId: string, newTitle: string) => {
        await updateThread(remoteId, { title: newTitle });
      },
      archive: async (remoteId: string) => {
        await updateThread(remoteId, { status: "archived" });
      },
      unarchive: async (remoteId: string) => {
        await updateThread(remoteId, { status: "regular" });
      },
      delete: async (remoteId: string) => {
        await deleteThread(remoteId);
        if (currentThreadId === remoteId) {
          setCurrentThreadId(undefined);
        }
      },
      initialize: async () => {
        const { thread_id } = await createThread();
        setCurrentThreadId(thread_id);
        return {
          remoteId: thread_id,
          externalId: thread_id,
        };
      },
      fetch: async (threadId: string) => {
        const threads = await listThreads();
        const thread = threads.find((item) => item.thread_id === threadId);
        return {
          remoteId: threadId,
          externalId: threadId,
          title: formatThreadTitle(thread?.title, thread?.last_message || "历史会话"),
          status: thread?.status || ("regular" as const),
        };
      },
      generateTitle: async (remoteId: string, messages: readonly { content: unknown }[]) => {
        const rawText = extractThreadTitleFromMessages(messages);
        try {
          await updateThread(remoteId, { title: rawText });
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "更新标题失败";
          if (!message.includes("Thread not found")) {
            throw error;
          }
        }
        return createAssistantStream((controller) => {
          controller.appendText(rawText);
          controller.close();
        });
      },
    }),
    [currentThreadId],
  );

  if (!isThreadSelectionReady) {
    return <div className="h-full bg-background" />;
  }

  return (
    <AssistantRuntimeView
      adapter={adapter}
      currentThreadId={currentThreadId}
      isSidebarCollapsed={isSidebarCollapsed}
      isStreaming={isStreaming}
      liveTurnTrace={liveTurnTrace}
      setCurrentThreadId={setCurrentThreadId}
      setIsSidebarCollapsed={setIsSidebarCollapsed}
      setIsStreaming={setIsStreaming}
      setLiveTurnTrace={setLiveTurnTrace}
    />
  );
}

function AssistantRuntimeView({
  adapter,
  currentThreadId,
  isSidebarCollapsed,
  isStreaming,
  liveTurnTrace,
  setCurrentThreadId,
  setIsSidebarCollapsed,
  setIsStreaming,
  setLiveTurnTrace,
}: {
  adapter: any;
  currentThreadId: string | undefined;
  isSidebarCollapsed: boolean;
  isStreaming: boolean;
  liveTurnTrace: ChatTurnTrace | null;
  setCurrentThreadId: (threadId: string | undefined) => void;
  setIsSidebarCollapsed: (value: boolean | ((prev: boolean) => boolean)) => void;
  setIsStreaming: (value: boolean) => void;
  setLiveTurnTrace: (
    value:
      | ChatTurnTrace
      | null
      | ((prev: ChatTurnTrace | null) => ChatTurnTrace | null),
  ) => void;
}) {
  const [threadSummaries, setThreadSummaries] = useState<CompatThreadSummary[]>([]);
  const reloadThreads = useCallback(async () => {
    const threads = await listThreads();
    const uniqueThreads = Array.from(
      new Map(threads.map((thread) => [thread.thread_id, thread])).values(),
    );
    setThreadSummaries(uniqueThreads);
    if (
      currentThreadId &&
      !uniqueThreads.some((thread) => thread.thread_id === currentThreadId)
    ) {
      setCurrentThreadId(undefined);
    }
  }, [currentThreadId, setCurrentThreadId]);

  useEffect(() => {
    void reloadThreads();
  }, [reloadThreads]);

  const runtime = useRemoteThreadListRuntime({
    threadId: currentThreadId,
    adapter,
    runtimeHook: () =>
      useLangGraphRuntime({
        stream: async function* (messages, { initialize, command }) {
          const { externalId } = await initialize();
          if (!externalId) throw new Error("Thread not found");
          setIsStreaming(true);
          setLiveTurnTrace({
            analysis: {
              status: "running",
              label: "问题分析中",
            },
          });
          const generator = await sendMessage({
            threadId: externalId,
            messages,
            command,
            onProgressEvent: (event) => {
              setLiveTurnTrace((prev) => applyProgressEventToTrace(prev || {}, event));
            },
          });
          try {
            for await (const event of generator) {
              if (event.event === "metadata" && event.data && typeof event.data === "object") {
                const threadId = (event.data as { thread_id?: string }).thread_id;
                if (threadId) setCurrentThreadId(threadId);
              }
              yield event;
            }
          } finally {
            setIsStreaming(false);
            setLiveTurnTrace(null);
            void reloadThreads();
          }
        },
        load: async (externalId) => {
          const state = await getThreadState(externalId);
          return {
            messages: state.values.messages,
          };
        },
      }),
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div
        className={`grid h-full min-h-0 overflow-hidden transition-all duration-200 ${
          isSidebarCollapsed
            ? "grid-cols-[72px_1fr]"
            : "grid-cols-[280px_1fr]"
        }`}
      >
        <aside className="min-h-0 border-r bg-muted/20">
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between border-b px-4 py-3">
              {isSidebarCollapsed ? null : (
                <div className="min-w-0">
                  <div className="font-medium text-sm">历史会话</div>
                  <div className="text-muted-foreground text-xs">
                    基于 PostgreSQL 持久化
                  </div>
                </div>
              )}
              <div className="flex items-center gap-2">
                <Button
                  className="size-8 rounded-full"
                  onClick={() => setCurrentThreadId(undefined)}
                  size="icon"
                  variant="outline"
                >
                  <MessageSquarePlus className="size-4" />
                </Button>
                <Button
                  className="size-8 rounded-full"
                  onClick={() => {
                    setIsSidebarCollapsed((current) => {
                      const next = !current;
                      window.localStorage.setItem(
                        "rag-assistant-sidebar-collapsed",
                        String(next),
                      );
                      return next;
                    });
                  }}
                  size="icon"
                  variant="outline"
                >
                  {isSidebarCollapsed ? (
                    <ChevronRight className="size-4" />
                  ) : (
                    <ChevronLeft className="size-4" />
                  )}
                </Button>
              </div>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-2">
              {threadSummaries.map((thread) => (
                <AssistantThreadListItem
                  key={thread.thread_id}
                  activeThreadId={currentThreadId}
                  collapsed={isSidebarCollapsed}
                  onDelete={async (threadId) => {
                    await deleteThread(threadId);
                    if (currentThreadId === threadId) {
                      setCurrentThreadId(undefined);
                    }
                    await reloadThreads();
                  }}
                  onSelect={setCurrentThreadId}
                  thread={thread}
                />
              ))}
            </div>
          </div>
        </aside>

        <div className="min-h-0 overflow-hidden">
          <Thread isStreaming={isStreaming} liveTurnTrace={liveTurnTrace} />
        </div>
      </div>
    </AssistantRuntimeProvider>
  );
}

function AssistantThreadListItem({
  activeThreadId,
  collapsed,
  onDelete,
  onSelect,
  thread,
}: {
  activeThreadId: string | undefined;
  collapsed: boolean;
  onDelete: (threadId: string) => Promise<void>;
  onSelect: (threadId: string | undefined) => void;
  thread: CompatThreadSummary;
}) {
  const isActive = activeThreadId === thread.thread_id;

  return (
    <div
      className={`group mb-2 block rounded-xl border p-2 text-sm shadow-xs transition-colors ${
        isActive
          ? "border-primary/40 bg-primary/5"
          : "bg-background hover:bg-accent/40"
      }`}
    >
      <div className={`flex gap-2 ${collapsed ? "items-center justify-center" : "items-start"}`}>
        <button
          className={`min-w-0 text-left ${collapsed ? "flex items-center justify-center" : "flex-1"}`}
          type="button"
          onClick={() => onSelect(thread.thread_id)}
        >
          <div className={`flex items-center gap-2 ${collapsed ? "justify-center" : ""}`}>
            <Database className="size-3.5 text-muted-foreground" />
            {collapsed ? null : (
              <div className="truncate font-medium">
                {formatThreadTitle(thread.title, thread.last_message)}
              </div>
            )}
          </div>
          {collapsed ? null : (
            <div className="truncate pt-1 text-muted-foreground text-xs">
              {thread.last_message || thread.updated_at || "暂无消息"}
            </div>
          )}
        </button>
        <div className={collapsed ? "hidden" : ""}>
          <Button
            className="opacity-0 transition-opacity group-hover:opacity-100"
            size="icon"
            type="button"
            variant="ghost"
            onClick={() => void onDelete(thread.thread_id)}
          >
            <Trash2 className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
