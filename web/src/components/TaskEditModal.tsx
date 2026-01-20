"use client";

import { useMemo, useState } from "react";
import Modal from "./Modal";

export type TaskRecord = {
  sno: number;
  sub_division: string;
  account_code: string;
  number_of_works: number;
  estimate_amount: number;
  agreement_amount: number;
  exp_upto_31_03_2025: number;
  balance_amount_as_on_01_04_2025: number;
  exp_upto_last_month: number;
  exp_during_this_month: number;
  total_exp_during_year: number;
  total_value_work_done_from_beginning: number;
  works_completed: number;
  balance_works: number;
  created_by: string;
  created_at: string;
};

type TaskForm = {
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

type TaskEditModalProps = {
  open: boolean;
  task: TaskRecord | null;
  onClose: () => void;
  onSave: (payload: Record<string, number | string>) => Promise<boolean>;
};

const emptyForm: TaskForm = {
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

function parseNumber(value: string, type: "int" | "float") {
  const trimmed = value.trim();
  if (!trimmed) return { value: null, error: "Required." };
  const parsed = type === "int" ? Number.parseInt(trimmed, 10) : Number(trimmed);
  if (Number.isNaN(parsed)) {
    return { value: null, error: type === "int" ? "Enter a whole number." : "Enter a valid number." };
  }
  if (parsed < 0) return { value: null, error: "Must be non-negative." };
  return { value: parsed, error: "" };
}

function formatFloat(value: number | null) {
  if (value === null || Number.isNaN(value)) return "-";
  return Number(value).toFixed(2);
}

function formatInt(value: number | null) {
  if (value === null || Number.isNaN(value)) return "-";
  return String(Math.trunc(value));
}

export default function TaskEditModal({ open, task, onClose, onSave }: TaskEditModalProps) {
  const [form, setForm] = useState<TaskForm>(() => {
    if (!task) return emptyForm;
    return {
      sub_division: task.sub_division || "",
      account_code: task.account_code || "",
      number_of_works: String(task.number_of_works ?? ""),
      estimate_amount: String(task.estimate_amount ?? ""),
      agreement_amount: String(task.agreement_amount ?? ""),
      exp_upto_31_03_2025: String(task.exp_upto_31_03_2025 ?? ""),
      exp_upto_last_month: String(task.exp_upto_last_month ?? ""),
      exp_during_this_month: String(task.exp_during_this_month ?? ""),
      works_completed: String(task.works_completed ?? ""),
    };
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

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

    return { balanceAmount, totalYear, totalValue, balanceWorks };
  }, [form]);

  const validate = () => {
    const nextErrors: Record<string, string> = {};
    if (!form.sub_division.trim()) nextErrors.sub_division = "Sub-Division is required.";
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

  const handleSave = async () => {
    const validation = validate();
    setErrors(validation);
    if (Object.keys(validation).length > 0) return;

    if (!task) return;
    setSaving(true);
    const success = await onSave({
      sub_division: form.sub_division.trim(),
      account_code: form.account_code,
      number_of_works: Number(form.number_of_works),
      estimate_amount: Number(form.estimate_amount),
      agreement_amount: Number(form.agreement_amount),
      exp_upto_31_03_2025: Number(form.exp_upto_31_03_2025),
      exp_upto_last_month: Number(form.exp_upto_last_month),
      exp_during_this_month: Number(form.exp_during_this_month),
      works_completed: Number(form.works_completed),
    });
    setSaving(false);
    if (success) {
      onClose();
    }
  };

  return (
    <Modal open={open} title={task ? `Edit Task #${task.sno}` : "Edit Task"} onClose={onClose}>
      <div className="space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          <div className="md:col-span-2">
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Sub-Division
            </label>
            <input
              value={form.sub_division}
              onChange={(event) => setForm((prev) => ({ ...prev, sub_division: event.target.value }))}
              className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                errors.sub_division ? "border-red-400 bg-red-500/10" : "border-white/10 bg-slate-900/80"
              }`}
            />
            {errors.sub_division ? (
              <p className="mt-1 text-xs text-red-300">{errors.sub_division}</p>
            ) : null}
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Account Code
            </label>
            <select
              value={form.account_code}
              onChange={(event) => setForm((prev) => ({ ...prev, account_code: event.target.value }))}
              className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                errors.account_code ? "border-red-400 bg-red-500/10" : "border-white/10 bg-slate-900/80"
              }`}
            >
              <option value="">Select</option>
              <option value="Spill">Spill</option>
              <option value="New">New</option>
            </select>
            {errors.account_code ? (
              <p className="mt-1 text-xs text-red-300">{errors.account_code}</p>
            ) : null}
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Number of Works
            </label>
            <input
              value={form.number_of_works}
              onChange={(event) => setForm((prev) => ({ ...prev, number_of_works: event.target.value }))}
              className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                errors.number_of_works ? "border-red-400 bg-red-500/10" : "border-white/10 bg-slate-900/80"
              }`}
            />
            {errors.number_of_works ? (
              <p className="mt-1 text-xs text-red-300">{errors.number_of_works}</p>
            ) : null}
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Estimate Amount
            </label>
            <input
              value={form.estimate_amount}
              onChange={(event) => setForm((prev) => ({ ...prev, estimate_amount: event.target.value }))}
              className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                errors.estimate_amount ? "border-red-400 bg-red-500/10" : "border-white/10 bg-slate-900/80"
              }`}
            />
            {errors.estimate_amount ? (
              <p className="mt-1 text-xs text-red-300">{errors.estimate_amount}</p>
            ) : null}
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Agreement Amount
            </label>
            <input
              value={form.agreement_amount}
              onChange={(event) => setForm((prev) => ({ ...prev, agreement_amount: event.target.value }))}
              className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                errors.agreement_amount ? "border-red-400 bg-red-500/10" : "border-white/10 bg-slate-900/80"
              }`}
            />
            {errors.agreement_amount ? (
              <p className="mt-1 text-xs text-red-300">{errors.agreement_amount}</p>
            ) : null}
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Expenditure up to 31-03-2025
            </label>
            <input
              value={form.exp_upto_31_03_2025}
              onChange={(event) => setForm((prev) => ({ ...prev, exp_upto_31_03_2025: event.target.value }))}
              className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                errors.exp_upto_31_03_2025 ? "border-red-400 bg-red-500/10" : "border-white/10 bg-slate-900/80"
              }`}
            />
            {errors.exp_upto_31_03_2025 ? (
              <p className="mt-1 text-xs text-red-300">{errors.exp_upto_31_03_2025}</p>
            ) : null}
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Expenditure up to Last Month
            </label>
            <input
              value={form.exp_upto_last_month}
              onChange={(event) => setForm((prev) => ({ ...prev, exp_upto_last_month: event.target.value }))}
              className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                errors.exp_upto_last_month ? "border-red-400 bg-red-500/10" : "border-white/10 bg-slate-900/80"
              }`}
            />
            {errors.exp_upto_last_month ? (
              <p className="mt-1 text-xs text-red-300">{errors.exp_upto_last_month}</p>
            ) : null}
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Expenditure During This Month
            </label>
            <input
              value={form.exp_during_this_month}
              onChange={(event) => setForm((prev) => ({ ...prev, exp_during_this_month: event.target.value }))}
              className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                errors.exp_during_this_month ? "border-red-400 bg-red-500/10" : "border-white/10 bg-slate-900/80"
              }`}
            />
            {errors.exp_during_this_month ? (
              <p className="mt-1 text-xs text-red-300">{errors.exp_during_this_month}</p>
            ) : null}
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-slate-400">
              Number of Works Completed
            </label>
            <input
              value={form.works_completed}
              onChange={(event) => setForm((prev) => ({ ...prev, works_completed: event.target.value }))}
              className={`mt-2 w-full rounded-xl border px-4 py-2 text-sm text-white ${
                errors.works_completed ? "border-red-400 bg-red-500/10" : "border-white/10 bg-slate-900/80"
              }`}
            />
            {errors.works_completed ? (
              <p className="mt-1 text-xs text-red-300">{errors.works_completed}</p>
            ) : null}
          </div>
        </div>

        <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4 text-xs text-slate-300">
          <p className="uppercase tracking-widest text-slate-400">Computed Preview</p>
          <div className="mt-2 space-y-1">
            <div>
              Balance Amount as on 01-04-2025: {formatFloat(computed.balanceAmount)}
            </div>
            <div>Total Expenditure During the Year: {formatFloat(computed.totalYear)}</div>
            <div>
              Total Value Work Done from Beginning: {formatFloat(computed.totalValue)}
            </div>
            <div>Balance Number of Works: {formatInt(computed.balanceWorks)}</div>
          </div>
        </div>

        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="w-full rounded-xl bg-orange-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-60"
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </Modal>
  );
}
