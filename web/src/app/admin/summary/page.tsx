import AppShell from "@/components/AppShell";
import { requireAuth } from "@/lib/auth";
import AdminSummaryClient from "./summary-client";

export default async function AdminSummaryPage() {
  const auth = await requireAuth(["admin"]);
  return (
    <AppShell role={auth.role || "admin"} username={auth.username}>
      <AdminSummaryClient />
    </AppShell>
  );
}
