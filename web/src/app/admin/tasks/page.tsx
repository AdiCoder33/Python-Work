import AppShell from "@/components/AppShell";
import { requireAuth } from "@/lib/auth";
import AdminTasksClient from "./tasks-client";

export default async function AdminTasksPage() {
  const auth = await requireAuth(["admin"]);
  return (
    <AppShell role={auth.role || "admin"} username={auth.username}>
      <AdminTasksClient />
    </AppShell>
  );
}
