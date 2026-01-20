import AppShell from "@/components/AppShell";
import { requireAuth } from "@/lib/auth";
import UserTaskClient from "./user-task-client";

export default async function NewTaskPage() {
  const auth = await requireAuth(["user", "admin"]);
  return (
    <AppShell role={auth.role || "user"} username={auth.username}>
      <UserTaskClient />
    </AppShell>
  );
}
