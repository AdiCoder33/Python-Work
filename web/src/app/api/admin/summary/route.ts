import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { forwardRequest, proxyJsonResponse } from "@/lib/api";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  if (!token) {
    return NextResponse.json(
      { error: { code: "NOT_AUTHORIZED", message: "Not authenticated." } },
      { status: 401 }
    );
  }

  const { searchParams } = new URL(request.url);
  const query: Record<string, string> = {};
  searchParams.forEach((value, key) => {
    query[key] = value;
  });

  const response = await forwardRequest({
    path: "/admin/summary",
    method: "GET",
    query,
    token,
  });

  return proxyJsonResponse(response);
}
