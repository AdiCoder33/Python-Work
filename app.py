import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlencode
import tkinter as tk
from tkinter import filedialog, ttk, messagebox


API_BASE_URL = os.getenv("CAPITAL_WORKS_API", "http://localhost:8000")


FORM_COLUMN_DEFS = [
    ("S. No.", "sno", "int"),
    ("Sub-Division", "sub_division", "text"),
    ("Account Code", "account_code", "text"),
    ("Number of Works", "number_of_works", "int"),
    ("Estimate Amount", "estimate_amount", "float"),
    ("Agreement Amount", "agreement_amount", "float"),
    ("Expenditure up to 31-03-2025", "exp_upto_31_03_2025", "float"),
    ("Balance Amount as on 01-04-2025", "balance_amount_as_on_01_04_2025", "float"),
    ("Expenditure up to Last Month", "exp_upto_last_month", "float"),
    ("Expenditure During This Month", "exp_during_this_month", "float"),
    ("Total Expenditure During the Year", "total_exp_during_year", "float"),
    (
        "Total Value of Work Done from the Beginning",
        "total_value_work_done_from_beginning",
        "float",
    ),
    ("Number of Works Completed", "works_completed", "int"),
    ("Balance Number of Works", "balance_works", "int"),
]

ADMIN_COLUMN_DEFS = FORM_COLUMN_DEFS + [
    ("Created By", "created_by", "text"),
    ("Created At", "created_at", "text"),
]

SUMMARY_FIELDS = [
    (label, key, col_type)
    for label, key, col_type in ADMIN_COLUMN_DEFS
    if col_type in ("int", "float") and key != "sno"
]


def parse_float(text):
    text = text.strip()
    if text == "":
        return None, True, True
    try:
        value = float(text)
    except ValueError:
        return None, False, False
    if value < 0:
        return None, False, False
    return value, True, False


def parse_int(text):
    text = text.strip()
    if text == "":
        return None, True, True
    try:
        value = int(text)
    except ValueError:
        return None, False, False
    if value < 0:
        return None, False, False
    return value, True, False


def format_float(value):
    return f"{value:.2f}"


def extract_error_message(raw_text):
    if not raw_text:
        return "Request failed."
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text
    if isinstance(payload, dict):
        error = payload.get("error")
        trace_id = payload.get("trace_id")
        if isinstance(error, dict):
            message = error.get("message") or "Request failed."
            if trace_id:
                return f"{message} (trace: {trace_id})"
            return message
        detail = payload.get("detail")
        if isinstance(detail, list):
            messages = [item.get("msg", "") for item in detail if isinstance(item, dict)]
            detail = "; ".join([msg for msg in messages if msg])
        return detail or raw_text
    return raw_text


def api_request(method, path, data=None, token=None, params=None, timeout=10):
    base_url = API_BASE_URL.rstrip("/")
    url = f"{base_url}{path}"
    if params:
        query = urlencode(
            {key: value for key, value in params.items() if value not in (None, "")}
        )
        if query:
            url = f"{url}?{query}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return True, {}
            return True, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return False, extract_error_message(raw) or f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return False, f"Unable to reach server: {exc.reason}"


