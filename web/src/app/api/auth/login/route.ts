import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { forwardRequest, proxyJsonResponse } from "@/lib/api";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(request: Request) {
  const payload = await request.json().catch(() => null);
  if (!payload?.username || !payload?.password) {
    return NextResponse.json(
      {
        error: {
          code: "VALIDATION_ERROR",
          message: "Username and password are required.",
        },
      },
      { status: 400 }
    );
  }

  const response = await forwardRequest({
    path: "/auth/login",
    method: "POST",
    body: payload,
  });

  if (!response.ok) {
    return proxyJsonResponse(response);
  }

  const data = await response.json();
  const cookieStore = await cookies();
  const secure = process.env.NODE_ENV === "production";
  cookieStore.set("token", data.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure,
    path: "/",
  });
  cookieStore.set("role", data.role, {
    httpOnly: true,
    sameSite: "lax",
    secure,
    path: "/",
  });
  cookieStore.set("username", data.username, {
    httpOnly: true,
    sameSite: "lax",
    secure,
    path: "/",
  });

  return NextResponse.json({ role: data.role, username: data.username });
}
