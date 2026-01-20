"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

type AppShellProps = {
  role: string;
  username?: string;
  children: React.ReactNode;
};

const adminLinks = [
  { href: "/admin/tasks", label: "Tasks" },
  { href: "/admin/summary", label: "Summary" },
  { href: "/admin/users", label: "Users" },
  { href: "/user/new-task", label: "New Task" },
];

const userLinks = [
  { href: "/user/new-task", label: "New Task" },
  { href: "/user/tasks", label: "My Tasks" },
];

export default function AppShell({ role, username, children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  const links = role === "admin" ? adminLinks : userLinks;

  const handleLogout = async () => {
    if (busy) return;
    setBusy(true);
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-white/10 bg-slate-950/70 backdrop-blur">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="title-serif text-lg font-semibold tracking-wide">
              Capital Works
            </p>
            <p className="text-xs text-slate-400">
              Above Rs. 50.00 Lakhs - {role.toUpperCase()}
            </p>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-300">
            <span>{username || "Signed in"}</span>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-full border border-white/10 px-4 py-1.5 text-xs uppercase tracking-widest text-slate-200 transition hover:border-white/30 hover:text-white"
            >
              {busy ? "Signing out..." : "Logout"}
            </button>
          </div>
        </div>
        <nav className="border-t border-white/10 bg-slate-950/60">
          <div className="mx-auto flex w-full max-w-6xl flex-wrap gap-2 px-6 py-3">
            {links.map((link) => {
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-full px-4 py-1.5 text-xs uppercase tracking-widest transition ${
                    active
                      ? "bg-orange-500 text-slate-950"
                      : "border border-white/10 text-slate-300 hover:border-white/30 hover:text-white"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-6xl px-6 py-10">
        {children}
      </main>
    </div>
  );
}
