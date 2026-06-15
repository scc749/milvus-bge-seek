import {
  ComposerAddAttachment,
  ComposerAttachments,
  UserMessageAttachments,
} from "@/components/assistant-ui/attachment";
import { MarkdownText } from "@/components/assistant-ui/markdown-text";
import { ToolFallback } from "@/components/assistant-ui/tool-fallback";
import { TooltipIconButton } from "@/components/assistant-ui/tooltip-icon-button";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChatTurnTrace, RetrievalTraceItem } from "@/lib/chatApi";
import { cn } from "@/lib/utils";
import {
  ActionBarMorePrimitive,
  ActionBarPrimitive,
  AuiIf,
  BranchPickerPrimitive,
  ComposerPrimitive,
  ErrorPrimitive,
  MessagePrimitive,
  SuggestionPrimitive,
  ThreadPrimitive,
  useAuiState,
} from "@assistant-ui/react";
import {
  BrainIcon,
  ArrowDownIcon,
  ArrowUpIcon,
  CheckIcon,
  CheckCircle2Icon,
  ChevronLeftIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  CopyIcon,
  DownloadIcon,
  LoaderCircleIcon,
  MoreHorizontalIcon,
  PencilIcon,
  RefreshCwIcon,
  SearchIcon,
  SparklesIcon,
  SquareIcon,
} from "lucide-react";
import {
  createContext,
  useContext,
  type FC,
} from "react";

type ThreadProps = {
  liveTurnTrace: ChatTurnTrace | null;
  isStreaming: boolean;
};

type AssistantMessageMetadata =
  | {
      custom?: {
        citations?: Array<Record<string, unknown>>;
        turn_trace?: ChatTurnTrace;
      };
    }
  | undefined;

const ThreadTraceContext = createContext<ThreadProps>({
  liveTurnTrace: null,
  isStreaming: false,
});

export const Thread: FC<ThreadProps> = ({ liveTurnTrace, isStreaming }) => {
  return (
    <ThreadTraceContext.Provider value={{ liveTurnTrace, isStreaming }}>
      <ThreadPrimitive.Root
        className="aui-root aui-thread-root @container flex h-full min-h-0 flex-col bg-background"
        style={{
          ["--thread-max-width" as string]: "44rem",
          ["--composer-radius" as string]: "24px",
          ["--composer-padding" as string]: "10px",
        }}
      >
        <ThreadPrimitive.Viewport
          turnAnchor="top"
          className="aui-thread-viewport relative flex min-h-0 flex-1 flex-col overflow-x-auto overflow-y-auto scroll-smooth px-4 pt-4"
        >
          <AuiIf condition={(s) => s.thread.isEmpty}>
            <ThreadWelcome />
          </AuiIf>

          <ThreadPrimitive.Messages>
            {() => <ThreadMessage />}
          </ThreadPrimitive.Messages>

          <ThreadPrimitive.ViewportFooter className="aui-thread-viewport-footer sticky bottom-0 mx-auto mt-auto flex w-full max-w-(--thread-max-width) flex-col gap-4 overflow-visible rounded-t-(--composer-radius) bg-background pb-4 md:pb-6">
            <ThreadScrollToBottom />
            <Composer />
          </ThreadPrimitive.ViewportFooter>
        </ThreadPrimitive.Viewport>
      </ThreadPrimitive.Root>
    </ThreadTraceContext.Provider>
  );
};

const ThreadMessage: FC = () => {
  const role = useAuiState((s) => s.message.role);
  const isEditing = useAuiState((s) => s.message.composer.isEditing);
  if (isEditing) return <EditComposer />;
  if (role === "user") return <UserMessage />;
  return <AssistantMessage />;
};

const extractAssistantMessageMetadata = (message: Record<string, unknown>) => {
  const metadata =
    (message.metadata as AssistantMessageMetadata | undefined) ??
    undefined;
  if (metadata?.custom) {
    return metadata;
  }

  const responseMetadata =
    (message.response_metadata as Record<string, unknown> | undefined) ??
    undefined;
  const citations = Array.isArray(responseMetadata?.citations)
    ? (responseMetadata.citations as Array<Record<string, unknown>>)
    : [];
  const turnTrace =
    responseMetadata?.turn_trace &&
    typeof responseMetadata.turn_trace === "object"
      ? (responseMetadata.turn_trace as ChatTurnTrace)
      : undefined;

  if (!citations.length && !turnTrace) {
    return undefined;
  }

  return {
    custom: {
      citations,
      turn_trace: turnTrace,
    },
  } satisfies AssistantMessageMetadata;
};

