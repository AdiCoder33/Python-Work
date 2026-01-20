import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST() {
  const cookieStore = await cookies();
  const options = { path: "/", maxAge: 0 };
  cookieStore.set("token", "", options);
  cookieStore.set("role", "", options);
  cookieStore.set("username", "", options);
  return NextResponse.json({ ok: true });
}
