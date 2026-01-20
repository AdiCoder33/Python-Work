import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export type AuthInfo = {
  token?: string;
  role?: string;
  username?: string;
};

export async function getAuth(): Promise<AuthInfo> {
  const cookieStore = await cookies();
  return {
    token: cookieStore.get("token")?.value,
    role: cookieStore.get("role")?.value,
    username: cookieStore.get("username")?.value,
  };
}

export async function requireAuth(
  allowedRoles?: string[]
): Promise<AuthInfo> {
  const auth = await getAuth();
  if (!auth.token || !auth.role) {
    redirect("/login");
  }
  if (allowedRoles && !allowedRoles.includes(auth.role)) {
    if (auth.role === "admin") {
      redirect("/admin/tasks");
    }
    redirect("/user/new-task");
  }
  return auth;
}
