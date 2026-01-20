"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

function extractErrorMessage(payload: unknown) {
  if (!payload || typeof payload !== "object") return "Login failed.";
  const data = payload as Record<string, unknown>;
  const error = data.error as Record<string, unknown> | undefined;
  const traceId = data.trace_id as string | undefined;
  if (error?.message) {
    return traceId ? `${error.message} (trace: ${traceId})` : `${error.message}`;
  }
  if (data.detail && typeof data.detail === "string") {
    return data.detail;
  }
  return "Login failed.";
}

export default function LoginClient() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Username and password are required.");
      return;
    }
    setLoading(true);
    setError("");
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      setError(extractErrorMessage(payload));
      setLoading(false);
      return;
    }

    const payload = await response.json();
    const role = payload.role || "user";
    router.push(role === "admin" ? "/admin/tasks" : "/user/new-task");
  };

  return (
    <div className="min-h-screen">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl items-center px-6">
        <div className="grid w-full gap-10 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-10 shadow-2xl shadow-black/40 backdrop-blur">
            <p className="text-xs uppercase tracking-[0.3em] text-orange-200/80">
              Capital Works Portal
            </p>
            <h1 className="title-serif mt-3 text-4xl font-semibold text-white">
              Secure Access
            </h1>
            <p className="mt-4 text-sm text-slate-300">
              Log in to submit capital works data or manage administrative
              reporting. Credentials are verified against the government
              registry.
            </p>
            <div className="mt-8 space-y-3 text-xs text-slate-400">
              <div className="flex items-center gap-3">
                <span className="h-2 w-2 rounded-full bg-orange-400" />
                Live Excel-backed ledger
              </div>
              <div className="flex items-center gap-3">
                <span className="h-2 w-2 rounded-full bg-teal-300" />
                Role-based controls
              </div>
              <div className="flex items-center gap-3">
                <span className="h-2 w-2 rounded-full bg-slate-300" />
                Audit-ready submissions
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-10 shadow-2xl">
            <h2 className="title-serif text-2xl text-white">Login</h2>
            <p className="mt-2 text-sm text-slate-400">
              Use your assigned credentials to continue.
            </p>
            <form onSubmit={handleSubmit} className="mt-6 space-y-5">
              <div>
                <label className="text-xs uppercase tracking-widest text-slate-400">
                  Username
                </label>
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none transition focus:border-orange-400"
                  placeholder="name@domain.gov"
                />
              </div>
              <div>
                <label className="text-xs uppercase tracking-widest text-slate-400">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none transition focus:border-orange-400"
                  placeholder="********"
                />
              </div>
              {error ? (
                <div className="rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {error}
                </div>
              ) : null}
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-xl bg-orange-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-orange-300 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Signing in..." : "Login"}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
