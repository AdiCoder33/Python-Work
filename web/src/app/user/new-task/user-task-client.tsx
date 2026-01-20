"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type FormState = {
  sub_division: string;
  account_code: string;
  number_of_works: string;
  estimate_amount: string;
  agreement_amount: string;
  exp_upto_31_03_2025: string;
  exp_upto_last_month: string;
  exp_during_this_month: string;
  works_completed: string;
};

type TemplateMap = Record<string, Partial<FormState>>;

const emptyForm: FormState = {
  sub_division: "",
  account_code: "",
  number_of_works: "",
  estimate_amount: "",
  agreement_amount: "",
  exp_upto_31_03_2025: "",
  exp_upto_last_month: "",
  exp_during_this_month: "",
  works_completed: "",
};

const floatFields = [
  "estimate_amount",
  "agreement_amount",
  "exp_upto_31_03_2025",
  "exp_upto_last_month",
  "exp_during_this_month",
] as const;

const intFields = ["number_of_works", "works_completed"] as const;

function formatFloat(value: number) {
  return value.toFixed(2);
}

function parseNumber(value: string, type: "int" | "float") {
  const trimmed = value.trim();
  if (!trimmed) return { value: null, error: "Required." };
  const parsed = type === "int" ? Number.parseInt(trimmed, 10) : Number(trimmed);
  if (Number.isNaN(parsed)) {
    return { value: null, error: type === "int" ? "Enter a whole number." : "Enter a valid number." };
  }
  if (parsed < 0) {
    return { value: null, error: "Must be non-negative." };
  }
  return { value: parsed, error: "" };
}

function resolveErrorMessage(data: unknown) {
  if (!data || typeof data !== "object") return "Request failed.";
  const payload = data as Record<string, unknown>;
  const error = payload.error as Record<string, unknown> | undefined;
  const traceId = payload.trace_id as string | undefined;
  if (error?.message) {
    return traceId ? `${error.message} (trace: ${traceId})` : `${error.message}`;
  }
  if (payload.detail && typeof payload.detail === "string") {
    return payload.detail;
  }
  return "Request failed.";
}

