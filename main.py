import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests


BACKEND_URL = "http://127.0.0.1:8000"


class WorkFormApp:
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("Work Progress Form")
        self.master.geometry("1400x820")
        self.master.resizable(False, False)
        self.s_no_counter = 1
        self.jwt_token: str | None = None
        self.user_role: str | None = None
        self.records_data: list[dict] = []
        self.sort_direction: dict[str, bool] = {}

        self._build_style()
        self._init_variables()
        self._build_layout()
        self._wire_traces()
        self._update_calculations()

    def _build_style(self) -> None:
        style = ttk.Style(self.master)
        style.theme_use("clam")
        style.configure("Header.TLabel", background="#f0f0f0", padding=(4, 6), anchor="center")
        style.configure("Cell.TEntry", padding=(3, 4))
        style.configure("Cell.TCombobox", padding=(3, 4))
        style.configure("Total.Treeview", font=("", 10, "bold"))
        style.configure("SubTotal.Treeview", font=("", 9, "bold"))

    def _init_variables(self) -> None:
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.auth_status = tk.StringVar(value="Not authenticated")

        self.s_no = tk.IntVar(value=self.s_no_counter)
        self.sub_division = tk.StringVar()
        self.account_code = tk.StringVar(value="Spill")
        self.num_works = tk.IntVar()
        self.estimate_amount = tk.DoubleVar()
        self.agreement_amount = tk.DoubleVar()
        self.exp_3103 = tk.DoubleVar()
        self.balance_0104 = tk.DoubleVar()
        self.exp_last_month = tk.DoubleVar()
        self.exp_this_month = tk.DoubleVar()
        self.total_year = tk.DoubleVar()
        self.total_from_beginning = tk.DoubleVar()
        self.completed_works = tk.IntVar()
        self.balance_works = tk.IntVar()

    def _build_layout(self) -> None:
        container = ttk.Frame(self.master, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        auth_frame = ttk.LabelFrame(container, text="Authentication", padding=(8, 6))
        auth_frame.grid(row=0, column=0, columnspan=14, sticky="ew", pady=(0, 8))

        ttk.Label(auth_frame, text="Username:").grid(row=0, column=0, padx=4, pady=2, sticky="w")
        ttk.Entry(auth_frame, textvariable=self.username, width=18).grid(row=0, column=1, padx=4, pady=2)
        ttk.Label(auth_frame, text="Password:").grid(row=0, column=2, padx=4, pady=2, sticky="w")
        ttk.Entry(auth_frame, textvariable=self.password, width=18, show="*").grid(row=0, column=3, padx=4, pady=2)
        ttk.Button(auth_frame, text="Login", command=self._handle_login).grid(row=0, column=4, padx=6, pady=2)
        ttk.Label(auth_frame, textvariable=self.auth_status, foreground="#0a6b0a").grid(
            row=0, column=5, padx=6, pady=2, sticky="w"
        )

        headings = [
            "S. No.",
            "Sub-Division",
            "Account Code",
            "Number of Works",
            "Estimate Amount",
            "Agreement Amount",
            "Expenditure up to 31-03-2025",
            "Balance Amount as on 01-04-2025",
            "Expenditure up to Last Month",
            "Expenditure During This Month",
            "Total Expenditure During the Year",
            "Total Value of Work Done from the Beginning",
            "Number of Works Completed",
            "Balance Number of Works",
        ]

        table = ttk.Frame(container)
        table.grid(row=1, column=0, columnspan=14, sticky="nsew")

        for col, text in enumerate(headings):
            ttk.Label(table, text=text, style="Header.TLabel", relief=tk.RIDGE).grid(
                row=0, column=col, sticky="nsew", padx=1, pady=1
            )
            table.grid_columnconfigure(col, weight=1, uniform="col")

        vcmd_int = (self.master.register(self._validate_int), "%P")
        vcmd_float = (self.master.register(self._validate_float), "%P")

        row = 1
        ttk.Label(table, textvariable=self.s_no, relief=tk.SOLID, anchor="center", padding=(6, 4)).grid(
            row=row, column=0, sticky="nsew", padx=1, pady=1
        )

        ttk.Entry(table, textvariable=self.sub_division, width=16, style="Cell.TEntry").grid(
            row=row, column=1, sticky="nsew", padx=1, pady=1
        )

        ttk.Combobox(
            table,
            textvariable=self.account_code,
            values=["Spill", "New"],
            state="readonly",
            width=8,
            style="Cell.TCombobox",
        ).grid(row=row, column=2, sticky="nsew", padx=1, pady=1)

        ttk.Entry(
            table,
            textvariable=self.num_works,
            validate="key",
            validatecommand=vcmd_int,
            width=8,
            style="Cell.TEntry",
        ).grid(row=row, column=3, sticky="nsew", padx=1, pady=1)

        ttk.Entry(
            table,
            textvariable=self.estimate_amount,
            validate="key",
            validatecommand=vcmd_float,
            width=12,
            style="Cell.TEntry",
        ).grid(row=row, column=4, sticky="nsew", padx=1, pady=1)

        ttk.Entry(
            table,
            textvariable=self.agreement_amount,
            validate="key",
            validatecommand=vcmd_float,
            width=12,
            style="Cell.TEntry",
        ).grid(row=row, column=5, sticky="nsew", padx=1, pady=1)

        ttk.Entry(
            table,
            textvariable=self.exp_3103,
            validate="key",
            validatecommand=vcmd_float,
            width=14,
            style="Cell.TEntry",
        ).grid(row=row, column=6, sticky="nsew", padx=1, pady=1)

        self._make_readonly_entry(table, self.balance_0104, row, 7)

        ttk.Entry(
            table,
            textvariable=self.exp_last_month,
            validate="key",
            validatecommand=vcmd_float,
            width=14,
            style="Cell.TEntry",
        ).grid(row=row, column=8, sticky="nsew", padx=1, pady=1)

        ttk.Entry(
            table,
            textvariable=self.exp_this_month,
            validate="key",
            validatecommand=vcmd_float,
            width=14,
            style="Cell.TEntry",
        ).grid(row=row, column=9, sticky="nsew", padx=1, pady=1)

        self._make_readonly_entry(table, self.total_year, row, 10)
        self._make_readonly_entry(table, self.total_from_beginning, row, 11)

        ttk.Entry(
            table,
            textvariable=self.completed_works,
            validate="key",
            validatecommand=vcmd_int,
            width=10,
            style="Cell.TEntry",
        ).grid(row=row, column=12, sticky="nsew", padx=1, pady=1)

        self._make_readonly_entry(table, self.balance_works, row, 13)

        btn_bar = ttk.Frame(table, padding=(0, 10, 0, 0))
        btn_bar.grid(row=2, column=0, columnspan=len(headings), sticky="e")

        ttk.Button(btn_bar, text="Submit", command=self._handle_submit).grid(row=0, column=0, padx=4)
        ttk.Button(btn_bar, text="Clear", command=self._handle_clear).grid(row=0, column=1, padx=4)
        ttk.Button(btn_bar, text="Exit", command=self.master.destroy).grid(row=0, column=2, padx=4)

        # Admin view frame (hidden/disabled for non-admin users)
        admin_frame = ttk.LabelFrame(container, text="Admin View", padding=8)
        admin_frame.grid(row=3, column=0, columnspan=14, sticky="nsew", pady=(12, 0))
        admin_frame.grid_columnconfigure(0, weight=1)
        self.admin_frame = admin_frame

        toolbar = ttk.Frame(admin_frame)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_columnconfigure(5, weight=1)

        self.btn_load = ttk.Button(toolbar, text="Load Records", command=self._fetch_records, state="disabled")
        self.btn_load.grid(row=0, column=0, padx=4, pady=4)

        self.btn_export = ttk.Button(toolbar, text="Export Excel", command=self._export_excel, state="disabled")
        self.btn_export.grid(row=0, column=1, padx=4, pady=4)

        self.view_status = tk.StringVar(value="Admin view disabled (login as Admin)")
        ttk.Label(toolbar, textvariable=self.view_status, foreground="#555").grid(row=0, column=2, padx=6)

        tree_container = ttk.Frame(admin_frame)
        tree_container.grid(row=1, column=0, sticky="nsew")
        admin_frame.grid_rowconfigure(1, weight=1)
        admin_frame.grid_columnconfigure(0, weight=1)

        self.columns = [
            "s_no",
            "sub_division",
            "account_code",
            "num_works",
            "estimate_amount",
            "agreement_amount",
            "exp_3103",
            "balance_0104",
            "exp_last_month",
            "exp_this_month",
            "total_year",
            "total_from_beginning",
            "completed_works",
            "balance_works",
        ]
        column_headers = [
            "S. No.",
            "Sub-Division",
            "Account Code",
            "Number of Works",
            "Estimate Amount",
            "Agreement Amount",
            "Expenditure up to 31-03-2025",
            "Balance Amount as on 01-04-2025",
            "Expenditure up to Last Month",
            "Expenditure During This Month",
            "Total Expenditure During the Year",
            "Total Value of Work Done from the Beginning",
            "Number of Works Completed",
            "Balance Number of Works",
        ]

        self.tree = ttk.Treeview(
            tree_container,
            columns=self.columns,
            show="headings",
            height=12,
        )

        for cid, header in zip(self.columns, column_headers):
            self.tree.heading(cid, text=header, command=lambda c=cid: self._sort_by(c))
            self.tree.column(cid, width=120, anchor="center")

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        self.tree.tag_configure("subtotal", background="#f5f5f5", font=("", 9, "bold"))
        self.tree.tag_configure("grandtotal", background="#e5e5e5", font=("", 10, "bold"))

    def _wire_traces(self) -> None:
        for var in [
            self.estimate_amount,
            self.exp_3103,
            self.exp_last_month,
            self.exp_this_month,
            self.num_works,
            self.completed_works,
        ]:
            var.trace_add("write", lambda *args: self._update_calculations())

    def _make_readonly_entry(self, container: ttk.Frame, var: tk.Variable, row: int, column: int) -> None:
        entry = ttk.Entry(container, textvariable=var, state="readonly", width=14, style="Cell.TEntry")
        entry.grid(row=row, column=column, sticky="nsew", padx=1, pady=1)

    def _parse_float(self, value: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _parse_int(self, value: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _update_calculations(self) -> None:
        estimate = self._parse_float(self.estimate_amount.get())
        exp_3103 = self._parse_float(self.exp_3103.get())
        exp_last = self._parse_float(self.exp_last_month.get())
        exp_this = self._parse_float(self.exp_this_month.get())
        works_total = self._parse_int(self.num_works.get())
        works_done = self._parse_int(self.completed_works.get())

        balance_start = estimate - exp_3103
        total_year = exp_last + exp_this
        total_from_beginning = exp_3103 + total_year
        balance_works = works_total - works_done

        self.balance_0104.set(round(balance_start, 2))
        self.total_year.set(round(total_year, 2))
        self.total_from_beginning.set(round(total_from_beginning, 2))
        self.balance_works.set(balance_works)

    def _handle_login(self) -> None:
        username = self.username.get().strip()
        password = self.password.get().strip()

        if not username or not password:
            messagebox.showerror("Login Failed", "Username and password are required.")
            return

        try:
            resp = requests.post(
                f"{BACKEND_URL}/token", data={"username": username, "password": password}, timeout=10
            )
        except requests.RequestException as exc:
            messagebox.showerror("Login Failed", f"Could not reach server: {exc}")
            return

        if resp.status_code != 200:
            messagebox.showerror("Login Failed", resp.text or "Invalid credentials.")
            return

        data = resp.json()
        token = data.get("access_token")
        role = data.get("role", "User")
        if not token:
            messagebox.showerror("Login Failed", "No token received from server.")
            return

        self.jwt_token = token
        self.user_role = role
        self.auth_status.set(f"Authenticated as {role}")
        self._refresh_admin_controls()
        messagebox.showinfo("Login Successful", f"Authenticated as {role}.")

    def _validate_int(self, proposed: str) -> bool:
        if proposed == "":
            return True
        if proposed.isdigit():
            return True
        self.master.bell()
        return False

    def _validate_float(self, proposed: str) -> bool:
        if proposed in ("", "-", ".", "-."):
            return True
        try:
            float(proposed)
            return True
        except ValueError:
            self.master.bell()
            return False

    def _handle_submit(self) -> None:
        if not self.jwt_token:
            messagebox.showerror("Not Authenticated", "Login before submitting the form.")
            return

        errors = []

        if not self.sub_division.get().strip():
            errors.append("Sub-Division is required.")
        if self.account_code.get() not in ("Spill", "New"):
            errors.append("Account Code must be Spill or New.")
        if self.num_works.get() <= 0:
            errors.append("Number of Works must be greater than zero.")
        if self.completed_works.get() < 0 or self.completed_works.get() > self.num_works.get():
            errors.append("Completed works cannot exceed total works.")

        float_fields = [
            ("Estimate Amount", self.estimate_amount.get()),
            ("Agreement Amount", self.agreement_amount.get()),
            ("Expenditure up to 31-03-2025", self.exp_3103.get()),
            ("Expenditure up to Last Month", self.exp_last_month.get()),
            ("Expenditure During This Month", self.exp_this_month.get()),
        ]

        for label, value in float_fields:
            if self._parse_float(value) < 0:
                errors.append(f"{label} cannot be negative.")

        if errors:
            messagebox.showerror("Validation Failed", "\n".join(errors))
            return

        payload = {
            "s_no": self.s_no.get(),
            "sub_division": self.sub_division.get().strip(),
            "account_code": self.account_code.get(),
            "num_works": self.num_works.get(),
            "estimate_amount": self._parse_float(self.estimate_amount.get()),
            "agreement_amount": self._parse_float(self.agreement_amount.get()),
            "exp_3103": self._parse_float(self.exp_3103.get()),
            "balance_0104": self._parse_float(self.balance_0104.get()),
            "exp_last_month": self._parse_float(self.exp_last_month.get()),
            "exp_this_month": self._parse_float(self.exp_this_month.get()),
            "total_year": self._parse_float(self.total_year.get()),
            "total_from_beginning": self._parse_float(self.total_from_beginning.get()),
            "completed_works": self.completed_works.get(),
            "balance_works": self.balance_works.get(),
        }

        headers = {"Authorization": f"Bearer {self.jwt_token}"}
        try:
            resp = requests.post(f"{BACKEND_URL}/submit", json=payload, headers=headers, timeout=15)
        except requests.RequestException as exc:
            messagebox.showerror("Submission Failed", f"Could not reach server: {exc}")
            return

        if resp.status_code != 200:
            message = resp.text or "Server rejected the submission."
            try:
                data = resp.json()
                message = data.get("detail", message)
            except Exception:
                pass
            messagebox.showerror("Submission Failed", message)
            return

        data = resp.json()
        record = data.get("record") or {}
        self._apply_server_record(record)

        messagebox.showinfo("Submitted", data.get("message", "Record stored on server."))
        self.s_no_counter += 1
        self.s_no.set(self.s_no_counter)
        self._handle_clear(skip_counter=True)

        if self.user_role == "Admin":
            self._fetch_records(silent=True)

    def _apply_server_record(self, record: dict) -> None:
        self.sub_division.set(record.get("sub_division", self.sub_division.get()))
        self.account_code.set(record.get("account_code", self.account_code.get()))
        self.num_works.set(record.get("num_works", self.num_works.get()))
        self.estimate_amount.set(record.get("estimate_amount", self.estimate_amount.get()))
        self.agreement_amount.set(record.get("agreement_amount", self.agreement_amount.get()))
        self.exp_3103.set(record.get("exp_3103", self.exp_3103.get()))
        self.exp_last_month.set(record.get("exp_last_month", self.exp_last_month.get()))
        self.exp_this_month.set(record.get("exp_this_month", self.exp_this_month.get()))
        self.completed_works.set(record.get("completed_works", self.completed_works.get()))

        # Derived fields from server (single source of truth)
        self.balance_0104.set(record.get("balance_0104", self.balance_0104.get()))
        self.total_year.set(record.get("total_year", self.total_year.get()))
        self.total_from_beginning.set(record.get("total_from_beginning", self.total_from_beginning.get()))
        self.balance_works.set(record.get("balance_works", self.balance_works.get()))

    def _refresh_admin_controls(self) -> None:
        if self.user_role == "Admin":
            self.btn_load.config(state="normal")
            self.btn_export.config(state="normal")
            self.view_status.set("Admin view ready. Load records to view.")
        else:
            self.btn_load.config(state="disabled")
            self.btn_export.config(state="disabled")
            self.view_status.set("Admin view disabled (login as Admin)")
            self._clear_tree()

    def _fetch_records(self, silent: bool = False) -> None:
        if self.user_role != "Admin":
            if not silent:
                messagebox.showerror("Access Denied", "Only Admin can view records.")
            return
        if not self.jwt_token:
            if not silent:
                messagebox.showerror("Not Authenticated", "Login before loading records.")
            return
        headers = {"Authorization": f"Bearer {self.jwt_token}"}
        try:
            resp = requests.get(f"{BACKEND_URL}/records", headers=headers, timeout=15)
        except requests.RequestException as exc:
            if not silent:
                messagebox.showerror("Load Failed", f"Could not reach server: {exc}")
            return
        if resp.status_code != 200:
            detail = resp.text
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            if not silent:
                messagebox.showerror("Load Failed", detail)
            return

        data = resp.json().get("records", [])
        self.records_data = data
        self._populate_tree(data)
        self.view_status.set(f"Loaded {len(data)} records")

    def _clear_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _populate_tree(self, records: list[dict]) -> None:
        self._clear_tree()
        for rec in records:
            values = [rec.get(col, "") for col in self.columns]
            self.tree.insert("", "end", values=values)
        self._append_totals(records)

    def _append_totals(self, records: list[dict]) -> None:
        numeric_cols = [
            "num_works",
            "estimate_amount",
            "agreement_amount",
            "exp_3103",
            "balance_0104",
            "exp_last_month",
            "exp_this_month",
            "total_year",
            "total_from_beginning",
            "completed_works",
            "balance_works",
        ]

        subtotals: dict[str, dict[str, float]] = {}
        grand_totals = {col: 0.0 for col in numeric_cols}

        for rec in records:
            code = rec.get("account_code", "Unspecified") or "Unspecified"
            bucket = subtotals.setdefault(code, {col: 0.0 for col in numeric_cols})
            for col in numeric_cols:
                val = rec.get(col, 0) or 0
                bucket[col] += float(val)
                grand_totals[col] += float(val)

        for code, sums in subtotals.items():
            values = [
                "",
                f"Subtotal ({code})",
                code,
            ] + [sums.get(col, 0.0) for col in numeric_cols]
            self.tree.insert("", "end", values=values, tags=("subtotal",))

        grand_values = [
            "",
            "GRAND TOTAL",
            "",
        ] + [grand_totals.get(col, 0.0) for col in numeric_cols]
        self.tree.insert("", "end", values=grand_values, tags=("grandtotal",))

    def _sort_by(self, column: str) -> None:
        if not self.records_data:
            return
        reverse = self.sort_direction.get(column, False)
        self.sort_direction[column] = not reverse

        numeric_cols = {
            "s_no",
            "num_works",
            "estimate_amount",
            "agreement_amount",
            "exp_3103",
            "balance_0104",
            "exp_last_month",
            "exp_this_month",
            "total_year",
            "total_from_beginning",
            "completed_works",
            "balance_works",
        }

        def sort_key(rec: dict):
            val = rec.get(column)
            if column in numeric_cols:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return 0.0
            return str(val).lower() if val is not None else ""

        sorted_records = sorted(self.records_data, key=sort_key, reverse=reverse)
        self.records_data = sorted_records
        self._populate_tree(sorted_records)

    def _export_excel(self) -> None:
        if self.user_role != "Admin":
            messagebox.showerror("Access Denied", "Only Admin can export.")
            return
        if not self.jwt_token:
            messagebox.showerror("Not Authenticated", "Login before exporting.")
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")], title="Save Excel Export"
        )
        if not save_path:
            return
        headers = {"Authorization": f"Bearer {self.jwt_token}"}
        try:
            resp = requests.get(f"{BACKEND_URL}/export", headers=headers, timeout=20)
        except requests.RequestException as exc:
            messagebox.showerror("Export Failed", f"Could not reach server: {exc}")
            return
        if resp.status_code != 200:
            detail = resp.text
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            messagebox.showerror("Export Failed", detail)
            return
        try:
            with open(save_path, "wb") as f:
                f.write(resp.content)
        except OSError as exc:
            messagebox.showerror("Export Failed", f"Could not save file: {exc}")
            return
        messagebox.showinfo("Exported", f"Excel saved to {save_path}")

    def _handle_clear(self, skip_counter: bool = False) -> None:
        self.sub_division.set("")
        self.account_code.set("Spill")
        self.num_works.set(0)
        self.estimate_amount.set(0.0)
        self.agreement_amount.set(0.0)
        self.exp_3103.set(0.0)
        self.exp_last_month.set(0.0)
        self.exp_this_month.set(0.0)
        self.completed_works.set(0)
        self._update_calculations()
        if not skip_counter:
            self.s_no_counter = 1
            self.s_no.set(self.s_no_counter)


def main() -> None:
    root = tk.Tk()
    WorkFormApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