const ThreadScrollToBottom: FC = () => {
  return (
    <ThreadPrimitive.ScrollToBottom asChild>
      <TooltipIconButton
        tooltip="Scroll to bottom"
        variant="outline"
        className="aui-thread-scroll-to-bottom absolute -top-12 z-10 self-center rounded-full p-4 disabled:invisible dark:border-border dark:bg-background dark:hover:bg-accent"
      >
        <ArrowDownIcon />
      </TooltipIconButton>
    </ThreadPrimitive.ScrollToBottom>
  );
};

const ThreadWelcome: FC = () => {
  return (
    <div className="aui-thread-welcome-root mx-auto my-auto flex w-full max-w-(--thread-max-width) grow flex-col">
      <div className="aui-thread-welcome-center flex w-full grow flex-col items-center justify-center">
        <div className="aui-thread-welcome-message flex size-full flex-col justify-center px-4">
          <h1 className="aui-thread-welcome-message-inner fade-in slide-in-from-bottom-1 animate-in fill-mode-both font-semibold text-2xl duration-200">
            Hello there!
          </h1>
          <p className="aui-thread-welcome-message-inner fade-in slide-in-from-bottom-1 animate-in fill-mode-both text-muted-foreground text-xl delay-75 duration-200">
            How can I help you today?
          </p>
        </div>
      </div>
      <ThreadSuggestions />
    </div>
  );
};

const ThreadSuggestions: FC = () => {
  return (
    <div className="aui-thread-welcome-suggestions grid w-full @md:grid-cols-2 gap-2 pb-4">
      <ThreadPrimitive.Suggestions>
        {() => <ThreadSuggestionItem />}
      </ThreadPrimitive.Suggestions>
    </div>
  );
};

const ThreadSuggestionItem: FC = () => {
  return (
    <div className="aui-thread-welcome-suggestion-display fade-in slide-in-from-bottom-2 @md:nth-[n+3]:block nth-[n+3]:hidden animate-in fill-mode-both duration-200">
      <SuggestionPrimitive.Trigger send asChild>
        <Button
          variant="ghost"
          className="aui-thread-welcome-suggestion h-auto w-full @md:flex-col flex-wrap items-start justify-start gap-1 rounded-3xl border bg-background px-4 py-3 text-left text-sm transition-colors hover:bg-muted"
        >
          <SuggestionPrimitive.Title className="aui-thread-welcome-suggestion-text-1 font-medium" />
          <SuggestionPrimitive.Description className="aui-thread-welcome-suggestion-text-2 text-muted-foreground empty:hidden" />
        </Button>
      </SuggestionPrimitive.Trigger>
    </div>
  );
};

const Composer: FC = () => {
  return (
    <ComposerPrimitive.Root className="aui-composer-root relative flex w-full flex-col">
      <ComposerPrimitive.AttachmentDropzone asChild>
        <div
          data-slot="composer-shell"
          className="flex w-full flex-col gap-2 rounded-(--composer-radius) border bg-background p-(--composer-padding) transition-shadow focus-within:border-ring/75 focus-within:ring-2 focus-within:ring-ring/20 data-[dragging=true]:border-ring data-[dragging=true]:border-dashed data-[dragging=true]:bg-accent/50"
        >
          <ComposerAttachments />
          <ComposerPrimitive.Input
            placeholder="Send a message..."
            className="aui-composer-input max-h-32 min-h-10 w-full resize-none bg-transparent px-1.75 py-1 text-sm outline-none placeholder:text-muted-foreground/80"
            rows={1}
            autoFocus
            aria-label="Message input"
          />
          <ComposerAction />
        </div>
      </ComposerPrimitive.AttachmentDropzone>
    </ComposerPrimitive.Root>
  );
};

const ComposerAction: FC = () => {
  return (
    <div className="aui-composer-action-wrapper relative flex items-center justify-between">
      <ComposerAddAttachment />
      <AuiIf condition={(s) => !s.thread.isRunning}>
        <ComposerPrimitive.Send asChild>
          <TooltipIconButton
            tooltip="Send message"
            side="bottom"
            type="button"
            variant="default"
            size="icon"
            className="aui-composer-send size-8 rounded-full"
            aria-label="Send message"
          >
            <ArrowUpIcon className="aui-composer-send-icon size-4" />
          </TooltipIconButton>
        </ComposerPrimitive.Send>
      </AuiIf>
      <AuiIf condition={(s) => s.thread.isRunning}>
        <ComposerPrimitive.Cancel asChild>
          <Button
            type="button"
            variant="default"
            size="icon"
            className="aui-composer-cancel size-8 rounded-full"
            aria-label="Stop generating"
          >
            <SquareIcon className="aui-composer-cancel-icon size-3 fill-current" />
          </Button>
        </ComposerPrimitive.Cancel>
      </AuiIf>
    </div>
  );
};

