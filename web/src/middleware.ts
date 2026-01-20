import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get("token")?.value;
  const role = request.cookies.get("role")?.value;

  if (pathname.startsWith("/login")) {
    if (token && role) {
      const redirectTo = role === "admin" ? "/admin/tasks" : "/user/new-task";
      return NextResponse.redirect(new URL(redirectTo, request.url));
    }
    return NextResponse.next();
  }

  if (pathname === "/") {
    if (!token || !role) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
    const redirectTo = role === "admin" ? "/admin/tasks" : "/user/new-task";
    return NextResponse.redirect(new URL(redirectTo, request.url));
  }

  if (pathname.startsWith("/admin")) {
    if (!token || !role) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
    if (role !== "admin") {
      return NextResponse.redirect(new URL("/user/new-task", request.url));
    }
  }

  if (pathname.startsWith("/user")) {
    if (!token || !role) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/login", "/admin/:path*", "/user/:path*"],
};