export default function UserTaskClient() {
  const [form, setForm] = useState<FormState>(() => {
    if (typeof window === "undefined") {
      return emptyForm;
    }
    const lastSubdivision = sessionStorage.getItem("last_subdivision") || "";
    const lastAccount = sessionStorage.getItem("last_account_code") || "";
    return {
      ...emptyForm,
      sub_division: lastSubdivision,
      account_code: lastAccount,
    };
  });
  const [subdivisions, setSubdivisions] = useState<string[]>([
    "RKV SubDiv-1",
    "RKV SubDiv-2",
    "RKV SubDiv-3",
    "Other...",
  ]);
  const [templates, setTemplates] = useState<TemplateMap>({ Blank: {} });
  const [templateName, setTemplateName] = useState("Blank");
  const [otherSubdivision, setOtherSubdivision] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const isOtherSelected = form.sub_division === "Other...";

  const resolvedSubdivision = isOtherSelected ? otherSubdivision.trim() : form.sub_division.trim();

  const computed = useMemo(() => {
    const toNumber = (value: string) => {
      const trimmed = value.trim();
      if (!trimmed) return Number.NaN;
      return Number(trimmed);
    };

    const agreement = toNumber(form.agreement_amount);
    const exp31 = toNumber(form.exp_upto_31_03_2025);
    const expLast = toNumber(form.exp_upto_last_month);
    const expThis = toNumber(form.exp_during_this_month);
    const works = toNumber(form.number_of_works);
    const completed = toNumber(form.works_completed);

    const balanceAmount =
      Number.isFinite(agreement) && Number.isFinite(exp31) ? agreement - exp31 : null;
    const totalYear =
      Number.isFinite(expLast) && Number.isFinite(expThis) ? expLast + expThis : null;
    const totalValue =
      Number.isFinite(exp31) && Number.isFinite(totalYear) ? exp31 + totalYear : null;
    const balanceWorks =
      Number.isFinite(works) && Number.isFinite(completed) ? works - completed : null;

    return {
      balanceAmount,
      totalYear,
      totalValue,
      balanceWorks,
    };
  }, [
    form.agreement_amount,
    form.exp_upto_31_03_2025,
    form.exp_upto_last_month,
    form.exp_during_this_month,
    form.number_of_works,
    form.works_completed,
  ]);

  useEffect(() => {
    const fetchConfig = async () => {
      const [subdivisionRes, templateRes] = await Promise.allSettled([
        fetch("/config/subdivisions.json"),
        fetch("/config/templates.json"),
      ]);

      if (subdivisionRes.status === "fulfilled") {
        const data = await subdivisionRes.value.json().catch(() => null);
        if (data?.subdivisions && Array.isArray(data.subdivisions)) {
          setSubdivisions([...data.subdivisions, "Other..."]);
        }
      }

      if (templateRes.status === "fulfilled") {
        const data = await templateRes.value.json().catch(() => null);
        if (data?.templates && typeof data.templates === "object") {
          setTemplates({ Blank: {}, ...data.templates });
        }
      }
    };

    fetchConfig();

  }, []);

  const handleChange = (key: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (key === "sub_division" && value !== "Other...") {
      setOtherSubdivision("");
    }
  };

  const markTouched = (key: string) => {
    setTouched((prev) => ({ ...prev, [key]: true }));
  };

  const handleTemplateChange = (name: string) => {
    setTemplateName(name);
    if (name === "Blank") {
      handleClear(false);
      return;
    }
    const template = templates[name] || {};
    setForm((prev) => ({ ...prev, ...template }));
    setErrors({});
    setTouched({});
  };

  const validate = () => {
    const nextErrors: Record<string, string> = {};
    if (!resolvedSubdivision) {
      nextErrors.sub_division = "Sub-Division is required.";
    }
    if (!["Spill", "New"].includes(form.account_code)) {
      nextErrors.account_code = "Account Code is required.";
    }

    intFields.forEach((field) => {
      const result = parseNumber(form[field], "int");
      if (result.error) nextErrors[field] = result.error;
    });

    floatFields.forEach((field) => {
      const result = parseNumber(form[field], "float");
      if (result.error) nextErrors[field] = result.error;
    });

    const works = parseNumber(form.number_of_works, "int").value;
    const completed = parseNumber(form.works_completed, "int").value;
    if (works !== null && completed !== null && completed > works) {
      nextErrors.works_completed =
        "Number of Works Completed cannot exceed Number of Works.";
    }

    const agreement = parseNumber(form.agreement_amount, "float").value;
    const exp31 = parseNumber(form.exp_upto_31_03_2025, "float").value;
    if (agreement !== null && exp31 !== null && agreement < exp31) {
      nextErrors.exp_upto_31_03_2025 =
        "Expenditure up to 31-03-2025 must be <= Agreement Amount.";
    }

    return nextErrors;
  };

  const handleSubmit = async () => {
    setMessage(null);
    const validation = validate();
    setErrors(validation);
    if (Object.keys(validation).length > 0) {
      const touchedAll: Record<string, boolean> = {};
      Object.keys(validation).forEach((key) => {
        touchedAll[key] = true;
      });
      setTouched((prev) => ({ ...prev, ...touchedAll }));
      return;
    }

    setLoading(true);
    const payload = {
      sub_division: resolvedSubdivision,
      account_code: form.account_code,
      number_of_works: Number(form.number_of_works),
      estimate_amount: Number(form.estimate_amount),
      agreement_amount: Number(form.agreement_amount),
      exp_upto_31_03_2025: Number(form.exp_upto_31_03_2025),
      exp_upto_last_month: Number(form.exp_upto_last_month),
      exp_during_this_month: Number(form.exp_during_this_month),
      works_completed: Number(form.works_completed),
    };

    const response = await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      setMessage(resolveErrorMessage(payload));
      setLoading(false);
      return;
    }

    const data = await response.json().catch(() => ({}));
    const sno = data.sno ? `S. No: ${data.sno}` : "Record submitted.";
    setMessage(`Success. ${sno}`);
    sessionStorage.setItem("last_subdivision", resolvedSubdivision);
    sessionStorage.setItem("last_account_code", form.account_code);
    handleClear(false);
    setTemplateName("Blank");
    setLoading(false);
  };

  const handleClear = (keepTemplate = true) => {
    setForm((prev) => ({
      ...emptyForm,
      sub_division: keepTemplate ? prev.sub_division : "",
      account_code: keepTemplate ? prev.account_code : "",
    }));
    setOtherSubdivision("");
    setErrors({});
    setTouched({});
    setMessage(null);
  };

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.key.toLowerCase() === "n") {
        event.preventDefault();
        handleClear();
      }
      if (event.key === "Enter") {
        const target = event.target as HTMLElement | null;
        if (target && (target.tagName === "INPUT" || target.tagName === "SELECT")) {
          event.preventDefault();
          handleSubmit();
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  return (
    <div className="space-y-8">
      <div className="rounded-3xl border border-white/10 bg-white/5 p-8 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-orange-200/80">
              Capital Works - Above Rs. 50.00 Lakhs
            </p>
            <h1 className="title-serif mt-3 text-3xl text-white">
              New Capital Works Submission
            </h1>
          </div>
          <div className="min-w-[220px]">
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Template
            </label>
            <select
              value={templateName}
              onChange={(event) => handleTemplateChange(event.target.value)}
              className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-2 text-sm text-white"
            >
              {Object.keys(templates).map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-8 shadow-2xl">
          <h2 className="title-serif text-xl text-white">Submission Details</h2>
          <p className="mt-2 text-sm text-slate-400">
            Fill in the editable fields. Computed values update automatically.
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className="text-xs uppercase tracking-widest text-slate-400">
                Sub-Division
              </label>
              <select
                value={form.sub_division}
                onChange={(event) => handleChange("sub_division", event.target.value)}
                onBlur={() => markTouched("sub_division")}
                className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                  errors.sub_division && touched.sub_division && !isOtherSelected
                    ? "border-red-400 bg-red-500/10"
                    : "border-white/10 bg-slate-900/80"
                }`}
              >
                <option value="">Select subdivision</option>
                {(subdivisions.length ? subdivisions : ["Other..."]).map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
              {errors.sub_division && touched.sub_division && !isOtherSelected ? (
                <p className="mt-1 text-xs text-red-300">{errors.sub_division}</p>
              ) : null}
            </div>
            {isOtherSelected ? (
              <div className="md:col-span-2">
                <label className="text-xs uppercase tracking-widest text-slate-400">
                  Other Sub-Division
                </label>
                <input
                  value={otherSubdivision}
                  onChange={(event) => setOtherSubdivision(event.target.value)}
                  onBlur={() => markTouched("sub_division")}
                  className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                    errors.sub_division && touched.sub_division
                      ? "border-red-400 bg-red-500/10"
                      : "border-white/10 bg-slate-900/80"
                  }`}
                  placeholder="Enter subdivision"
                />
                {errors.sub_division && touched.sub_division ? (
                  <p className="mt-1 text-xs text-red-300">{errors.sub_division}</p>
                ) : null}
              </div>
            ) : null}

            <div>
              <label className="text-xs uppercase tracking-widest text-slate-400">
                Account Code
              </label>
              <select
                value={form.account_code}
                onChange={(event) => handleChange("account_code", event.target.value)}
                onBlur={() => markTouched("account_code")}
                className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                  errors.account_code && touched.account_code
                    ? "border-red-400 bg-red-500/10"
                    : "border-white/10 bg-slate-900/80"
                }`}
              >
                <option value="">Select</option>
                <option value="Spill">Spill</option>
                <option value="New">New</option>
              </select>
              {errors.account_code && touched.account_code ? (
                <p className="mt-1 text-xs text-red-300">{errors.account_code}</p>
              ) : null}
            </div>

            {[
              { key: "number_of_works", label: "Number of Works", type: "number" },
              { key: "estimate_amount", label: "Estimate Amount", type: "number" },
              { key: "agreement_amount", label: "Agreement Amount", type: "number" },
              { key: "exp_upto_31_03_2025", label: "Expenditure up to 31-03-2025", type: "number" },
              { key: "exp_upto_last_month", label: "Expenditure up to Last Month", type: "number" },
              { key: "exp_during_this_month", label: "Expenditure During This Month", type: "number" },
              { key: "works_completed", label: "Number of Works Completed", type: "number" },
            ].map((field) => (
              <div key={field.key} className="md:col-span-1">
                <label className="text-xs uppercase tracking-widest text-slate-400">
                  {field.label}
                </label>
                <input
                  type={field.type}
                  value={form[field.key as keyof FormState]}
                  onChange={(event) =>
                    handleChange(field.key as keyof FormState, event.target.value)
                  }
                  onBlur={() => markTouched(field.key)}
                  className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                    errors[field.key] && touched[field.key]
                      ? "border-red-400 bg-red-500/10"
                      : "border-white/10 bg-slate-900/80"
                  }`}
                />
                {errors[field.key] && touched[field.key] ? (
                  <p className="mt-1 text-xs text-red-300">{errors[field.key]}</p>
                ) : null}
              </div>
            ))}
          </div>
          {message ? (
            <div className="mt-5 rounded-xl border border-orange-400/40 bg-orange-500/10 px-4 py-3 text-sm text-orange-100">
              {message}
            </div>
          ) : null}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading}
              className="rounded-xl bg-orange-400 px-6 py-2 text-sm font-semibold text-slate-950 transition hover:bg-orange-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Submitting..." : "Submit"}
            </button>
            <button
              type="button"
              onClick={() => handleClear()}
              className="rounded-xl border border-white/10 px-6 py-2 text-sm text-slate-200 transition hover:border-white/30"
            >
              Clear
            </button>
            <Link
              href="/user/tasks"
              className="rounded-xl border border-white/10 px-6 py-2 text-sm text-slate-200 transition hover:border-white/30"
            >
              View History
            </Link>
            <p className="text-xs text-slate-500">
              Shortcut: Enter to submit, Ctrl+N to clear
            </p>
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/5 p-8 shadow-xl">
          <h2 className="title-serif text-xl text-white">Computed Preview</h2>
          <p className="mt-2 text-sm text-slate-400">
            These fields are calculated client-side and verified by the server.
          </p>
          <div className="mt-6 space-y-4 text-sm">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <span className="text-slate-400">S. No.</span>
              <span className="text-white">Auto</span>
            </div>
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <span className="text-slate-400">Balance Amount as on 01-04-2025</span>
              <span className="text-white">
                {computed.balanceAmount === null
                  ? "-"
                  : formatFloat(computed.balanceAmount)}
              </span>
            </div>
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <span className="text-slate-400">Total Expenditure During the Year</span>
              <span className="text-white">
                {computed.totalYear === null ? "-" : formatFloat(computed.totalYear)}
              </span>
            </div>
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <span className="text-slate-400">
                Total Value of Work Done from the Beginning
              </span>
              <span className="text-white">
                {computed.totalValue === null ? "-" : formatFloat(computed.totalValue)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Balance Number of Works</span>
              <span className="text-white">
                {computed.balanceWorks === null ? "-" : computed.balanceWorks}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
