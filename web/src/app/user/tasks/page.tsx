import AppShell from "@/components/AppShell";
import { requireAuth } from "@/lib/auth";
import UserTasksClient from "./tasks-client";

export default async function UserTasksPage() {
  const auth = await requireAuth(["user", "admin"]);
  return (
    <AppShell role={auth.role || "user"} username={auth.username}>
      <UserTasksClient />
    </AppShell>
  );
}
