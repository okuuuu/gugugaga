"""Application entry point - Desktop UI with tkinter."""

import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None
    DND_FILES = None

import tkinter as tk

from kv_pet.file_lookup import MatchResult, lookup_part_numbers
from kv_pet.pdf_extract import extract_part_numbers


class PDFPartNumberExtractor:
    """Main application window for PDF Part Number Extractor."""

    def __init__(self):
        # Use TkinterDnD if available, otherwise fall back to regular Tk
        if TkinterDnD is not None:
            self.root = TkinterDnD.Tk()
            self.dnd_available = True
        else:
            self.root = tk.Tk()
            self.dnd_available = False

        self.root.title("PDF Part Number Extractor")
        self.root.geometry("1000x600")
        self.root.minsize(800, 500)

        self.pdf_paths: List[Path] = []
        self.search_folder: Optional[Path] = None
        self.results: Dict[str, Dict[str, MatchResult]] = {}

        # Store item data for click handling
        self._item_data: Dict[str, dict] = {}

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top section: PDF selection
        pdf_frame = ttk.LabelFrame(main_frame, text="PDF Files", padding="5")
        pdf_frame.pack(fill=tk.X, pady=(0, 10))

        # Drop zone - now clickable
        self.drop_zone = ttk.Label(
            pdf_frame,
            text="Drag & drop PDF files here, or click to browse"
            if self.dnd_available
            else "Click here to select PDF files",
            anchor="center",
            relief="sunken",
            padding=20,
            cursor="hand2",
        )
        self.drop_zone.pack(fill=tk.X, pady=5)

        # Bind click to browse
        self.drop_zone.bind("<Button-1>", lambda e: self._browse_pdfs())

        if self.dnd_available:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)

        # PDF buttons
        pdf_btn_frame = ttk.Frame(pdf_frame)
        pdf_btn_frame.pack(fill=tk.X)

        ttk.Button(pdf_btn_frame, text="Browse PDFs", command=self._browse_pdfs).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(pdf_btn_frame, text="Clear PDFs", command=self._clear_pdfs).pack(
            side=tk.LEFT, padx=5
        )

        self.pdf_count_label = ttk.Label(pdf_btn_frame, text="No PDFs selected")
        self.pdf_count_label.pack(side=tk.LEFT, padx=20)

        # Middle section: Folder selection
        folder_frame = ttk.LabelFrame(main_frame, text="Search Folder", padding="5")
        folder_frame.pack(fill=tk.X, pady=(0, 10))

        folder_btn_frame = ttk.Frame(folder_frame)
        folder_btn_frame.pack(fill=tk.X)

        ttk.Button(
            folder_btn_frame, text="Select Folder", command=self._browse_folder
        ).pack(side=tk.LEFT, padx=5)

        self.folder_label = ttk.Label(folder_btn_frame, text="No folder selected")
        self.folder_label.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)

        # Extract button
        self.extract_btn = ttk.Button(
            main_frame,
            text="Extract Part Numbers & Find Files",
            command=self._run_extraction,
        )
        self.extract_btn.pack(pady=10)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 10))

        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview for results - added Model column
        columns = ("Part Number", "Matching PDF", "Print", "Status", "Model")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="tree headings")
        self.tree.heading("#0", text="PDF File")
        self.tree.heading("Part Number", text="Part Number")
        self.tree.heading("Matching PDF", text="Matching PDF")
        self.tree.heading("Print", text="Print")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Model", text="Model")

        self.tree.column("#0", width=180)
        self.tree.column("Part Number", width=120)
        self.tree.column("Matching PDF", width=350)
        self.tree.column("Print", width=50, anchor="center")
        self.tree.column("Status", width=100)
        self.tree.column("Model", width=60, anchor="center")

        # Scrollbars
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(
            results_frame, orient="horizontal", command=self.tree.xview
        )
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)

        # Single click handler for actions
        self.tree.bind("<Button-1>", self._on_tree_click)
        # Double-click to open file
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame, textvariable=self.status_var, relief="sunken", anchor="w"
        )
        status_bar.pack(fill=tk.X, pady=(10, 0))

    def _on_drop(self, event):
        """Handle file drop event."""
        # Parse dropped files (tkinterdnd2 format)
        files = self.root.tk.splitlist(event.data)
        pdf_files = [Path(f) for f in files if f.lower().endswith(".pdf")]

        if pdf_files:
            self.pdf_paths.extend(pdf_files)
            self._update_pdf_count()
            self.status_var.set(f"Added {len(pdf_files)} PDF file(s)")
        else:
            self.status_var.set("No PDF files in dropped items")

    def _browse_pdfs(self):
        """Open file dialog to select PDFs."""
        files = filedialog.askopenfilenames(
            title="Select PDF Files",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
        )
        if files:
            self.pdf_paths.extend(Path(f) for f in files)
            self._update_pdf_count()

    def _clear_pdfs(self):
        """Clear all selected PDFs."""
        self.pdf_paths.clear()
        self._update_pdf_count()
        self.status_var.set("PDF list cleared")

    def _update_pdf_count(self):
        """Update the PDF count label."""
        count = len(self.pdf_paths)
        self.pdf_count_label.config(
            text=f"{count} PDF(s) selected" if count else "No PDFs selected"
        )

    def _browse_folder(self):
        """Open folder dialog to select search folder."""
        folder = filedialog.askdirectory(title="Select Folder to Search")
        if folder:
            self.search_folder = Path(folder)
            display_path = str(self.search_folder)
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            self.folder_label.config(text=display_path)
            self.status_var.set(f"Search folder: {self.search_folder.name}")

    def _run_extraction(self):
        """Run the extraction in a background thread."""
        if not self.pdf_paths:
            messagebox.showwarning("No PDFs", "Please select at least one PDF file.")
            return

        if not self.search_folder:
            messagebox.showwarning(
                "No Folder", "Please select a folder to search for matching files."
            )
            return

        # Disable button and start progress
        self.extract_btn.config(state="disabled")
        self.progress.start()
        self.status_var.set("Extracting...")

        # Run in background thread
        thread = threading.Thread(target=self._extraction_worker, daemon=True)
        thread.start()

    def _extraction_worker(self):
        """Background worker for extraction."""
        try:
            self.results.clear()

            for pdf_path in self.pdf_paths:
                self.root.after(
                    0,
                    lambda p=pdf_path: self.status_var.set(f"Processing: {p.name}"),
                )

                try:
                    part_numbers = extract_part_numbers(pdf_path)

                    if part_numbers and self.search_folder:
                        matches = lookup_part_numbers(part_numbers, self.search_folder)
                    else:
                        matches = {pn: MatchResult(status="No folder") for pn in part_numbers}

                    self.results[str(pdf_path)] = matches
                except Exception as e:
                    self.results[str(pdf_path)] = {"ERROR": MatchResult(status="Error")}

            # Update UI on main thread
            self.root.after(0, self._display_results)

        except Exception as e:
            self.root.after(
                0, lambda: messagebox.showerror("Error", f"Extraction failed: {e}")
            )
        finally:
            self.root.after(0, self._extraction_complete)

    def _extraction_complete(self):
        """Called when extraction is complete."""
        self.progress.stop()
        self.extract_btn.config(state="normal")
        self.status_var.set("Extraction complete")

    def _display_results(self):
        """Display extraction results in the treeview."""
        # Clear existing items and data
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._item_data.clear()

        for pdf_path, matches in self.results.items():
            pdf_name = Path(pdf_path).name
            pdf_node = self.tree.insert("", "end", text=pdf_name, open=True)

            if not matches:
                self.tree.insert(
                    pdf_node,
                    "end",
                    values=("", "", "", "No tables found", ""),
                )
                continue

            for part_number, match_result in matches.items():
                if part_number == "ERROR":
                    self.tree.insert(
                        pdf_node,
                        "end",
                        values=("", "", "", "Error processing PDF", ""),
                    )
                    continue

                # Handle MatchResult object
                if isinstance(match_result, MatchResult):
                    pdf_files = match_result.pdf_files
                    model_files = match_result.model_files
                    status = match_result.status
                    no_pdf_required = match_result.no_pdf_required
                else:
                    # Fallback for legacy format
                    pdf_files = match_result if isinstance(match_result, list) else []
                    model_files = []
                    status = f"{len(pdf_files)} match(es)" if pdf_files else "No matches"
                    no_pdf_required = False

                # Build display strings
                if no_pdf_required:
                    pdf_display = ""
                    print_display = ""
                elif pdf_files:
                    pdf_display = pdf_files[0].name
                    if len(pdf_files) > 1:
                        pdf_display += f" (+{len(pdf_files) - 1})"
                    print_display = "[Print]"
                else:
                    pdf_display = ""
                    print_display = ""

                # Model indicator
                if model_files:
                    model_display = "[3D]"
                else:
                    model_display = ""

                item_id = self.tree.insert(
                    pdf_node,
                    "end",
                    values=(part_number, pdf_display, print_display, status, model_display),
                )

                # Store data for click handling
                self._item_data[item_id] = {
                    "pdf_files": pdf_files,
                    "model_files": model_files,
                    "part_number": part_number,
                }

    def _on_tree_click(self, event):
        """Handle single click on tree item for Print/Model actions."""
        # Identify clicked region
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)

        if not item or item not in self._item_data:
            return

        data = self._item_data[item]

        # Column #3 is "Print" (columns are #0, #1, #2, #3, #4, #5)
        # #0 is tree column, then Part Number=#1, Matching PDF=#2, Print=#3, Status=#4, Model=#5
        if column == "#3":  # Print column
            if data["pdf_files"]:
                self._print_file(data["pdf_files"][0])
        elif column == "#5":  # Model column
            if data["model_files"]:
                self._open_file(data["model_files"][0])

    def _on_tree_double_click(self, event):
        """Handle double-click on tree item to open PDF file."""
        item = self.tree.identify_row(event.y)
        if not item or item not in self._item_data:
            return

        data = self._item_data[item]
        if data["pdf_files"]:
            self._open_file(data["pdf_files"][0])

    def _open_file(self, path: Path):
        """Open file in system default application."""
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)])
            else:
                subprocess.run(["xdg-open", str(path)])
            self.status_var.set(f"Opened: {path.name}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")

    def _print_file(self, path: Path):
        """Print a PDF file using system print."""
        try:
            if sys.platform == "win32":
                # Use ShellExecute with "print" verb
                os.startfile(path, "print")
            elif sys.platform == "darwin":
                subprocess.run(["lpr", str(path)])
            else:
                subprocess.run(["lpr", str(path)])
            self.status_var.set(f"Sent to printer: {path.name}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not print file: {e}")

    def run(self):
        """Start the application main loop."""
        self.root.mainloop()


def main():
    """Application entry point."""
    app = PDFPartNumberExtractor()
    app.run()


if __name__ == "__main__":
    main()
