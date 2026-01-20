import { redirect } from "next/navigation";
import { getAuth } from "@/lib/auth";

export default async function Home() {
  const { token, role } = await getAuth();
  if (!token || !role) {
    redirect("/login");
  }
  if (role === "admin") {
    redirect("/admin/tasks");
  }
  redirect("/user/new-task");
}
