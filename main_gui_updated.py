import csv
import os
import re
import shutil
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import easyocr
from PIL import Image, ImageTk

APP_TITLE = "Vehicle Number Plate Recognition System"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "authorized_vehicles.csv")
LOG_FILE = os.path.join(BASE_DIR, "scan_log.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "results")
PLATE_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")
OCR_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def clean_plate(text):
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def load_authorized_vehicles():
    authorized = {}
    if not os.path.exists(CSV_FILE):
        return authorized
    with open(CSV_FILE, newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            plate = clean_plate(row.get("plate_number", ""))
            if plate:
                authorized[plate] = row.get("owner_name", "Unknown").strip() or "Unknown"
    return authorized


def append_scan_log(plate, status, confidence):
    file_exists = os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["date_time", "plate_number", "status", "ocr_confidence"])
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            plate,
            status,
            round(confidence, 2) if confidence is not None else "",
        ])



class VehicleRecognitionApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1050x760")
        self.root.minsize(850, 620)
        self.image_path = None
        self.original_image = None
        self.preview_photo = None
        self.reader = None
        self.busy = False
        self.webcam = None
        self.webcam_running = False
        self.webcam_ocr_busy = False
        self.webcam_frame_count = 0
        self.last_logged_plate = ""
        self.last_logged_time = 0.0
        self.webcam_window_name = "Live Vehicle Recognition"

        self.plate_var = tk.StringVar(value="—")
        self.confidence_var = tk.StringVar(value="—")
        self.status_var = tk.StringVar(value="Choose an image or start the webcam.")
        self.owner_var = tk.StringVar(value="—")
        self.file_var = tk.StringVar(value="No image selected")
        self.history_search_var = tk.StringVar()
        self.theme_name = "Dark"

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_dashboard()
        self.refresh_history()
        self.apply_theme()

    def _build_ui(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.root.configure(bg="#111827")

        self.style.configure("TFrame", padding=0)
        self.style.configure("TLabel", font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", font=("Segoe UI", 19, "bold"))
        self.style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        self.style.configure("Metric.TLabel", font=("Segoe UI", 22, "bold"))
        self.style.configure("Result.TLabel", font=("Segoe UI", 16, "bold"))
        self.style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        self.style.configure("Treeview", rowheight=27, font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        heading_box = ttk.Frame(header)
        heading_box.grid(row=0, column=0, sticky="w")
        ttk.Label(heading_box, text="Vehicle Number Plate Recognition", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            heading_box,
            text="Dashboard  •  EasyOCR  •  Live Webcam  •  CSV History",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(3, 0))
        self.theme_button = ttk.Button(header, text="☀ Light Mode", command=self.toggle_theme)
        self.theme_button.grid(row=0, column=1, sticky="e", padx=(10, 0))

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)
        self.dashboard_tab = ttk.Frame(self.notebook, padding=14)
        self.scanner_tab = ttk.Frame(self.notebook, padding=14)
        self.history_tab = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.scanner_tab, text="Scanner")
        self.notebook.add(self.history_tab, text="Scan History")
        self._build_dashboard()
        self._build_scanner()
        self._build_history()

    def _build_dashboard(self):
        ttk.Label(self.dashboard_tab, text="Scan Log Overview", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            self.dashboard_tab,
            text="Summary of vehicle scans recorded by this application",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(0, 16))
        cards = ttk.Frame(self.dashboard_tab)
        cards.pack(fill="x", pady=(0, 14))
        for col in range(3):
            cards.columnconfigure(col, weight=1)
        self.metric_total = tk.StringVar(value="0")
        self.metric_authorized = tk.StringVar(value="0")
        self.metric_unknown = tk.StringVar(value="0")
        self._metric_card(cards, 0, "Total scans", self.metric_total)
        self._metric_card(cards, 1, "Authorized matches", self.metric_authorized)
        self._metric_card(cards, 2, "Not in local list", self.metric_unknown)

        quick = ttk.LabelFrame(self.dashboard_tab, text="Quick Actions", padding=14)
        quick.pack(fill="x", pady=(0, 14))
        ttk.Button(
            quick, text="Open Scanner", style="Action.TButton",
            command=lambda: self.notebook.select(self.scanner_tab),
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            quick, text="Refresh Statistics", style="Action.TButton",
            command=self.refresh_dashboard,
        ).pack(side="left", padx=8)
        ttk.Button(
            quick, text="Open Scan History", style="Action.TButton",
            command=lambda: (self.refresh_history(), self.notebook.select(self.history_tab)),
        ).pack(side="left", padx=8)

        recent_frame = ttk.LabelFrame(self.dashboard_tab, text="Recent Scans", padding=10)
        recent_frame.pack(fill="both", expand=True)
        cols = ("date_time", "plate_number", "status", "ocr_confidence")
        self.recent_tree = ttk.Treeview(recent_frame, columns=cols, show="headings", height=7)
        headings = {
            "date_time": "Date / Time", "plate_number": "Plate Number",
            "status": "Status", "ocr_confidence": "Confidence",
        }
        widths = {"date_time": 175, "plate_number": 130, "status": 240, "ocr_confidence": 95}
        for col in cols:
            self.recent_tree.heading(col, text=headings[col])
            self.recent_tree.column(col, width=widths[col], anchor="w")
        self.recent_tree.pack(fill="both", expand=True)

    def _metric_card(self, parent, column, title, variable):
        card = ttk.LabelFrame(parent, text=title, padding=14)
        card.grid(row=0, column=column, sticky="nsew", padx=5)
        ttk.Label(card, textvariable=variable, style="Metric.TLabel").pack(anchor="w")

    def _build_scanner(self):
        content = ttk.Frame(self.scanner_tab)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        image_frame = ttk.LabelFrame(content, text="Vehicle Image / Webcam Preview", padding=12)
        image_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        image_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)
        self.image_preview = ttk.Label(
            image_frame, text="Choose an image or start the webcam",
            anchor="center", justify="center",
        )
        self.image_preview.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        ttk.Label(image_frame, textvariable=self.file_var, wraplength=550).grid(
            row=1, column=0, sticky="w", pady=(0, 10)
        )
        buttons = ttk.Frame(image_frame)
        buttons.grid(row=2, column=0, sticky="ew")
        for col in range(2):
            buttons.columnconfigure(col, weight=1)
        self.choose_button = ttk.Button(
            buttons, text="Choose Image", style="Action.TButton", command=self.choose_image
        )
        self.choose_button.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=3)
        self.scan_button = ttk.Button(
            buttons, text="Scan Plate", style="Action.TButton", command=self.start_scan
        )
        self.scan_button.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=3)
        self.start_webcam_button = ttk.Button(
            buttons, text="Start Webcam", style="Action.TButton", command=self.start_webcam
        )
        self.start_webcam_button.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=3)
        self.stop_webcam_button = ttk.Button(
            buttons, text="Stop Webcam", style="Action.TButton",
            command=self.stop_webcam, state="disabled",
        )
        self.stop_webcam_button.grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=3)

        result_frame = ttk.LabelFrame(content, text="Recognition Result", padding=14)
        result_frame.grid(row=0, column=1, sticky="nsew")
        result_frame.columnconfigure(0, weight=1)
        ttk.Label(result_frame, text="Detected Number Plate").grid(row=0, column=0, sticky="w")
        ttk.Label(result_frame, textvariable=self.plate_var, style="Result.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 14)
        )
        ttk.Label(result_frame, text="OCR Confidence").grid(row=2, column=0, sticky="w")
        ttk.Label(result_frame, textvariable=self.confidence_var).grid(
            row=3, column=0, sticky="w", pady=(4, 14)
        )
        ttk.Label(result_frame, text="Local List Status").grid(row=4, column=0, sticky="w")
        ttk.Label(result_frame, textvariable=self.status_var, wraplength=280, justify="left").grid(
            row=5, column=0, sticky="w", pady=(4, 14)
        )
        ttk.Label(result_frame, text="Owner name in CSV (if matched)").grid(
            row=6, column=0, sticky="w"
        )
        ttk.Label(result_frame, textvariable=self.owner_var, wraplength=280).grid(
            row=7, column=0, sticky="w", pady=(4, 14)
        )
        ttk.Separator(result_frame).grid(row=8, column=0, sticky="ew", pady=6)
        ttk.Label(
            result_frame,
            text="AUTHORIZED means only that the plate matched your local CSV list.",
            wraplength=280, justify="left",
        ).grid(row=9, column=0, sticky="w", pady=(8, 0))
        self.progress = ttk.Progressbar(self.scanner_tab, mode="indeterminate")
        self.progress.pack(fill="x", pady=(12, 5))
        ttk.Label(self.scanner_tab, textvariable=self.status_var).pack(anchor="w")

    def _build_history(self):
        top = ttk.Frame(self.history_tab)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Scan History", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="Refresh", command=self.refresh_history).pack(side="right", padx=(6, 0))
        ttk.Button(top, text="Export Copy…", command=self.export_history).pack(side="right")

        search_row = ttk.Frame(self.history_tab)
        search_row.pack(fill="x", pady=(0, 10))
        ttk.Label(search_row, text="Search plate / status:").pack(side="left", padx=(0, 8))
        search_entry = ttk.Entry(search_row, textvariable=self.history_search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        self.history_search_var.trace_add("write", lambda *_: self.refresh_history())

        cols = ("date_time", "plate_number", "status", "ocr_confidence")
        self.history_tree = ttk.Treeview(self.history_tab, columns=cols, show="headings")
        labels = {
            "date_time": "Date / Time", "plate_number": "Plate Number",
            "status": "Status", "ocr_confidence": "Confidence",
        }
        widths = {"date_time": 190, "plate_number": 150, "status": 300, "ocr_confidence": 110}
        for col in cols:
            self.history_tree.heading(col, text=labels[col])
            self.history_tree.column(col, width=widths[col], anchor="w")
        self.history_tree.pack(fill="both", expand=True)
        self.history_count_var = tk.StringVar(value="0 records")
        ttk.Label(self.history_tab, textvariable=self.history_count_var).pack(anchor="w", pady=(8, 0))

    def _read_history_rows(self):
        rows = []
        if not os.path.exists(LOG_FILE):
            return rows
        try:
            with open(LOG_FILE, newline="", encoding="utf-8-sig") as file:
                for row in csv.DictReader(file):
                    rows.append((
                        row.get("date_time", ""), row.get("plate_number", ""),
                        row.get("status", ""), row.get("ocr_confidence", ""),
                    ))
        except (OSError, csv.Error):
            pass
        return rows

    def refresh_history(self):
        if not hasattr(self, "history_tree"):
            return
        query = self.history_search_var.get().strip().upper()
        rows = self._read_history_rows()
        for tree in (self.history_tree, self.recent_tree):
            for item in tree.get_children():
                tree.delete(item)
        filtered = [row for row in rows if query in " ".join(row).upper()]
        for row in reversed(filtered):
            self.history_tree.insert("", "end", values=row)
        for row in reversed(rows[-8:]):
            self.recent_tree.insert("", "end", values=row)
        self.history_count_var.set(f"{len(filtered)} records shown / {len(rows)} total")
        self.refresh_dashboard(rows)

    def refresh_dashboard(self, rows=None):
        if not hasattr(self, "metric_total"):
            return
        rows = self._read_history_rows() if rows is None else rows
        authorized_count = sum("AUTHORIZED" in row[2].upper() for row in rows)
        unknown_count = sum("NOT IN LOCAL LIST" in row[2].upper() for row in rows)
        self.metric_total.set(str(len(rows)))
        self.metric_authorized.set(str(authorized_count))
        self.metric_unknown.set(str(unknown_count))

    def export_history(self):
        if not os.path.exists(LOG_FILE):
            messagebox.showinfo("No History", "There is no scan history to export yet.")
            return
        destination = filedialog.asksaveasfilename(
            title="Export Scan History",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="scan_history_export.csv",
        )
        if not destination:
            return
        try:
            shutil.copy2(LOG_FILE, destination)
            messagebox.showinfo("Export Complete", f"History exported to:\n{destination}")
        except OSError as exc:
            messagebox.showerror("Export Error", str(exc))

    def toggle_theme(self):
        self.theme_name = "Light" if self.theme_name == "Dark" else "Dark"
        self.apply_theme()

    def apply_theme(self):
        if self.theme_name == "Dark":
            bg, panel, fg, muted, field = "#111827", "#1f2937", "#f3f4f6", "#cbd5e1", "#0f172a"
            self.theme_button.configure(text="☀ Light Mode")
        else:
            bg, panel, fg, muted, field = "#f3f4f6", "#ffffff", "#111827", "#4b5563", "#ffffff"
            self.theme_button.configure(text="☾ Dark Mode")
        self.root.configure(bg=bg)
        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabelframe", background=bg, foreground=fg)
        self.style.configure("TLabelframe.Label", background=bg, foreground=fg, font=("Segoe UI", 10, "bold"))
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("Title.TLabel", background=bg, foreground=fg)
        self.style.configure("Subtitle.TLabel", background=bg, foreground=muted)
        self.style.configure("Metric.TLabel", background=panel, foreground="#38bdf8" if self.theme_name == "Dark" else "#0369a1")
        self.style.configure("TButton", background=panel, foreground=fg, padding=6)
        self.style.map("TButton", background=[("active", "#374151" if self.theme_name == "Dark" else "#e5e7eb")])
        self.style.configure("Action.TButton", background="#2563eb", foreground="#ffffff", padding=8)
        self.style.map("Action.TButton", background=[("active", "#1d4ed8")])
        self.style.configure("TNotebook", background=bg, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=panel, foreground=fg, padding=(14, 8))
        self.style.map("TNotebook.Tab", background=[("selected", "#2563eb" if self.theme_name == "Dark" else "#dbeafe")], foreground=[("selected", "#ffffff" if self.theme_name == "Dark" else "#1e3a8a")])
        self.style.configure("Treeview", background=field, fieldbackground=field, foreground=fg, rowheight=27)
        self.style.configure("Treeview.Heading", background=panel, foreground=fg)
        self.style.map("Treeview", background=[("selected", "#1d4ed8")], foreground=[("selected", "#ffffff")])
        self.style.configure("TEntry", fieldbackground=field, foreground=fg)
        self.style.configure("Horizontal.TProgressbar", troughcolor=panel, background="#2563eb")

    def _get_reader(self):
        if self.reader is None:
            self.reader = easyocr.Reader(["en"], gpu=False)
        return self.reader

    def _show_preview(self, cv_image):
        if cv_image is None:
            return
        rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        max_width = max(self.image_preview.winfo_width(), 420)
        max_height = max(self.image_preview.winfo_height(), 320)
        pil_image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(pil_image)
        self.image_preview.configure(image=self.preview_photo, text="")

    def choose_image(self):
        if self.webcam_running:
            messagebox.showinfo("Webcam Running", "Stop the webcam first.")
            return
        path = filedialog.askopenfilename(
            title="Select Vehicle Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp")],
        )
        if not path:
            return
        image = cv2.imread(path)
        if image is None:
            messagebox.showerror("Image Error", "Could not open this image. Select another image.")
            return
        self.image_path = path
        self.original_image = image
        self.file_var.set(os.path.basename(path))
        self.plate_var.set("—")
        self.confidence_var.set("—")
        self.owner_var.set("—")
        self.status_var.set("Image selected. Click Scan Plate.")
        self._show_preview(image)

    def start_scan(self):
        if self.busy:
            return
        if self.webcam_running:
            messagebox.showinfo("Webcam Running", "Stop the webcam first.")
            return
        if not self.image_path or self.original_image is None:
            messagebox.showinfo("Select Image", "Please choose a vehicle image first.")
            return
        self.busy = True
        self._set_image_controls(False)
        self.progress.start(10)
        self.status_var.set("Image OCR is running. Please wait...")
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        try:
            reader = self._get_reader()
            image = self.original_image.copy()
            results = reader.readtext(image, detail=1, paragraph=False, allowlist=OCR_ALLOWLIST)
            authorized = load_authorized_vehicles()
            matches = []
            for box, text, confidence in results:
                plate = clean_plate(text)
                if PLATE_PATTERN.fullmatch(plate) and confidence >= 0.25:
                    matches.append((box, plate, float(confidence)))
            matches.sort(key=lambda item: item[2], reverse=True)
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            output_path = os.path.join(OUTPUT_DIR, "annotated_result.jpg")
            if not matches:
                cv2.imwrite(output_path, image)
                self.root.after(0, lambda: self._finish_no_match(output_path, results))
                return
            box, plate, confidence = matches[0]
            self._draw_plate(image, box, plate)
            owner = authorized.get(plate)
            status = "AUTHORIZED (local CSV match)" if owner is not None else "NOT IN LOCAL LIST"
            append_scan_log(plate, status, confidence)
            cv2.imwrite(output_path, image)
            self.root.after(0, lambda: self._finish_success(image, plate, confidence, status, owner or "—", output_path))
        except Exception as exc:
            error = str(exc)
            self.root.after(0, lambda err=error: self._finish_error(err))

    @staticmethod
    def _draw_plate(image, box, plate):
        import numpy as np
        points = [(int(point[0]), int(point[1])) for point in box]
        cv2.polylines(image, [np.array(points, dtype=np.int32)], True, (0, 255, 0), 2)
        cv2.putText(image, plate, (points[0][0], max(points[0][1] - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    def _finish_success(self, image, plate, confidence, status, owner, output_path):
        self._show_preview(image)
        self.plate_var.set(plate)
        self.confidence_var.set(f"{confidence:.0%} ({confidence:.2f})")
        self.status_var.set(status)
        self.owner_var.set(owner)
        self._finish_busy()
        self.refresh_history()
        messagebox.showinfo("Scan Complete", f"Plate: {plate}\nStatus: {status}\nSaved image: {output_path}")

    def _finish_no_match(self, output_path, results):
        self.plate_var.set("Not detected")
        self.confidence_var.set("—")
        self.status_var.set("No likely plate detected. Try a clearer, closer image.")
        self.owner_var.set("—")
        self._finish_busy()
        raw_text = ", ".join(clean_plate(item[1]) for item in results if item[1].strip())
        message = "Could not recognize a likely vehicle number plate.\n\n"
        if raw_text:
            message += f"Text read by OCR: {raw_text}\n\n"
        message += f"Output image: {output_path}"
        messagebox.showwarning("Plate Not Detected", message)

    def _finish_error(self, error):
        self._finish_busy()
        self.status_var.set("An error occurred during scanning.")
        messagebox.showerror("Scan Error", error)

    def _finish_busy(self):
        self.progress.stop()
        self._set_image_controls(True)
        self.busy = False

    def _set_image_controls(self, enabled):
        state = "normal" if enabled else "disabled"
        self.choose_button.configure(state=state)
        self.scan_button.configure(state=state)
        self.start_webcam_button.configure(state=state)

    def start_webcam(self):
        if self.webcam_running or self.busy:
            return
        camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not camera.isOpened():
            camera.release()
            camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            camera.release()
            messagebox.showerror("Camera Error", "Could not open webcam. Check camera permissions.")
            return
        self.webcam = camera
        self.webcam_running = True
        self.webcam_ocr_busy = False
        self.webcam_frame_count = 0
        self.last_logged_plate = ""
        self.last_logged_time = 0.0
        self.file_var.set("Live webcam")
        self.status_var.set("Webcam is running. Place the plate in front of the camera.")
        self.start_webcam_button.configure(state="disabled")
        self.stop_webcam_button.configure(state="normal")
        self.choose_button.configure(state="disabled")
        self.scan_button.configure(state="disabled")
        self._webcam_loop()

    def stop_webcam(self):
        self.webcam_running = False
        if self.webcam is not None:
            self.webcam.release()
            self.webcam = None
        try:
            cv2.destroyWindow(self.webcam_window_name)
        except cv2.error:
            pass
        self.start_webcam_button.configure(state="normal")
        self.stop_webcam_button.configure(state="disabled")
        self.choose_button.configure(state="normal")
        self.scan_button.configure(state="normal")
        self.file_var.set(os.path.basename(self.image_path) if self.image_path else "No image selected")
        self.status_var.set("Webcam stopped. Choose an image or start again.")

    def _webcam_loop(self):
        if not self.webcam_running or self.webcam is None:
            return
        ok, frame = self.webcam.read()
        if not ok:
            self.stop_webcam()
            messagebox.showerror("Camera Error", "Could not read video from webcam.")
            return
        self.webcam_frame_count += 1
        if self.webcam_frame_count % 12 == 0 and not self.webcam_ocr_busy:
            self.webcam_ocr_busy = True
            threading.Thread(target=self._webcam_ocr_worker, args=(frame.copy(),), daemon=True).start()
        cv2.imshow(self.webcam_window_name, frame)
        key = cv2.waitKey(1) & 0xFF
        try:
            window_visible = cv2.getWindowProperty(self.webcam_window_name, cv2.WND_PROP_VISIBLE) >= 1
        except cv2.error:
            window_visible = False
        if key == ord("q") or not window_visible:
            self.stop_webcam()
            return
        self.root.after(15, self._webcam_loop)

    def _webcam_ocr_worker(self, frame):
        try:
            reader = self._get_reader()
            results = reader.readtext(frame, detail=1, paragraph=False, allowlist=OCR_ALLOWLIST)
            matches = []
            for box, text, confidence in results:
                plate = clean_plate(text)
                if PLATE_PATTERN.fullmatch(plate) and confidence >= 0.25:
                    matches.append((box, plate, float(confidence)))
            if not matches:
                return
            box, plate, confidence = max(matches, key=lambda item: item[2])
            owner = load_authorized_vehicles().get(plate)
            status = "AUTHORIZED (local CSV match)" if owner is not None else "NOT IN LOCAL LIST"
            now = time.time()
            if plate != self.last_logged_plate or now - self.last_logged_time >= 10:
                append_scan_log(plate, status, confidence)
                self.root.after(0, self.refresh_history)
                self.last_logged_plate = plate
                self.last_logged_time = now
            annotated = frame.copy()
            self._draw_plate(annotated, box, plate)
            self.root.after(0, lambda img=annotated, p=plate, c=confidence, s=status, o=owner: self._update_webcam_result(img, p, c, s, o))
        except Exception as exc:
            error = str(exc)
            self.root.after(0, lambda err=error: self._webcam_error(err))
        finally:
            self.root.after(0, self._clear_webcam_ocr_busy)

    def _clear_webcam_ocr_busy(self):
        self.webcam_ocr_busy = False

    def _update_webcam_result(self, image, plate, confidence, status, owner):
        if not self.webcam_running:
            return
        self._show_preview(image)
        self.plate_var.set(plate)
        self.confidence_var.set(f"{confidence:.0%} ({confidence:.2f})")
        self.status_var.set(status)
        self.owner_var.set(owner or "Not in local list")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        cv2.imwrite(os.path.join(OUTPUT_DIR, "webcam_annotated_result.jpg"), image)

    def _webcam_error(self, error):
        if self.webcam_running:
            self.status_var.set("An error occurred during webcam OCR.")
            print("Webcam OCR error:", error)

    def on_close(self):
        if self.webcam_running:
            self.stop_webcam()
        self.root.destroy()


def main():
    root = tk.Tk()
    VehicleRecognitionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