const MessageError: FC = () => {
  return (
    <MessagePrimitive.Error>
      <ErrorPrimitive.Root className="aui-message-error-root mt-2 rounded-md border border-destructive bg-destructive/10 p-3 text-destructive text-sm dark:bg-destructive/5 dark:text-red-200">
        <ErrorPrimitive.Message className="aui-message-error-message line-clamp-2" />
      </ErrorPrimitive.Root>
    </MessagePrimitive.Error>
  );
};

const AssistantMessage: FC = () => {
  const metadata = useAuiState(
    (s) => extractAssistantMessageMetadata(s.message as Record<string, unknown>),
  );
  const persistedTrace = metadata?.custom?.turn_trace;

  return (
    <MessagePrimitive.Root
      className="aui-assistant-message-root fade-in slide-in-from-bottom-1 relative mx-auto w-full max-w-(--thread-max-width) animate-in py-3 duration-150"
      data-role="assistant"
    >
      <div className="aui-assistant-message-content wrap-break-word px-2 text-foreground leading-relaxed">
        <AssistantTraceSummary trace={persistedTrace ?? null} />
        <MessagePrimitive.Parts>
          {({ part }) => {
            if (part.type === "text") return <MarkdownText />;
            if (part.type === "reasoning") return null;
            if (part.type === "tool-call")
              return part.toolUI ?? <ToolFallback {...part} />;
            return null;
          }}
        </MessagePrimitive.Parts>
        <AssistantCitations />
        <MessageError />
      </div>

      <div className="aui-assistant-message-footer mt-1 ml-2 flex">
        <BranchPicker />
        <AssistantActionBar />
      </div>
    </MessagePrimitive.Root>
  );
};

