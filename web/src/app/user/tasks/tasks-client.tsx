"use client";

import { useEffect, useMemo, useState } from "react";
import TaskEditModal, { TaskRecord } from "@/components/TaskEditModal";

type ColumnDef = {
  key: string;
  label: string;
  type: "text" | "int" | "float";
};

const columns: ColumnDef[] = [
  { key: "sno", label: "S. No.", type: "int" },
  { key: "sub_division", label: "Sub-Division", type: "text" },
  { key: "account_code", label: "Account Code", type: "text" },
  { key: "number_of_works", label: "Number of Works", type: "int" },
  { key: "estimate_amount", label: "Estimate Amount", type: "float" },
  { key: "agreement_amount", label: "Agreement Amount", type: "float" },
  {
    key: "exp_upto_31_03_2025",
    label: "Expenditure up to 31-03-2025",
    type: "float",
  },
  {
    key: "balance_amount_as_on_01_04_2025",
    label: "Balance Amount as on 01-04-2025",
    type: "float",
  },
  {
    key: "exp_upto_last_month",
    label: "Expenditure up to Last Month",
    type: "float",
  },
  {
    key: "exp_during_this_month",
    label: "Expenditure During This Month",
    type: "float",
  },
  {
    key: "total_exp_during_year",
    label: "Total Expenditure During the Year",
    type: "float",
  },
  {
    key: "total_value_work_done_from_beginning",
    label: "Total Value of Work Done from the Beginning",
    type: "float",
  },
  { key: "works_completed", label: "Number of Works Completed", type: "int" },
  { key: "balance_works", label: "Balance Number of Works", type: "int" },
  { key: "created_at", label: "Created At", type: "text" },
];

type TaskResponse = {
  items: TaskRecord[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
};

function formatCell(value: string | number | undefined, type: ColumnDef["type"]) {
  if (value === undefined || value === null || value === "") return "-";
  if (type === "float") {
    const num = Number(value);
    return Number.isFinite(num) ? num.toFixed(2) : String(value);
  }
  if (type === "int") {
    const num = Number(value);
    return Number.isFinite(num) ? String(Math.trunc(num)) : String(value);
  }
  return String(value);
}

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

export default function UserTasksClient() {
  const [subDivision, setSubDivision] = useState("");
  const [accountCode, setAccountCode] = useState("All");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [data, setData] = useState<TaskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<TaskRecord | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const resetPage = () => setPage(1);

  const query = useMemo(() => {
    return {
      sort_by: sortBy,
      order,
      page,
      page_size: pageSize,
      sub_division: subDivision || undefined,
      account_code: accountCode === "All" ? undefined : accountCode,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    };
  }, [sortBy, order, page, pageSize, subDivision, accountCode, dateFrom, dateTo]);

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
      const response = await fetch(`/api/tasks?${params.toString()}`, {
        signal: controller.signal,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        setError(extractErrorMessage(payload));
        setLoading(false);
        return;
      }
      const payload = (await response.json()) as TaskResponse;
      setData(payload);
      setLoading(false);
    };
    load();
    return () => controller.abort();
  }, [query, refreshKey]);

  const totalPages = data?.total_pages || 1;

  const handleEditSave = async (payload: Record<string, number | string>) => {
    if (!editing) return false;
    const response = await fetch(`/api/tasks/${editing.sno}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      setError(extractErrorMessage(payload));
      return false;
    }
    setActionMessage("Task updated.");
    setRefreshKey((prev) => prev + 1);
    return true;
  };

  const handleDelete = async (task: TaskRecord) => {
    const ok = window.confirm(`Delete task #${task.sno}?`);
    if (!ok) return;
    const response = await fetch(`/api/tasks/${task.sno}`, { method: "DELETE" });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      setError(extractErrorMessage(payload));
      return;
    }
    setActionMessage("Task deleted.");
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-orange-200/80">
            User Console
          </p>
          <h1 className="title-serif mt-2 text-3xl text-white">My Submissions</h1>
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-xl">
        <div className="grid gap-4 md:grid-cols-4">
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Sub-Division
            </label>
            <input
              value={subDivision}
              onChange={(event) => {
                setSubDivision(event.target.value);
                resetPage();
              }}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
              placeholder="Search"
            />
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Account Code
            </label>
            <select
              value={accountCode}
              onChange={(event) => {
                setAccountCode(event.target.value);
                resetPage();
              }}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            >
              <option value="All">All</option>
              <option value="Spill">Spill</option>
              <option value="New">New</option>
            </select>
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Date From
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(event) => {
                setDateFrom(event.target.value);
                resetPage();
              }}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Date To
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(event) => {
                setDateTo(event.target.value);
                resetPage();
              }}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Sort By
            </label>
            <select
              value={sortBy}
              onChange={(event) => {
                setSortBy(event.target.value);
                resetPage();
              }}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            >
              {columns.map((col) => (
                <option key={col.key} value={col.key}>
                  {col.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Order
            </label>
            <div className="mt-2 flex rounded-xl border border-white/10 bg-slate-900/80 p-1 text-xs">
              {(["asc", "desc"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => {
                    setOrder(value);
                    resetPage();
                  }}
                  className={`flex-1 rounded-lg px-3 py-2 uppercase tracking-widest transition ${
                    order === value
                      ? "bg-orange-400 text-slate-950"
                      : "text-slate-300 hover:text-white"
                  }`}
                >
                  {value}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Page Size
            </label>
            <select
              value={pageSize}
              onChange={(event) => {
                setPageSize(Number(event.target.value));
                resetPage();
              }}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            >
              {[25, 50, 100, 200, 500].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
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
        {!loading && !error && data && data.items.length === 0 ? (
          <p className="text-sm text-slate-400">No records found.</p>
        ) : null}
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-[1500px] w-full text-left text-xs text-slate-300">
            <thead className="border-b border-white/10 text-[11px] uppercase tracking-widest text-slate-400">
              <tr>
                {columns.map((col) => (
                  <th key={col.key} className="px-3 py-3">
                    {col.label}
                  </th>
                ))}
                <th className="px-3 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((item, idx) => (
                <tr
                  key={`${item.sno}-${idx}`}
                  className="border-b border-white/5 hover:bg-white/5"
                >
                  {columns.map((col) => (
                    <td key={col.key} className="px-3 py-3">
                      {formatCell(item[col.key as keyof TaskRecord] as string | number, col.type)}
                    </td>
                  ))}
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => setEditing(item)}
                        className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-widest text-slate-200 transition hover:border-white/30"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(item)}
                        className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-widest text-slate-200 transition hover:border-white/30"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
          <span>
            Page {data?.page || 1} of {totalPages} - {data?.total_items || 0} total
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              disabled={page <= 1}
              className="rounded-full border border-white/10 px-4 py-2 uppercase tracking-widest text-slate-300 transition hover:border-white/30 disabled:opacity-40"
            >
              Prev
            </button>
            <button
              type="button"
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={page >= totalPages}
              className="rounded-full border border-white/10 px-4 py-2 uppercase tracking-widest text-slate-300 transition hover:border-white/30 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      <TaskEditModal
        key={editing?.sno ?? "task"}
        open={Boolean(editing)}
        task={editing}
        onClose={() => setEditing(null)}
        onSave={handleEditSave}
      />
    </div>
  );
}
