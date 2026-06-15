import { Assistant } from "@/app/assistant";
import { SectionTitle } from "@/components/console/console-ui";

export default function AssistantPage() {
  return (
    <div className="flex min-h-0 flex-col gap-6">
      <SectionTitle
        title="助手对话"
        description="使用 assistant-ui 模板对接 LangGraph assistant 图，进行检索问答与调试。"
      />
      <div className="h-[calc(100vh-12rem)] min-h-0 overflow-hidden rounded-2xl border bg-card shadow-sm">
        <Assistant />
      </div>
    </div>
  );
}
