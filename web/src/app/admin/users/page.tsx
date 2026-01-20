import AppShell from "@/components/AppShell";
import { requireAuth } from "@/lib/auth";
import AdminUsersClient from "./users-client";

export default async function AdminUsersPage() {
  const auth = await requireAuth(["admin"]);
  return (
    <AppShell role={auth.role || "admin"} username={auth.username}>
      <AdminUsersClient currentUser={auth.username || ""} />
    </AppShell>
  );
}
