import { ReactNode } from "react";

import { AppShell } from "@/components/console/app-shell";

export default function ConsoleLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