const AssistantCitations: FC = () => {
  const metadata = useAuiState(
    (s) => extractAssistantMessageMetadata(s.message as Record<string, unknown>),
  );
  const citations = metadata?.custom?.citations ?? [];

  if (!citations.length) {
    return null;
  }

  return (
    <div className="mt-3 rounded-xl border bg-muted/20 px-3 py-3">
      <div className="mb-2 font-medium text-sm">参考知识来源</div>
      <div className="grid gap-2">
        {citations.slice(0, 5).map((citation, index) => (
          <div key={String(citation.chunk_id || citation.document_id || index)} className="rounded-lg border bg-background px-3 py-2 text-xs">
            <div className="font-medium text-sm">
              {String(citation.title || citation.document_id || "未命名文档")}
            </div>
            <div className="break-all text-muted-foreground">
              {String(citation.source_uri || "-")}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const AssistantTraceSummary: FC<{
  trace: ChatTurnTrace | null;
}> = ({ trace }) => {
  if (!trace) {
    return null;
  }

  const hasAnalysisSummary = Boolean(trace.analysis?.intent || trace.analysis?.rewritten_query);
  const hasRetrievalSummary = Boolean(trace.retrieval);

  if (!hasAnalysisSummary && !hasRetrievalSummary) {
    return null;
  }

  return (
    <div className="mb-3 space-y-2">
      {hasAnalysisSummary ? (
        <div className="flex items-start gap-2 rounded-lg border bg-muted/20 px-3 py-2 text-xs">
          <BrainIcon className="mt-0.5 size-3.5 text-primary" />
          <div className="min-w-0 flex-1 text-muted-foreground">
            <span className="font-medium text-foreground">问题分析</span>
            {trace.analysis?.intent ? `：${trace.analysis.intent}` : ""}
            {typeof trace.analysis?.top_k === "number"
              ? `，检索范围 Top-${trace.analysis.top_k}`
              : ""}
            {trace.analysis?.rewritten_query ? (
              <div className="mt-1 break-all">检索表达：{trace.analysis.rewritten_query}</div>
            ) : null}
          </div>
        </div>
      ) : null}
      {hasRetrievalSummary ? (
        <CompactRetrievalCard retrieval={trace.retrieval} />
      ) : null}
    </div>
  );
};

const LiveUserTurnStatus: FC<{
  trace: ChatTurnTrace | null;
}> = ({ trace }) => {
  const analysis = trace?.analysis;
  const retrieval = trace?.retrieval;
  const generation = trace?.generation;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm">
        {analysis?.status === "completed" ? (
          <CheckCircle2Icon className="size-4 text-primary" />
        ) : (
          <LoaderCircleIcon className="size-4 animate-spin text-primary" />
        )}
        <div className="text-foreground">
          {analysis?.status === "completed"
            ? analysis.label || "问题分析完成"
            : analysis?.label || "问题分析中"}
        </div>
      </div>

      {retrieval ? <CompactRetrievalCard retrieval={retrieval} /> : null}

      {generation?.status === "running" ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <LoaderCircleIcon className="size-4 animate-spin text-primary" />
          <span>{generation.label || "答案生成中"}</span>
        </div>
      ) : null}
    </div>
  );
};

const CompactRetrievalCard: FC<{
  retrieval: ChatTurnTrace["retrieval"];
}> = ({ retrieval }) => {
  if (!retrieval) {
    return null;
  }

  const items = retrieval.items || [];
  const totalHits = retrieval.total_hits ?? items.length;
  const matchedDocuments =
    retrieval.matched_documents ?? countMatchedDocuments(items);

  return (
    <div className="rounded-xl border bg-muted/20 px-3 py-3">
      <div className="flex items-start gap-2">
        <SearchIcon className="mt-0.5 size-4 text-primary" />
        <div className="min-w-0 flex-1">
          <div className="font-medium text-sm">
            本次检索了 {matchedDocuments} 篇知识库文档中的 {totalHits} 个片段
          </div>
          {retrieval.query ? (
            <div className="mt-1 break-all text-muted-foreground text-xs">
              检索查询：{retrieval.query}
            </div>
          ) : null}
          {items.length ? (
            <Collapsible className="mt-2">
              <CollapsibleTrigger className="flex items-center gap-1 text-primary text-xs hover:underline">
                <ChevronDownIcon className="size-3.5" />
                展开查看检索内容
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 space-y-2">
                {items.slice(0, 5).map((item, index) => (
                  <div
                    key={String(item.chunk_id || item.document_id || index)}
                    className="rounded-lg border bg-background px-3 py-2"
                  >
                    <div className="font-medium text-sm">
                      {item.title || item.document_id || "未命名文档"}
                    </div>
                    <div className="break-all text-muted-foreground text-xs">
                      {item.source_uri || "-"}
                    </div>
                    {item.snippet ? (
                      <div className="mt-1 text-xs leading-relaxed">
                        {item.snippet}
                      </div>
                    ) : null}
                  </div>
                ))}
              </CollapsibleContent>
            </Collapsible>
          ) : null}
        </div>
      </div>
    </div>
  );
};

const countMatchedDocuments = (items: RetrievalTraceItem[]) => {
  return new Set(
    items
      .map((item) => item.document_id)
      .filter((value): value is string => Boolean(value)),
  ).size;
};

const AssistantActionBar: FC = () => {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      autohideFloat="single-branch"
      className="aui-assistant-action-bar-root col-start-3 row-start-2 -ml-1 flex gap-1 text-muted-foreground data-floating:absolute data-floating:rounded-md data-floating:border data-floating:bg-background data-floating:p-1 data-floating:shadow-sm"
    >
      <ActionBarPrimitive.Copy asChild>
        <TooltipIconButton tooltip="Copy">
          <AuiIf condition={(s) => s.message.isCopied}>
            <CheckIcon />
          </AuiIf>
          <AuiIf condition={(s) => !s.message.isCopied}>
            <CopyIcon />
          </AuiIf>
        </TooltipIconButton>
      </ActionBarPrimitive.Copy>
      <ActionBarPrimitive.Reload asChild>
        <TooltipIconButton tooltip="Refresh">
          <RefreshCwIcon />
        </TooltipIconButton>
      </ActionBarPrimitive.Reload>
      <ActionBarMorePrimitive.Root>
        <ActionBarMorePrimitive.Trigger asChild>
          <TooltipIconButton
            tooltip="More"
            className="data-[state=open]:bg-accent"
          >
            <MoreHorizontalIcon />
          </TooltipIconButton>
        </ActionBarMorePrimitive.Trigger>
        <ActionBarMorePrimitive.Content
          side="bottom"
          align="start"
          className="aui-action-bar-more-content z-50 min-w-32 overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
        >
          <ActionBarPrimitive.ExportMarkdown asChild>
            <ActionBarMorePrimitive.Item className="aui-action-bar-more-item flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground">
              <DownloadIcon className="size-4" />
              Export as Markdown
            </ActionBarMorePrimitive.Item>
          </ActionBarPrimitive.ExportMarkdown>
        </ActionBarMorePrimitive.Content>
      </ActionBarMorePrimitive.Root>
    </ActionBarPrimitive.Root>
  );
};

const UserMessage: FC = () => {
  const { liveTurnTrace, isStreaming } = useContext(ThreadTraceContext);
  const isLatestUserMessage = useAuiState((s) => {
    const thread = s.thread as unknown as {
      messages?: ReadonlyArray<Record<string, unknown>>;
    };
    const messages = Array.isArray(thread?.messages)
      ? (thread.messages ?? [])
      : [];
    const lastUser = [...messages]
      .reverse()
      .find((message) => {
        const role = message.role ?? message.type;
        return role === "user" || role === "human";
      });
    if (lastUser?.id && s.message.id) {
      return lastUser.id === s.message.id;
    }
    const currentContent = JSON.stringify(s.message.content ?? "");
    const lastContent = JSON.stringify(lastUser?.content ?? "");
    return currentContent === lastContent;
  });

  return (
    <MessagePrimitive.Root
      className="aui-user-message-root fade-in slide-in-from-bottom-1 mx-auto grid w-full max-w-(--thread-max-width) animate-in auto-rows-auto grid-cols-[minmax(72px,1fr)_auto] content-start gap-y-2 px-2 py-3 duration-150 [&:where(>*)]:col-start-2"
      data-role="user"
    >
      <UserMessageAttachments />

      <div className="aui-user-message-content-wrapper relative col-start-2 min-w-0">
        <div className="aui-user-message-content wrap-break-word peer rounded-2xl bg-muted px-4 py-2.5 text-foreground empty:hidden">
          <MessagePrimitive.Parts />
        </div>
        <div className="aui-user-action-bar-wrapper absolute top-1/2 left-0 -translate-x-full -translate-y-1/2 pr-2 peer-empty:hidden">
          <UserActionBar />
        </div>
        {isStreaming && isLatestUserMessage ? (
          <div className="mt-3">
            <LiveUserTurnStatus trace={liveTurnTrace} />
          </div>
        ) : null}
      </div>

      <BranchPicker className="aui-user-branch-picker col-span-full col-start-1 row-start-3 -mr-1 justify-end" />
    </MessagePrimitive.Root>
  );
};

const UserActionBar: FC = () => {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      className="aui-user-action-bar-root flex flex-col items-end"
    >
      <ActionBarPrimitive.Edit asChild>
        <TooltipIconButton tooltip="Edit" className="aui-user-action-edit p-4">
          <PencilIcon />
        </TooltipIconButton>
      </ActionBarPrimitive.Edit>
    </ActionBarPrimitive.Root>
  );
};

const EditComposer: FC = () => {
  return (
    <MessagePrimitive.Root className="aui-edit-composer-wrapper mx-auto flex w-full max-w-(--thread-max-width) flex-col px-2 py-3">
      <ComposerPrimitive.Root className="aui-edit-composer-root ml-auto flex w-full max-w-[85%] flex-col rounded-2xl bg-muted">
        <ComposerPrimitive.Input
          className="aui-edit-composer-input min-h-14 w-full resize-none bg-transparent p-4 text-foreground text-sm outline-none"
          autoFocus
        />
        <div className="aui-edit-composer-footer mx-3 mb-3 flex items-center gap-2 self-end">
          <ComposerPrimitive.Cancel asChild>
            <Button variant="ghost" size="sm">
              Cancel
            </Button>
          </ComposerPrimitive.Cancel>
          <ComposerPrimitive.Send asChild>
            <Button size="sm">Update</Button>
          </ComposerPrimitive.Send>
        </div>
      </ComposerPrimitive.Root>
    </MessagePrimitive.Root>
  );
};

const BranchPicker: FC<BranchPickerPrimitive.Root.Props> = ({
  className,
  ...rest
}) => {
  return (
    <BranchPickerPrimitive.Root
      hideWhenSingleBranch
      className={cn(
        "aui-branch-picker-root mr-2 -ml-2 inline-flex items-center text-muted-foreground text-xs",
        className,
      )}
      {...rest}
    >
      <BranchPickerPrimitive.Previous asChild>
        <TooltipIconButton tooltip="Previous">
          <ChevronLeftIcon />
        </TooltipIconButton>
      </BranchPickerPrimitive.Previous>
      <span className="aui-branch-picker-state font-medium">
        <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
      </span>
      <BranchPickerPrimitive.Next asChild>
        <TooltipIconButton tooltip="Next">
          <ChevronRightIcon />
        </TooltipIconButton>
      </BranchPickerPrimitive.Next>
    </BranchPickerPrimitive.Root>
  );
};
