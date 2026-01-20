"use client";

import { useEffect, useMemo, useState } from "react";
import Modal from "@/components/Modal";

type UserRecord = {
  username: string;
  role: string;
  is_active: number;
  created_at: string;
  last_login_at?: string | null;
};

function extractErrorMessage(payload: unknown) {
  if (!payload || typeof payload !== "object") return "Request failed.";
  const data = payload as Record<string, unknown>;
  const error = data.error as Record<string, unknown> | undefined;
  const traceId = data.trace_id as string | undefined;
  if (error?.message) {
    return traceId ? `${error.message} (trace: ${traceId})` : `${error.message}`;
  }
  if (data.detail && typeof data.detail === "string") {
    return data.detail;
  }
  return "Request failed.";
}

export default function AdminUsersClient({ currentUser }: { currentUser: string }) {
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const [createOpen, setCreateOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [selected, setSelected] = useState<UserRecord | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const [createForm, setCreateForm] = useState({
    username: "",
    password: "",
    role: "user",
  });
  const [resetForm, setResetForm] = useState({
    password: "",
    confirm: "",
  });

  const query = useMemo(() => {
    return {
      q: search || undefined,
      role: roleFilter === "All" ? undefined : roleFilter.toLowerCase(),
      is_active:
        statusFilter === "All"
          ? undefined
          : statusFilter === "Active"
            ? 1
            : 0,
    };
  }, [search, roleFilter, statusFilter]);

  useEffect(() => {
    const controller = new AbortController();
    const load = async () => {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      Object.entries(query).forEach(([key, value]) => {
        if (value === undefined || value === "") return;
        params.set(key, String(value));
      });
      const response = await fetch(`/api/admin/users?${params.toString()}`, {
        signal: controller.signal,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        setError(extractErrorMessage(payload));
        setLoading(false);
        return;
      }
      const payload = (await response.json()) as UserRecord[];
      setUsers(payload);
      setLoading(false);
    };
    load();
    return () => controller.abort();
  }, [query, refreshKey]);

  const openCreate = () => {
    setCreateForm({ username: "", password: "", role: "user" });
    setCreateOpen(true);
  };

  const submitCreate = async () => {
    if (!createForm.username.trim() || !createForm.password.trim()) {
      setActionMessage("Username and password are required.");
      return;
    }
    const response = await fetch("/api/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: createForm.username.trim(),
        password: createForm.password,
        role: createForm.role,
      }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      setActionMessage(extractErrorMessage(payload));
      return;
    }
    setActionMessage("User created successfully.");
    setCreateOpen(false);
    setRefreshKey((prev) => prev + 1);
  };

  const toggleStatus = async (user: UserRecord) => {
    if (user.username === currentUser && user.is_active === 1) {
      setActionMessage("You cannot disable your own account.");
      return;
    }
    const response = await fetch(
      `/api/admin/users/${encodeURIComponent(user.username)}/status`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: user.is_active === 1 ? 0 : 1 }),
      }
    );
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      setActionMessage(extractErrorMessage(payload));
      return;
    }
    setActionMessage("User status updated.");
    setRefreshKey((prev) => prev + 1);
  };

  const openReset = (user: UserRecord) => {
    setSelected(user);
    setResetForm({ password: "", confirm: "" });
    setResetOpen(true);
  };

  const submitReset = async () => {
    if (!selected) return;
    if (!resetForm.password.trim()) {
      setActionMessage("Password is required.");
      return;
    }
    if (resetForm.password !== resetForm.confirm) {
      setActionMessage("Passwords do not match.");
      return;
    }
    const response = await fetch(
      `/api/admin/users/${encodeURIComponent(selected.username)}/reset-password`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_password: resetForm.password }),
      }
    );
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      setActionMessage(extractErrorMessage(payload));
      return;
    }
    setActionMessage("Password reset successfully.");
    setResetOpen(false);
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-orange-200/80">
            Admin Console
          </p>
          <h1 className="title-serif mt-2 text-3xl text-white">
            User Management
          </h1>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="rounded-full border border-white/10 px-5 py-2 text-xs uppercase tracking-widest text-slate-200 transition hover:border-white/30"
        >
          Create User
        </button>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-xl">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Search
            </label>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
              placeholder="Username"
            />
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Role
            </label>
            <select
              value={roleFilter}
              onChange={(event) => setRoleFilter(event.target.value)}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            >
              <option value="All">All</option>
              <option value="Admin">Admin</option>
              <option value="User">User</option>
            </select>
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            >
              <option value="All">All</option>
              <option value="Active">Active</option>
              <option value="Disabled">Disabled</option>
            </select>
          </div>
        </div>
      </div>

      {actionMessage ? (
        <div className="rounded-xl border border-orange-400/40 bg-orange-500/10 px-4 py-3 text-sm text-orange-100">
          {actionMessage}
        </div>
      ) : null}

      <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-2xl">
        {loading ? <p className="text-sm text-slate-400">Loading...</p> : null}
        {error ? (
          <div className="rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        ) : null}
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-[720px] w-full text-left text-xs text-slate-300">
            <thead className="border-b border-white/10 text-[11px] uppercase tracking-widest text-slate-400">
              <tr>
                <th className="px-3 py-3">Username</th>
                <th className="px-3 py-3">Role</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Created At</th>
                <th className="px-3 py-3">Last Login</th>
                <th className="px-3 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr
                  key={user.username}
                  className="border-b border-white/5 hover:bg-white/5"
                >
                  <td className="px-3 py-3">{user.username}</td>
                  <td className="px-3 py-3">{user.role}</td>
                  <td className="px-3 py-3">
                    {user.is_active === 1 ? "Active" : "Disabled"}
                  </td>
                  <td className="px-3 py-3">{user.created_at || "-"}</td>
                  <td className="px-3 py-3">{user.last_login_at || "-"}</td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => toggleStatus(user)}
                        className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-widest text-slate-200 transition hover:border-white/30"
                      >
                        {user.is_active === 1 ? "Disable" : "Enable"}
                      </button>
                      <button
                        type="button"
                        onClick={() => openReset(user)}
                        className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-widest text-slate-200 transition hover:border-white/30"
                      >
                        Reset
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && users.length === 0 ? (
                <tr>
                  <td className="px-3 py-6 text-center text-sm text-slate-400" colSpan={6}>
                    No users found.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>

      <Modal open={createOpen} title="Create User" onClose={() => setCreateOpen(false)}>
        <div className="space-y-4">
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Username
            </label>
            <input
              value={createForm.username}
              onChange={(event) =>
                setCreateForm((prev) => ({ ...prev, username: event.target.value }))
              }
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Password
            </label>
            <input
              type="password"
              value={createForm.password}
              onChange={(event) =>
                setCreateForm((prev) => ({ ...prev, password: event.target.value }))
              }
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Role
            </label>
            <select
              value={createForm.role}
              onChange={(event) =>
                setCreateForm((prev) => ({ ...prev, role: event.target.value }))
              }
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            >
              <option value="admin">Admin</option>
              <option value="user">User</option>
            </select>
          </div>
          <button
            type="button"
            onClick={submitCreate}
            className="w-full rounded-xl bg-orange-400 px-4 py-2 text-sm font-semibold text-slate-950"
          >
            Create User
          </button>
        </div>
      </Modal>

      <Modal open={resetOpen} title="Reset Password" onClose={() => setResetOpen(false)}>
        <div className="space-y-4">
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              New Password
            </label>
            <input
              type="password"
              value={resetForm.password}
              onChange={(event) =>
                setResetForm((prev) => ({ ...prev, password: event.target.value }))
              }
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Confirm Password
            </label>
            <input
              type="password"
              value={resetForm.confirm}
              onChange={(event) =>
                setResetForm((prev) => ({ ...prev, confirm: event.target.value }))
              }
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            />
          </div>
          <button
            type="button"
            onClick={submitReset}
            className="w-full rounded-xl bg-orange-400 px-4 py-2 text-sm font-semibold text-slate-950"
          >
            Reset Password
          </button>
        </div>
      </Modal>
    </div>
  );
}
