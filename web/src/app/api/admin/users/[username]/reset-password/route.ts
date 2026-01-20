import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { forwardRequest, proxyJsonResponse } from "@/lib/api";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{ username: string }>;
};

export async function POST(request: Request, context: RouteContext) {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  if (!token) {
    return NextResponse.json(
      { error: { code: "NOT_AUTHORIZED", message: "Not authenticated." } },
      { status: 401 }
    );
  }

  const payload = await request.json().catch(() => null);
  const { username } = await context.params;
  const encodedUsername = encodeURIComponent(username);
  const response = await forwardRequest({
    path: `/admin/users/${encodedUsername}/reset-password`,
    method: "POST",
    body: payload,
    token,
  });

  return proxyJsonResponse(response);
}
