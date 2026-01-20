"use client";

import { useEffect, useMemo, useState } from "react";

type NumericField = {
  key: string;
  label: string;
  type: "int" | "float";
};

const numericFields: NumericField[] = [
  { key: "number_of_works", label: "Number of Works", type: "int" },
  { key: "estimate_amount", label: "Estimate Amount", type: "float" },
  { key: "agreement_amount", label: "Agreement Amount", type: "float" },
  { key: "exp_upto_31_03_2025", label: "Expenditure up to 31-03-2025", type: "float" },
  {
    key: "balance_amount_as_on_01_04_2025",
    label: "Balance Amount as on 01-04-2025",
    type: "float",
  },
  { key: "exp_upto_last_month", label: "Expenditure up to Last Month", type: "float" },
  {
    key: "exp_during_this_month",
    label: "Expenditure During This Month",
    type: "float",
  },
  { key: "total_exp_during_year", label: "Total Expenditure During the Year", type: "float" },
  {
    key: "total_value_work_done_from_beginning",
    label: "Total Value of Work Done from the Beginning",
    type: "float",
  },
  { key: "works_completed", label: "Number of Works Completed", type: "int" },
  { key: "balance_works", label: "Balance Number of Works", type: "int" },
];

type SummaryResponse = {
  grand_totals: Record<string, number>;
  by_sub_division: {
    sub_division: string;
    totals: Record<string, number>;
    by_account_code?: { account_code: string; totals: Record<string, number> }[];
  }[];
};

function formatValue(value: number | undefined, type: "int" | "float") {
  if (value === undefined || value === null) return "-";
  if (type === "float") return Number(value).toFixed(2);
  return String(Math.trunc(value));
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

export default function AdminSummaryClient() {
  const [subDivision, setSubDivision] = useState("");
  const [accountCode, setAccountCode] = useState("All");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(
    () => ({
      sub_division: subDivision || undefined,
      account_code: accountCode === "All" ? undefined : accountCode,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
    [subDivision, accountCode, dateFrom, dateTo]
  );

  useEffect(() => {
    const controller = new AbortController();
    const load = async () => {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      Object.entries(query).forEach(([key, value]) => {
        if (!value) return;
        params.set(key, String(value));
      });
      const response = await fetch(`/api/admin/summary?${params.toString()}`, {
        signal: controller.signal,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        setError(extractErrorMessage(payload));
        setLoading(false);
        return;
      }
      const payload = (await response.json()) as SummaryResponse;
      setSummary(payload);
      setLoading(false);
    };
    load();
    return () => controller.abort();
  }, [query]);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-orange-200/80">
          Admin Console
        </p>
        <h1 className="title-serif mt-2 text-3xl text-white">Summary Ledger</h1>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-xl">
        <div className="grid gap-4 md:grid-cols-4">
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Sub-Division
            </label>
            <input
              value={subDivision}
              onChange={(event) => setSubDivision(event.target.value)}
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
              onChange={(event) => setAccountCode(event.target.value)}
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
              onChange={(event) => setDateFrom(event.target.value)}
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
              onChange={(event) => setDateTo(event.target.value)}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            />
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-2xl">
        {loading ? <p className="text-sm text-slate-400">Loading...</p> : null}
        {error ? (
          <div className="rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        ) : null}
        {summary ? (
          <div className="space-y-6">
            <div>
              <h2 className="title-serif text-lg text-white">Grand Totals</h2>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                {numericFields.map((field) => (
                  <div
                    key={field.key}
                    className="rounded-2xl border border-white/10 bg-white/5 p-4"
                  >
                    <p className="text-xs uppercase tracking-widest text-slate-400">
                      {field.label}
                    </p>
                    <p className="mt-2 text-xl text-white">
                      {formatValue(summary.grand_totals?.[field.key], field.type)}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h2 className="title-serif text-lg text-white">By Sub-Division</h2>
              <div className="mt-4 space-y-4">
                {summary.by_sub_division?.map((entry) => (
                  <div
                    key={entry.sub_division}
                    className="rounded-2xl border border-white/10 bg-white/5 p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div>
                        <p className="text-xs uppercase tracking-widest text-slate-400">
                          Sub-Division
                        </p>
                        <p className="text-lg text-white">{entry.sub_division}</p>
                      </div>
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      {numericFields.map((field) => (
                        <div key={field.key} className="text-sm text-slate-300">
                          <span className="text-slate-400">{field.label}: </span>
                          {formatValue(entry.totals?.[field.key], field.type)}
                        </div>
                      ))}
                    </div>
                    {entry.by_account_code?.length ? (
                      <div className="mt-4 border-t border-white/10 pt-4">
                        <p className="text-xs uppercase tracking-widest text-slate-400">
                          By Account Code
                        </p>
                        <div className="mt-3 grid gap-4 md:grid-cols-2">
                          {entry.by_account_code.map((account) => (
                            <div
                              key={account.account_code}
                              className="rounded-xl border border-white/10 bg-slate-900/60 p-3"
                            >
                              <p className="text-sm text-white">
                                {account.account_code}
                              </p>
                              <div className="mt-2 space-y-1 text-xs text-slate-300">
                                {numericFields.map((field) => (
                                  <div key={field.key}>
                                    <span className="text-slate-400">{field.label}: </span>
                                    {formatValue(account.totals?.[field.key], field.type)}
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
