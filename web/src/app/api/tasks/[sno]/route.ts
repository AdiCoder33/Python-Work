import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { forwardRequest, proxyJsonResponse } from "@/lib/api";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{ sno: string }>;
};

export async function PATCH(request: Request, context: RouteContext) {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  if (!token) {
    return NextResponse.json(
      { error: { code: "NOT_AUTHORIZED", message: "Not authenticated." } },
      { status: 401 }
    );
  }

  const payload = await request.json().catch(() => null);
  const { sno } = await context.params;
  const response = await forwardRequest({
    path: `/tasks/${encodeURIComponent(sno)}`,
    method: "PATCH",
    body: payload,
    token,
  });

  return proxyJsonResponse(response);
}

export async function DELETE(_request: Request, context: RouteContext) {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;
  if (!token) {
    return NextResponse.json(
      { error: { code: "NOT_AUTHORIZED", message: "Not authenticated." } },
      { status: 401 }
    );
  }

  const { sno } = await context.params;
  const response = await forwardRequest({
    path: `/tasks/${encodeURIComponent(sno)}`,
    method: "DELETE",
    token,
  });

  return proxyJsonResponse(response);
}
