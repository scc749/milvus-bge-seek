"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ChevronLeft,
  ChevronRight,
  Database,
  FileStack,
  MessageSquare,
  ShieldX,
  Upload,
} from "lucide-react";
import { ReactNode, useEffect, useState } from "react";

import { cn } from "@/lib/utils";

const navItems = [
  {
    href: "/assistant",
    label: "助手对话",
    description: "assistant-ui 聊天入口",
    icon: MessageSquare,
  },
  {
    href: "/documents",
    label: "文档中心",
    description: "文档列表、详情与上传入库",
    icon: Database,
  },
  {
    href: "/jobs/ingest",
    label: "入库任务",
    description: "查看 ingest_job 任务结果",
    icon: Upload,
  },
  {
    href: "/jobs/delete",
    label: "删除任务",
    description: "查看 delete_job 执行结果",
    icon: ShieldX,
  },
];

export const AppShell = ({ children }: { children: ReactNode }) => {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem("rag-console-sidebar-collapsed");
    setCollapsed(stored === "true");
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((current) => {
      const next = !current;
      window.localStorage.setItem("rag-console-sidebar-collapsed", String(next));
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen max-w-[1600px] flex-col lg:flex-row">
        <aside
          className={cn(
            "border-b bg-card/80 px-4 py-5 backdrop-blur transition-all duration-200 lg:min-h-screen lg:border-r lg:border-b-0",
            collapsed ? "lg:w-24" : "lg:w-72",
          )}
        >
          <div
            className={cn(
              "mb-6 flex items-center gap-3",
              collapsed && "lg:justify-center",
            )}
          >
            <div className="rounded-xl bg-primary/10 p-2 text-primary">
              <FileStack className="size-5" />
            </div>
            {!collapsed ? (
              <div className="min-w-0">
                <div className="font-semibold">RAG Console</div>
                <div className="text-muted-foreground text-xs">
                  assistant + document center + task center
                </div>
              </div>
            ) : null}
            <button
              aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"}
              className="ml-auto hidden rounded-lg border p-2 text-muted-foreground transition-colors hover:bg-muted lg:inline-flex"
              onClick={toggleCollapsed}
              type="button"
            >
              {collapsed ? (
                <ChevronRight className="size-4" />
              ) : (
                <ChevronLeft className="size-4" />
              )}
            </button>
          </div>

          <nav className="grid gap-2">
            {navItems.map((item) => {
              const active =
                pathname === item.href ||
                (item.href !== "/assistant" && pathname.startsWith(item.href));
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "rounded-2xl border px-4 py-3 transition-colors",
                    collapsed && "lg:px-2",
                    active
                      ? "border-primary/30 bg-primary/10"
                      : "border-transparent hover:border-border hover:bg-muted/40",
                  )}
                >
                  <div
                    className={cn(
                      "flex items-start gap-3",
                      collapsed && "lg:flex-col lg:items-center lg:gap-2",
                    )}
                  >
                    <div
                      className={cn(
                        "mt-0.5 rounded-lg p-2",
                        active ? "bg-primary text-primary-foreground" : "bg-muted",
                      )}
                    >
                      <Icon className="size-4" />
                    </div>
                    {!collapsed ? (
                      <div className="min-w-0 space-y-1">
                        <div className="font-medium text-sm">{item.label}</div>
                        <div className="text-muted-foreground text-xs">
                          {item.description}
                        </div>
                      </div>
                    ) : (
                      <div className="hidden lg:block text-center font-medium text-[11px] leading-4">
                        {item.label}
                      </div>
                    )}
                  </div>
                </Link>
              );
            })}
          </nav>
        </aside>

        <main className="flex-1 min-w-0 px-4 py-6 md:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
};