def api_download(path, token=None, params=None, timeout=20):
    base_url = API_BASE_URL.rstrip("/")
    url = f"{base_url}{path}"
    if params:
        query = urlencode(
            {key: value for key, value in params.items() if value not in (None, "")}
        )
        if query:
            url = f"{url}?{query}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
            disposition = response.headers.get("Content-Disposition", "")
            filename = None
            if "filename=" in disposition:
                filename = disposition.split("filename=")[-1].strip().strip('"')
            return True, data, filename
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return False, extract_error_message(raw) or f"HTTP {exc.code}", None
    except urllib.error.URLError as exc:
        return False, f"Unable to reach server: {exc.reason}", None


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)

        self.inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas_window = canvas.create_window((0, 0), window=self.inner, anchor="nw")

        def on_canvas_configure(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.inner.bind("<Enter>", lambda e: self._bind_mousewheel(canvas))
        self.inner.bind("<Leave>", lambda e: self._unbind_mousewheel(canvas))

    def _bind_mousewheel(self, canvas):
        canvas.bind_all(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

    def _unbind_mousewheel(self, canvas):
        canvas.unbind_all("<MouseWheel>")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Capital Works - Above Rs. 50.00 Lakhs")
        self.root.geometry("1100x700")
        self.root.minsize(800, 600)

        self.token = None
        self.current_user = None
        self.current_role = None

        self.container = ttk.Frame(root)
        self.container.pack(fill="both", expand=True)
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        self.frames = {}
        for FrameClass in (LoginFrame, UserFormFrame, AdminFrame):
            frame = FrameClass(self.container, self)
            self.frames[FrameClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("LoginFrame")

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

    def set_auth(self, token, username, role):
        self.token = token
        self.current_user = username
        self.current_role = role

    def clear_auth(self):
        self.token = None
        self.current_user = None
        self.current_role = None

    def api_request(self, method, path, data=None, params=None, use_auth=True):
        token = self.token if use_auth else None
        return api_request(method, path, data=data, params=params, token=token)


class LoginFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=20)
        self.app = app

        title = ttk.Label(
            self, text="Login", font=("Segoe UI", 16, "bold")
        )
        title.pack(pady=(0, 20))

        form = ttk.Frame(self)
        form.pack()

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        ttk.Label(form, text="Username").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(form, textvariable=self.username_var, width=30).grid(
            row=0, column=1, pady=5, padx=10
        )

        ttk.Label(form, text="Password").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(form, textvariable=self.password_var, show="*", width=30).grid(
            row=1, column=1, pady=5, padx=10
        )

        ttk.Button(self, text="Login", command=self.handle_login).pack(pady=10)

    def handle_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        if not username or not password:
            messagebox.showerror(
                "Validation Error", "Username and Password are required."
            )
            return

        ok, result = self.app.api_request(
            "POST",
            "/auth/login",
            data={"username": username, "password": password},
            use_auth=False,
        )
        if not ok:
            messagebox.showerror("Login Failed", result)
            return

        self.app.set_auth(
            token=result.get("access_token"),
            username=result.get("username"),
            role=result.get("role"),
        )

        if result.get("role") == "admin":
            self.app.show_frame("AdminFrame")
        else:
            self.app.show_frame("UserFormFrame")

    def on_show(self):
        self.app.clear_auth()
        self.password_var.set("")


class UserFormFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        header = ttk.Frame(self, padding=(20, 20, 20, 0))
        header.pack(fill="x")
        ttk.Label(
            header,
            text="Capital Works - ABOVE Rs. 50.00 Lakhs",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")

        body = ScrollableFrame(self)
        body.pack(fill="both", expand=True, padx=20, pady=10)

        form = body.inner
        form.columnconfigure(1, weight=1)

        self.field_vars = {
            "sno": tk.StringVar(),
            "sub_division": tk.StringVar(),
            "account_code": tk.StringVar(),
            "number_of_works": tk.StringVar(),
            "estimate_amount": tk.StringVar(),
            "agreement_amount": tk.StringVar(),
            "exp_upto_31_03_2025": tk.StringVar(),
            "balance_amount_as_on_01_04_2025": tk.StringVar(),
            "exp_upto_last_month": tk.StringVar(),
            "exp_during_this_month": tk.StringVar(),
            "total_exp_during_year": tk.StringVar(),
            "total_value_work_done_from_beginning": tk.StringVar(),
            "works_completed": tk.StringVar(),
            "balance_works": tk.StringVar(),
        }

        readonly_fields = {
            "sno",
            "balance_amount_as_on_01_04_2025",
            "total_exp_during_year",
            "total_value_work_done_from_beginning",
            "balance_works",
        }

        input_row = 0
        self.inputs = {}
        for label, key, _ in FORM_COLUMN_DEFS:
            ttk.Label(form, text=label).grid(
                row=input_row, column=0, sticky="w", pady=6, padx=(0, 10)
            )
            if key == "account_code":
                entry = ttk.Combobox(
                    form,
                    textvariable=self.field_vars[key],
                    values=("Spill", "New"),
                    state="readonly",
                    width=27,
                )
            else:
                entry = ttk.Entry(form, textvariable=self.field_vars[key], width=30)
                if key in readonly_fields:
                    entry.configure(state="readonly")

            entry.grid(row=input_row, column=1, sticky="ew", pady=6)
            self.inputs[key] = entry
            input_row += 1

        button_frame = ttk.Frame(self, padding=20)
        button_frame.pack(fill="x")

        ttk.Button(button_frame, text="Submit", command=self.submit).pack(
            side="left", padx=5
        )
        ttk.Button(button_frame, text="Clear", command=self.clear_inputs).pack(
            side="left", padx=5
        )
        ttk.Button(
            button_frame, text="Go to Admin View", command=self.go_to_admin
        ).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Exit", command=self.app.root.destroy).pack(
            side="right", padx=5
        )

        for key in (
            "agreement_amount",
            "exp_upto_31_03_2025",
            "exp_upto_last_month",
            "exp_during_this_month",
            "number_of_works",
            "works_completed",
        ):
            self.field_vars[key].trace_add("write", self.update_computed)

    def on_show(self):
        self.field_vars["sno"].set("Auto")
        self.update_computed()

    def update_computed(self, *_):
        agreement, ok_agreement, empty_agreement = parse_float(
            self.field_vars["agreement_amount"].get()
        )
        exp_31, ok_exp_31, empty_exp_31 = parse_float(
            self.field_vars["exp_upto_31_03_2025"].get()
        )
        exp_last, ok_exp_last, empty_exp_last = parse_float(
            self.field_vars["exp_upto_last_month"].get()
        )
        exp_this, ok_exp_this, empty_exp_this = parse_float(
            self.field_vars["exp_during_this_month"].get()
        )
        works, ok_works, empty_works = parse_int(
            self.field_vars["number_of_works"].get()
        )
        completed, ok_completed, empty_completed = parse_int(
            self.field_vars["works_completed"].get()
        )

        if ok_agreement and ok_exp_31 and not (empty_agreement or empty_exp_31):
            balance_amount = agreement - exp_31
            self.field_vars["balance_amount_as_on_01_04_2025"].set(
                format_float(balance_amount)
            )
        else:
            self.field_vars["balance_amount_as_on_01_04_2025"].set("")

        if ok_exp_last and ok_exp_this and not (empty_exp_last or empty_exp_this):
            total_exp_year = exp_last + exp_this
            self.field_vars["total_exp_during_year"].set(format_float(total_exp_year))
        else:
            self.field_vars["total_exp_during_year"].set("")

        if (
            ok_exp_31
            and ok_exp_last
            and ok_exp_this
            and not (empty_exp_31 or empty_exp_last or empty_exp_this)
        ):
            total_exp_year = exp_last + exp_this
            total_value = exp_31 + total_exp_year
            self.field_vars["total_value_work_done_from_beginning"].set(
                format_float(total_value)
            )
        else:
            self.field_vars["total_value_work_done_from_beginning"].set("")

        if ok_works and ok_completed and not (empty_works or empty_completed):
            balance_works = works - completed
            if balance_works >= 0:
                self.field_vars["balance_works"].set(str(balance_works))
            else:
                self.field_vars["balance_works"].set("")
        else:
            self.field_vars["balance_works"].set("")

    def submit(self):
        errors = []

        sub_division = self.field_vars["sub_division"].get().strip()
        account_code = self.field_vars["account_code"].get().strip()
        if not sub_division:
            errors.append("Sub-Division is required.")
        if not account_code:
            errors.append("Account Code is required.")

        num_works, ok_works, empty_works = parse_int(
            self.field_vars["number_of_works"].get()
        )
        num_completed, ok_completed, empty_completed = parse_int(
            self.field_vars["works_completed"].get()
        )

        if empty_works:
            errors.append("Number of Works is required.")
        elif not ok_works:
            errors.append("Number of Works must be a non-negative integer.")

        if empty_completed:
            errors.append("Number of Works Completed is required.")
        elif not ok_completed:
            errors.append("Number of Works Completed must be a non-negative integer.")

        float_fields = [
            ("Estimate Amount", "estimate_amount"),
            ("Agreement Amount", "agreement_amount"),
            ("Expenditure up to 31-03-2025", "exp_upto_31_03_2025"),
            ("Expenditure up to Last Month", "exp_upto_last_month"),
            ("Expenditure During This Month", "exp_during_this_month"),
        ]
        parsed_floats = {}
        for label, key in float_fields:
            value, ok, empty = parse_float(self.field_vars[key].get())
            if empty:
                errors.append(f"{label} is required.")
            elif not ok:
                errors.append(f"{label} must be a non-negative number.")
            else:
                parsed_floats[key] = value

        if (
            ok_works
            and ok_completed
            and not (empty_works or empty_completed)
            and num_completed > num_works
        ):
            errors.append("Number of Works Completed cannot exceed Number of Works.")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return

        agreement_amount = parsed_floats["agreement_amount"]
        exp_up_to_31 = parsed_floats["exp_upto_31_03_2025"]
        exp_last_month = parsed_floats["exp_upto_last_month"]
        exp_this_month = parsed_floats["exp_during_this_month"]

        balance_amount = agreement_amount - exp_up_to_31
        if balance_amount < 0:
            errors.append("Balance Amount as on 01-04-2025 cannot be negative.")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return

        payload = {
            "sub_division": sub_division,
            "account_code": account_code,
            "number_of_works": num_works,
            "estimate_amount": parsed_floats["estimate_amount"],
            "agreement_amount": agreement_amount,
            "exp_upto_31_03_2025": exp_up_to_31,
            "exp_upto_last_month": exp_last_month,
            "exp_during_this_month": exp_this_month,
            "works_completed": num_completed,
        }

        ok, result = self.app.api_request("POST", "/tasks", data=payload)
        if not ok:
            messagebox.showerror("Submit Failed", result)
            return

        sno = result.get("sno")
        message = "Record submitted."
        if sno is not None:
            message = f"Record submitted. S. No: {sno}"
        messagebox.showinfo("Success", message)
        self.clear_inputs()
        self.field_vars["sno"].set("Auto")

    def clear_inputs(self):
        for key in self.field_vars:
            if key in (
                "sno",
                "balance_amount_as_on_01_04_2025",
                "total_exp_during_year",
                "total_value_work_done_from_beginning",
                "balance_works",
            ):
                continue
            self.field_vars[key].set("")
        self.field_vars["sno"].set("Auto")
        self.update_computed()

    def go_to_admin(self):
        if self.app.current_role != "admin":
            messagebox.showerror("Access Denied", "Admin access is required.")
            return
        self.app.show_frame("AdminFrame")


class AdminFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.current_records = []
        self.total_pages = 1
        self.total_items = 0
        self.refresh_job = None
        self.summary_dirty = True

        self.page_var = tk.IntVar(value=1)
        self.page_info_var = tk.StringVar(value="Page 1 of 1")

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(
            header,
            text="Admin Dashboard",
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")

        self.notebook = ttk.Notebook(self)
        self.records_tab = ttk.Frame(self.notebook)
        self.summary_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.records_tab, text="Records")
        self.notebook.add(self.summary_tab, text="Summary")
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        filter_frame = ttk.LabelFrame(self.records_tab, text="Filters", padding=10)
        filter_frame.pack(fill="x", pady=(0, 10))

        self.subdivision_filter_var = tk.StringVar()
        self.account_filter_var = tk.StringVar(value="All")
        self.date_from_var = tk.StringVar()
        self.date_to_var = tk.StringVar()

        self.sort_label_by_key = {key: label for label, key, _ in ADMIN_COLUMN_DEFS}
        self.sort_key_by_label = {label: key for label, key, _ in ADMIN_COLUMN_DEFS}
        sort_labels = [label for label, _, _ in ADMIN_COLUMN_DEFS]
        self.sort_by_var = tk.StringVar(value=self.sort_label_by_key.get("sno", sort_labels[0]))
        self.order_var = tk.StringVar(value="asc")
        self.page_size_var = tk.StringVar(value="50")

        ttk.Label(filter_frame, text="Sub-Division").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ttk.Entry(filter_frame, textvariable=self.subdivision_filter_var, width=30).grid(
            row=0, column=1, sticky="ew", pady=4
        )

        ttk.Label(filter_frame, text="Account Code").grid(
            row=0, column=2, sticky="w", padx=(12, 8), pady=4
        )
        ttk.Combobox(
            filter_frame,
            textvariable=self.account_filter_var,
            values=("All", "Spill", "New"),
            state="readonly",
            width=12,
        ).grid(row=0, column=3, sticky="w", pady=4)

        ttk.Label(filter_frame, text="Date From (YYYY-MM-DD)").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ttk.Entry(filter_frame, textvariable=self.date_from_var, width=18).grid(
            row=1, column=1, sticky="w", pady=4
        )
        ttk.Label(filter_frame, text="Date To (YYYY-MM-DD)").grid(
            row=1, column=2, sticky="w", padx=(12, 8), pady=4
        )
        ttk.Entry(filter_frame, textvariable=self.date_to_var, width=18).grid(
            row=1, column=3, sticky="w", pady=4
        )

        ttk.Label(filter_frame, text="Sort By").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ttk.Combobox(
            filter_frame,
            textvariable=self.sort_by_var,
            values=sort_labels,
            state="readonly",
            width=30,
        ).grid(row=2, column=1, sticky="w", pady=4)

        ttk.Label(filter_frame, text="Order").grid(
            row=2, column=2, sticky="w", padx=(12, 8), pady=4
        )
        ttk.Combobox(
            filter_frame,
            textvariable=self.order_var,
            values=("asc", "desc"),
            state="readonly",
            width=10,
        ).grid(row=2, column=3, sticky="w", pady=4)

        ttk.Label(filter_frame, text="Page Size").grid(
            row=2, column=4, sticky="w", padx=(12, 8), pady=4
        )
        ttk.Combobox(
            filter_frame,
            textvariable=self.page_size_var,
            values=("50", "100", "200", "500"),
            state="readonly",
            width=10,
        ).grid(row=2, column=5, sticky="w", pady=4)

        filter_buttons = ttk.Frame(filter_frame)
        filter_buttons.grid(row=3, column=0, columnspan=6, sticky="ew", pady=(8, 0))
        ttk.Button(filter_buttons, text="Refresh", command=self.refresh_all).pack(
            side="left", padx=5
        )
        ttk.Button(filter_buttons, text="Clear Filters", command=self.clear_filters).pack(
            side="left", padx=5
        )
        ttk.Button(filter_buttons, text="Export", command=self.export_tasks).pack(
            side="right", padx=5
        )

        filter_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(3, weight=1)

        table_frame = ttk.Frame(self.records_tab)
        table_frame.pack(fill="both", expand=True)

        column_keys = [col[1] for col in ADMIN_COLUMN_DEFS]
        self.tree = ttk.Treeview(table_frame, columns=column_keys, show="headings")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        width_map = {
            "sno": 60,
            "sub_division": 160,
            "account_code": 110,
            "number_of_works": 140,
            "estimate_amount": 140,
            "agreement_amount": 140,
            "exp_upto_31_03_2025": 190,
            "balance_amount_as_on_01_04_2025": 210,
            "exp_upto_last_month": 180,
            "exp_during_this_month": 190,
            "total_exp_during_year": 220,
            "total_value_work_done_from_beginning": 280,
            "works_completed": 180,
            "balance_works": 170,
            "created_by": 140,
            "created_at": 200,
        }

        type_map = {key: col_type for _, key, col_type in ADMIN_COLUMN_DEFS}
        for label, key, _ in ADMIN_COLUMN_DEFS:
            self.tree.heading(
                key,
                text=label,
                command=lambda k=key: self.handle_header_sort(k),
            )
            anchor = "e" if type_map[key] in ("int", "float") else "w"
            self.tree.column(
                key, width=width_map.get(key, 140), anchor=anchor, stretch=False
            )

        pagination_frame = ttk.Frame(self.records_tab, padding=(0, 8))
        pagination_frame.pack(fill="x")
        self.prev_button = ttk.Button(
            pagination_frame, text="Prev", command=self.prev_page
        )
        self.prev_button.pack(side="left", padx=5)
        ttk.Label(pagination_frame, textvariable=self.page_info_var).pack(
            side="left", padx=10
        )
        self.next_button = ttk.Button(
            pagination_frame, text="Next", command=self.next_page
        )
        self.next_button.pack(side="left", padx=5)

        summary_container = ttk.Frame(self.summary_tab, padding=10)
        summary_container.pack(fill="both", expand=True)

        grand_frame = ttk.LabelFrame(summary_container, text="Grand Totals", padding=10)
        grand_frame.pack(fill="x")
        self.grand_total_vars = {}
        for row, (label, key, col_type) in enumerate(SUMMARY_FIELDS):
            ttk.Label(grand_frame, text=label).grid(
                row=row, column=0, sticky="w", pady=2
            )
            var = tk.StringVar(value="0")
            self.grand_total_vars[key] = (var, col_type)
            ttk.Label(grand_frame, textvariable=var).grid(
                row=row, column=1, sticky="e", pady=2
            )
        grand_frame.columnconfigure(1, weight=1)

        sub_frame = ttk.LabelFrame(summary_container, text="Sub-Division Totals", padding=10)
        sub_frame.pack(fill="both", expand=True, pady=(10, 0))

        summary_columns = ["sub_division", "account_code"] + [
            key for _, key, _ in SUMMARY_FIELDS
        ]
        self.summary_tree = ttk.Treeview(
            sub_frame, columns=summary_columns, show="headings"
        )
        summary_vsb = ttk.Scrollbar(sub_frame, orient="vertical", command=self.summary_tree.yview)
        summary_hsb = ttk.Scrollbar(sub_frame, orient="horizontal", command=self.summary_tree.xview)
        self.summary_tree.configure(yscrollcommand=summary_vsb.set, xscrollcommand=summary_hsb.set)

        self.summary_tree.grid(row=0, column=0, sticky="nsew")
        summary_vsb.grid(row=0, column=1, sticky="ns")
        summary_hsb.grid(row=1, column=0, sticky="ew")
        sub_frame.columnconfigure(0, weight=1)
        sub_frame.rowconfigure(0, weight=1)

        self.summary_tree.heading("sub_division", text="Sub-Division")
        self.summary_tree.heading("account_code", text="Account Code")
        self.summary_tree.column("sub_division", width=160, anchor="w", stretch=False)
        self.summary_tree.column("account_code", width=120, anchor="w", stretch=False)
        for label, key, col_type in SUMMARY_FIELDS:
            self.summary_tree.heading(key, text=label)
            anchor = "e" if col_type in ("int", "float") else "w"
            self.summary_tree.column(key, width=140, anchor=anchor, stretch=False)

        button_frame = ttk.Frame(self, padding=(0, 10))
        button_frame.pack(fill="x")
        ttk.Button(
            button_frame,
            text="Back to User Form",
            command=lambda: self.app.show_frame("UserFormFrame"),
        ).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Logout", command=self.logout).pack(
            side="right", padx=5
        )

        for var in (
            self.subdivision_filter_var,
            self.account_filter_var,
            self.date_from_var,
            self.date_to_var,
            self.sort_by_var,
            self.order_var,
        ):
            var.trace_add("write", lambda *_: self.schedule_refresh(reset_page=True))
        self.page_size_var.trace_add("write", lambda *_: self.schedule_refresh(reset_page=True))

    def on_show(self):
        if self.app.current_role != "admin":
            messagebox.showerror("Access Denied", "Admin access is required.")
            self.app.show_frame("UserFormFrame")
            return
        self.page_var.set(1)
        self.summary_dirty = True
        self.load_tasks(page=1)
        if self.is_summary_active():
            self.refresh_summary()

    def on_tab_change(self, _event):
        if self.is_summary_active() and self.summary_dirty:
            self.refresh_summary()

    def is_summary_active(self):
        return self.notebook.index("current") == self.notebook.index(self.summary_tab)

    def clear_filters(self):
        self.subdivision_filter_var.set("")
        self.account_filter_var.set("All")
        self.date_from_var.set("")
        self.date_to_var.set("")
        self.sort_by_var.set(self.sort_label_by_key.get("sno", self.sort_by_var.get()))
        self.order_var.set("asc")
        self.page_size_var.set("50")
        self.page_var.set(1)
        self.schedule_refresh(reset_page=True)

    def refresh_all(self):
        self.schedule_refresh(reset_page=False)

    def logout(self):
        self.clear_filters()
        self.app.clear_auth()
        self.app.show_frame("LoginFrame")

    def build_filter_params(self):
        params = {}
        sub_division = self.subdivision_filter_var.get().strip()
        account_code = self.account_filter_var.get()
        date_from = self.date_from_var.get().strip()
        date_to = self.date_to_var.get().strip()

        if sub_division:
            params["sub_division"] = sub_division
        if account_code in ("Spill", "New"):
            params["account_code"] = account_code
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return params

    def build_task_params(self, page=None):
        params = self.build_filter_params()
        sort_label = self.sort_by_var.get()
        params["sort_by"] = self.sort_key_by_label.get(sort_label, "sno")
        params["order"] = self.order_var.get()
        try:
            page_size = int(self.page_size_var.get())
        except ValueError:
            page_size = 50
        params["page_size"] = page_size
        params["page"] = page if page is not None else self.page_var.get()
        return params

    def schedule_refresh(self, reset_page=True):
        if self.refresh_job:
            self.after_cancel(self.refresh_job)

        def run():
            self.refresh_job = None
            if reset_page:
                self.page_var.set(1)
            self.load_tasks(page=self.page_var.get())
            self.summary_dirty = True
            if self.is_summary_active():
                self.refresh_summary()

        self.refresh_job = self.after(350, run)

    def handle_header_sort(self, col_key):
        label = self.sort_label_by_key.get(col_key, self.sort_by_var.get())
        if self.sort_by_var.get() == label:
            self.order_var.set("desc" if self.order_var.get() == "asc" else "asc")
        else:
            self.sort_by_var.set(label)
            self.order_var.set("asc")
        self.schedule_refresh(reset_page=True)

    def load_tasks(self, page=1):
        ok, result = self.app.api_request(
            "GET", "/admin/tasks", params=self.build_task_params(page=page)
        )
        if not ok:
            messagebox.showerror("Load Failed", result)
            self.current_records = []
            self.total_pages = 1
            self.total_items = 0
            self.page_info_var.set("Page 1 of 1")
            self.refresh_tree()
            return

        items = result.get("items", []) if isinstance(result, dict) else []
        self.current_records = items
        self.page_var.set(result.get("page", page))
        self.total_pages = result.get("total_pages", 1)
        self.total_items = result.get("total_items", 0)
        self.refresh_tree()
        self.update_pagination()

    def update_pagination(self):
        page = self.page_var.get()
        self.page_info_var.set(
            f"Page {page} of {self.total_pages} (Total {self.total_items})"
        )
        if page <= 1:
            self.prev_button.state(["disabled"])
        else:
            self.prev_button.state(["!disabled"])
        if page >= self.total_pages:
            self.next_button.state(["disabled"])
        else:
            self.next_button.state(["!disabled"])

    def prev_page(self):
        page = self.page_var.get()
        if page > 1:
            self.load_tasks(page=page - 1)

    def next_page(self):
        page = self.page_var.get()
        if page < self.total_pages:
            self.load_tasks(page=page + 1)

    def refresh_summary(self):
        ok, result = self.app.api_request(
            "GET", "/admin/summary", params=self.build_filter_params()
        )
        if not ok:
            messagebox.showerror("Summary Failed", result)
            return
        if not isinstance(result, dict):
            return

        grand_totals = result.get("grand_totals", {})
        for key, (var, col_type) in self.grand_total_vars.items():
            value = grand_totals.get(key, 0)
            if col_type == "float":
                var.set(format_float(float(value)))
            else:
                var.set(str(int(value)))

        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)

        for sub_item in result.get("by_sub_division", []):
            sub_division = sub_item.get("sub_division", "")
            totals = sub_item.get("totals", {})
            self.insert_summary_row(sub_division, "All", totals)
            for account_item in sub_item.get("by_account_code", []):
                account_code = account_item.get("account_code", "")
                account_totals = account_item.get("totals", {})
                self.insert_summary_row(sub_division, account_code, account_totals)

        self.summary_dirty = False

    def insert_summary_row(self, sub_division, account_code, totals):
        values = [sub_division, account_code]
        for _label, key, col_type in SUMMARY_FIELDS:
            value = totals.get(key, 0)
            if col_type == "float":
                values.append(format_float(float(value)))
            else:
                values.append(str(int(value)))
        self.summary_tree.insert("", "end", values=values)

    def export_tasks(self):
        params = self.build_filter_params()
        sort_label = self.sort_by_var.get()
        params["sort_by"] = self.sort_key_by_label.get(sort_label, "sno")
        params["order"] = self.order_var.get()

        ok, data, filename = api_download("/admin/export", token=self.app.token, params=params)
        if not ok:
            messagebox.showerror("Export Failed", data)
            return

        initial_name = filename or "tasks_export.xlsx"
        path = filedialog.asksaveasfilename(
            title="Save Export",
            defaultextension=".xlsx",
            initialfile=initial_name,
            filetypes=[("Excel Files", "*.xlsx")],
        )
        if not path:
            return
        with open(path, "wb") as handle:
            handle.write(data)
        messagebox.showinfo("Export Complete", f"Saved export to {path}.")

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        type_map = {key: col_type for _, key, col_type in ADMIN_COLUMN_DEFS}
        for record in self.current_records:
            values = []
            for _, key, _ in ADMIN_COLUMN_DEFS:
                value = record.get(key, "")
                if type_map[key] == "float":
                    values.append(format_float(float(value)) if value not in ("", None) else "")
                elif type_map[key] == "int":
                    values.append(str(int(value)) if value not in ("", None) else "")
                else:
                    values.append("" if value is None else str(value))
            self.tree.insert("", "end", values=values)


def main():
    root = tk.Tk()
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
