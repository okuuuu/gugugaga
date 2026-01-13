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

try:
    from PIL import Image, ImageTk
    import pdfplumber
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from kv_pet.file_lookup import MatchResult, scan_folder, lookup_part_number
from kv_pet.pdf_extract import extract_part_rows, PartRow


class PDFPreviewCache:
    """Cache for PDF preview images."""

    def __init__(self, max_size: int = 20):
        self._cache: Dict[str, ImageTk.PhotoImage] = {}
        self._max_size = max_size

    def get(self, pdf_path: str, size: tuple = (200, 280)) -> Optional[ImageTk.PhotoImage]:
        """Get or create a preview image for a PDF."""
        if not PIL_AVAILABLE:
            return None

        cache_key = f"{pdf_path}_{size[0]}x{size[1]}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            with pdfplumber.open(pdf_path) as pdf:
                if pdf.pages:
                    # Render first page
                    page = pdf.pages[0]
                    img = page.to_image(resolution=72)
                    pil_img = img.original

                    # Resize to fit
                    pil_img.thumbnail(size, Image.Resampling.LANCZOS)

                    # Convert to PhotoImage
                    photo = ImageTk.PhotoImage(pil_img)

                    # Cache management
                    if len(self._cache) >= self._max_size:
                        # Remove oldest entry
                        oldest = next(iter(self._cache))
                        del self._cache[oldest]

                    self._cache[cache_key] = photo
                    return photo
        except Exception:
            pass

        return None

    def clear(self):
        """Clear the cache."""
        self._cache.clear()


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
        self.root.geometry("1200x700")
        self.root.minsize(1000, 600)

        self.pdf_paths: List[Path] = []
        self.search_folder: Optional[Path] = None
        self.results: Dict[str, Dict[str, tuple]] = {}  # {pdf_path: {pn: (PartRow, MatchResult)}}

        # Store item data for click handling
        self._item_data: Dict[str, dict] = {}

        # PDF preview cache
        self._preview_cache = PDFPreviewCache()
        self._current_preview_item: Optional[str] = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        # Main container with two panes
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left side: controls and results
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right side: PDF preview
        self.preview_frame = ttk.LabelFrame(main_frame, text="PDF Preview", padding="5")
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.preview_frame.pack_propagate(False)
        self.preview_frame.configure(width=220, height=320)

        self.preview_label = ttk.Label(self.preview_frame, text="Hover over a row\nto see PDF preview", anchor="center")
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        # Top section: PDF selection
        pdf_frame = ttk.LabelFrame(left_frame, text="PDF Files", padding="5")
        pdf_frame.pack(fill=tk.X, pady=(0, 10))

        # Drop zone - clickable
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

        # Folder selection
        folder_frame = ttk.LabelFrame(left_frame, text="Search Folder", padding="5")
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
            left_frame,
            text="Extract Part Numbers & Find Files",
            command=self._run_extraction,
        )
        self.extract_btn.pack(pady=10)

        # Progress bar
        self.progress = ttk.Progressbar(left_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 10))

        # Results section
        results_frame = ttk.LabelFrame(left_frame, text="Results", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview with all columns
        columns = ("Part Number", "Title", "Description", "Mass", "Qty", "Matching PDF", "Print", "Status", "Model")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="tree headings")
        self.tree.heading("#0", text="PDF File")
        self.tree.heading("Part Number", text="Part Number")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Description", text="Description")
        self.tree.heading("Mass", text="Mass")
        self.tree.heading("Qty", text="Qty")
        self.tree.heading("Matching PDF", text="Matching PDF")
        self.tree.heading("Print", text="Print")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Model", text="Model")

        self.tree.column("#0", width=150)
        self.tree.column("Part Number", width=100)
        self.tree.column("Title", width=80)
        self.tree.column("Description", width=80)
        self.tree.column("Mass", width=70)
        self.tree.column("Qty", width=40)
        self.tree.column("Matching PDF", width=200)
        self.tree.column("Print", width=45, anchor="center")
        self.tree.column("Status", width=90)
        self.tree.column("Model", width=50, anchor="center")

        # Scrollbars
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(results_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)

        # Event bindings
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Motion>", self._on_tree_motion)
        self.tree.bind("<Leave>", self._on_tree_leave)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            left_frame, textvariable=self.status_var, relief="sunken", anchor="w"
        )
        status_bar.pack(fill=tk.X, pady=(10, 0))

    def _on_drop(self, event):
        """Handle file drop event."""
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

        self.extract_btn.config(state="disabled")
        self.progress.start()
        self.status_var.set("Extracting...")

        thread = threading.Thread(target=self._extraction_worker, daemon=True)
        thread.start()

    def _extraction_worker(self):
        """Background worker for extraction."""
        try:
            self.results.clear()
            files = scan_folder(self.search_folder)

            for pdf_path in self.pdf_paths:
                self.root.after(
                    0,
                    lambda p=pdf_path: self.status_var.set(f"Processing: {p.name}"),
                )

                try:
                    part_rows = extract_part_rows(pdf_path)
                    matches = {}

                    for part_row in part_rows:
                        match_result = lookup_part_number(part_row.part_number, files)
                        matches[part_row.part_number] = (part_row, match_result)

                    self.results[str(pdf_path)] = matches
                except Exception as e:
                    self.results[str(pdf_path)] = {"ERROR": (None, MatchResult(status="Error"))}

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
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._item_data.clear()

        for pdf_path, matches in self.results.items():
            pdf_name = Path(pdf_path).name
            pdf_node = self.tree.insert("", "end", text=pdf_name, open=True)

            if not matches:
                self.tree.insert(
                    pdf_node, "end",
                    values=("", "", "", "", "", "", "", "No tables found", ""),
                )
                continue

            for part_number, data in matches.items():
                if part_number == "ERROR":
                    self.tree.insert(
                        pdf_node, "end",
                        values=("", "", "", "", "", "", "", "Error processing PDF", ""),
                    )
                    continue

                part_row, match_result = data

                # Part row fields
                title = part_row.title if part_row else ""
                description = part_row.description if part_row else ""
                mass = part_row.mass if part_row else ""
                qty = part_row.qty if part_row else ""

                # Match result fields
                pdf_files = match_result.pdf_files
                model_files = match_result.model_files
                status = match_result.status
                no_pdf_required = match_result.no_pdf_required

                # Display strings
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

                model_display = "[3D]" if model_files else ""

                item_id = self.tree.insert(
                    pdf_node, "end",
                    values=(part_number, title, description, mass, qty,
                            pdf_display, print_display, status, model_display),
                )

                self._item_data[item_id] = {
                    "pdf_files": pdf_files,
                    "model_files": model_files,
                    "part_number": part_number,
                }

    def _on_tree_click(self, event):
        """Handle single click on tree item for Print/Model actions."""
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)

        if not item or item not in self._item_data:
            return

        data = self._item_data[item]

        # Column indices: #0=tree, #1=PN, #2=Title, #3=Desc, #4=Mass, #5=Qty, #6=PDF, #7=Print, #8=Status, #9=Model
        if column == "#7":  # Print column
            if data["pdf_files"]:
                self._print_file(data["pdf_files"][0])
        elif column == "#9":  # Model column
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

    def _on_tree_motion(self, event):
        """Handle mouse motion over tree for PDF preview."""
        item = self.tree.identify_row(event.y)

        if item == self._current_preview_item:
            return

        self._current_preview_item = item

        if not item or item not in self._item_data:
            self._clear_preview()
            return

        data = self._item_data[item]
        if data["pdf_files"]:
            self._show_preview(data["pdf_files"][0])
        else:
            self._clear_preview()

    def _on_tree_leave(self, event):
        """Handle mouse leaving tree widget."""
        self._current_preview_item = None
        self._clear_preview()

    def _show_preview(self, pdf_path: Path):
        """Show PDF preview in the preview pane."""
        if not PIL_AVAILABLE:
            self.preview_label.config(image="", text="Preview not available\n(Pillow required)")
            return

        # Get from cache or generate
        photo = self._preview_cache.get(str(pdf_path))
        if photo:
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo  # Keep reference
        else:
            self.preview_label.config(image="", text="Loading preview...")
            # Generate in background
            self.root.after(10, lambda: self._load_preview_async(pdf_path))

    def _load_preview_async(self, pdf_path: Path):
        """Load preview asynchronously."""
        photo = self._preview_cache.get(str(pdf_path))
        if photo and self._current_preview_item:
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo

    def _clear_preview(self):
        """Clear the preview pane."""
        self.preview_label.config(image="", text="Hover over a row\nto see PDF preview")
        self.preview_label.image = None

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
