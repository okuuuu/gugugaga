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

    def __init__(self, max_size: int = 50):
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
                    page = pdf.pages[0]
                    # Use higher resolution for larger previews
                    resolution = max(72, min(150, size[0] // 2))
                    img = page.to_image(resolution=resolution)
                    pil_img = img.original

                    # Resize to fit
                    pil_img.thumbnail(size, Image.Resampling.LANCZOS)

                    photo = ImageTk.PhotoImage(pil_img)

                    # Cache management
                    if len(self._cache) >= self._max_size:
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
        if TkinterDnD is not None:
            self.root = TkinterDnD.Tk()
            self.dnd_available = True
        else:
            self.root = tk.Tk()
            self.dnd_available = False

        self.root.title("PDF Part Number Extractor")
        self.root.geometry("1300x750")
        self.root.minsize(1100, 650)

        self.pdf_paths: List[Path] = []
        self.search_folder: Optional[Path] = None
        self.results: Dict[str, Dict[str, tuple]] = {}

        # Store item data for click handling
        self._item_data: Dict[str, dict] = {}

        # PDF preview cache and state
        self._preview_cache = PDFPreviewCache()
        self._current_preview_item: Optional[str] = None
        self._selected_uploaded_pdf: Optional[Path] = None
        self._preview_size = tk.IntVar(value=250)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left side: controls and results
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right side: PDF preview panel
        self._setup_preview_panel(main_frame)

        # PDF Files section with listbox
        self._setup_pdf_section(left_frame)

        # Folder selection
        self._setup_folder_section(left_frame)

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
        self._setup_results_section(left_frame)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            left_frame, textvariable=self.status_var, relief="sunken", anchor="w"
        )
        status_bar.pack(fill=tk.X, pady=(10, 0))

    def _setup_preview_panel(self, parent):
        """Set up the right-side preview panel."""
        self.preview_frame = ttk.LabelFrame(parent, text="PDF Preview", padding="5")
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.preview_frame.pack_propagate(False)
        self.preview_frame.configure(width=280, height=450)

        # Size control
        size_frame = ttk.Frame(self.preview_frame)
        size_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(size_frame, text="Size:").pack(side=tk.LEFT)
        self.size_slider = ttk.Scale(
            size_frame,
            from_=150,
            to=400,
            orient=tk.HORIZONTAL,
            variable=self._preview_size,
            command=self._on_preview_size_change,
        )
        self.size_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.size_label = ttk.Label(size_frame, text="250px")
        self.size_label.pack(side=tk.LEFT)

        # Preview image area
        self.preview_label = ttk.Label(
            self.preview_frame,
            text="Select a PDF to preview\nor hover over results",
            anchor="center",
        )
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        # Preview source indicator
        self.preview_source_label = ttk.Label(
            self.preview_frame, text="", anchor="center", font=("", 8)
        )
        self.preview_source_label.pack(fill=tk.X)

    def _setup_pdf_section(self, parent):
        """Set up the PDF files section with listbox."""
        pdf_frame = ttk.LabelFrame(parent, text="PDF Files", padding="5")
        pdf_frame.pack(fill=tk.X, pady=(0, 10))

        # Drop zone
        self.drop_zone = ttk.Label(
            pdf_frame,
            text="Drag & drop PDF files here, or click to browse"
            if self.dnd_available
            else "Click here to select PDF files",
            anchor="center",
            relief="sunken",
            padding=10,
            cursor="hand2",
        )
        self.drop_zone.pack(fill=tk.X, pady=(0, 5))
        self.drop_zone.bind("<Button-1>", lambda e: self._browse_pdfs())

        if self.dnd_available:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)

        # Listbox for uploaded PDFs
        list_frame = ttk.Frame(pdf_frame)
        list_frame.pack(fill=tk.X)

        self.pdf_listbox = tk.Listbox(list_frame, height=4, selectmode=tk.SINGLE)
        self.pdf_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.pdf_listbox.bind("<<ListboxSelect>>", self._on_pdf_listbox_select)

        list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.pdf_listbox.yview)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pdf_listbox.config(yscrollcommand=list_scrollbar.set)

        # Buttons row
        btn_frame = ttk.Frame(pdf_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(btn_frame, text="Browse", command=self._browse_pdfs).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove", command=self._remove_selected_pdf).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear All", command=self._clear_pdfs).pack(side=tk.LEFT, padx=2)

        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        self.preview_btn = ttk.Button(btn_frame, text="Preview", command=self._preview_selected_pdf, state="disabled")
        self.preview_btn.pack(side=tk.LEFT, padx=2)

        self.print_btn = ttk.Button(btn_frame, text="Print", command=self._print_selected_pdf, state="disabled")
        self.print_btn.pack(side=tk.LEFT, padx=2)

        self.open_btn = ttk.Button(btn_frame, text="Open", command=self._open_selected_pdf, state="disabled")
        self.open_btn.pack(side=tk.LEFT, padx=2)

        self.pdf_count_label = ttk.Label(btn_frame, text="0 PDF(s)")
        self.pdf_count_label.pack(side=tk.RIGHT, padx=5)

    def _setup_folder_section(self, parent):
        """Set up the folder selection section."""
        folder_frame = ttk.LabelFrame(parent, text="Search Folder", padding="5")
        folder_frame.pack(fill=tk.X, pady=(0, 10))

        folder_btn_frame = ttk.Frame(folder_frame)
        folder_btn_frame.pack(fill=tk.X)

        ttk.Button(
            folder_btn_frame, text="Select Folder", command=self._browse_folder
        ).pack(side=tk.LEFT, padx=5)

        self.folder_label = ttk.Label(folder_btn_frame, text="No folder selected")
        self.folder_label.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)

    def _setup_results_section(self, parent):
        """Set up the results treeview section."""
        results_frame = ttk.LabelFrame(parent, text="Results", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True)

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
        self.tree.column("Matching PDF", width=180)
        self.tree.column("Print", width=45, anchor="center")
        self.tree.column("Status", width=90)
        self.tree.column("Model", width=50, anchor="center")

        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(results_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Motion>", self._on_tree_motion)
        self.tree.bind("<Leave>", self._on_tree_leave)

    def _on_preview_size_change(self, value):
        """Handle preview size slider change."""
        size = int(float(value))
        self.size_label.config(text=f"{size}px")

        # Refresh preview if one is showing
        if self._selected_uploaded_pdf:
            self._show_uploaded_pdf_preview(self._selected_uploaded_pdf)

    def _on_drop(self, event):
        """Handle file drop event."""
        files = self.root.tk.splitlist(event.data)
        pdf_files = [Path(f) for f in files if f.lower().endswith(".pdf")]

        if pdf_files:
            for pdf in pdf_files:
                if pdf not in self.pdf_paths:
                    self.pdf_paths.append(pdf)
            self._update_pdf_listbox()
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
            for f in files:
                pdf = Path(f)
                if pdf not in self.pdf_paths:
                    self.pdf_paths.append(pdf)
            self._update_pdf_listbox()

    def _remove_selected_pdf(self):
        """Remove the selected PDF from the list."""
        selection = self.pdf_listbox.curselection()
        if selection:
            idx = selection[0]
            if 0 <= idx < len(self.pdf_paths):
                removed = self.pdf_paths.pop(idx)
                self._update_pdf_listbox()
                self._clear_uploaded_preview()
                self.status_var.set(f"Removed: {removed.name}")

    def _clear_pdfs(self):
        """Clear all selected PDFs."""
        self.pdf_paths.clear()
        self._update_pdf_listbox()
        self._clear_uploaded_preview()
        self.status_var.set("PDF list cleared")

    def _update_pdf_listbox(self):
        """Update the PDF listbox with current files."""
        self.pdf_listbox.delete(0, tk.END)
        for pdf in self.pdf_paths:
            self.pdf_listbox.insert(tk.END, pdf.name)

        count = len(self.pdf_paths)
        self.pdf_count_label.config(text=f"{count} PDF(s)")

        # Update button states
        has_selection = bool(self.pdf_listbox.curselection())
        state = "normal" if has_selection else "disabled"
        self.preview_btn.config(state=state)
        self.print_btn.config(state=state)
        self.open_btn.config(state=state)

    def _on_pdf_listbox_select(self, event):
        """Handle PDF listbox selection change."""
        selection = self.pdf_listbox.curselection()
        if selection:
            idx = selection[0]
            if 0 <= idx < len(self.pdf_paths):
                self._selected_uploaded_pdf = self.pdf_paths[idx]
                self._show_uploaded_pdf_preview(self._selected_uploaded_pdf)

                # Enable action buttons
                self.preview_btn.config(state="normal")
                self.print_btn.config(state="normal")
                self.open_btn.config(state="normal")
        else:
            self._selected_uploaded_pdf = None
            self._clear_uploaded_preview()
            self.preview_btn.config(state="disabled")
            self.print_btn.config(state="disabled")
            self.open_btn.config(state="disabled")

    def _show_uploaded_pdf_preview(self, pdf_path: Path):
        """Show preview for an uploaded PDF."""
        if not PIL_AVAILABLE:
            self.preview_label.config(image="", text="Preview not available\n(Pillow required)")
            self.preview_source_label.config(text="")
            return

        size = self._preview_size.get()
        photo = self._preview_cache.get(str(pdf_path), size=(size, int(size * 1.4)))

        if photo:
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo
            self.preview_source_label.config(text=f"Source: {pdf_path.name}")
        else:
            self.preview_label.config(image="", text="Loading preview...")
            self.preview_source_label.config(text="")
            # Try loading
            self.root.after(50, lambda: self._refresh_uploaded_preview(pdf_path))

    def _refresh_uploaded_preview(self, pdf_path: Path):
        """Refresh the uploaded PDF preview after cache miss."""
        if self._selected_uploaded_pdf != pdf_path:
            return

        size = self._preview_size.get()
        photo = self._preview_cache.get(str(pdf_path), size=(size, int(size * 1.4)))

        if photo:
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo
            self.preview_source_label.config(text=f"Source: {pdf_path.name}")
        else:
            self.preview_label.config(image="", text="Failed to load preview")
            self.preview_source_label.config(text="")

    def _clear_uploaded_preview(self):
        """Clear the uploaded PDF preview."""
        self._selected_uploaded_pdf = None
        self.preview_label.config(image="", text="Select a PDF to preview\nor hover over results")
        self.preview_label.image = None
        self.preview_source_label.config(text="")

    def _preview_selected_pdf(self):
        """Show preview for the selected uploaded PDF."""
        if self._selected_uploaded_pdf:
            self._show_uploaded_pdf_preview(self._selected_uploaded_pdf)

    def _print_selected_pdf(self):
        """Print the selected uploaded PDF."""
        if self._selected_uploaded_pdf:
            self._print_file(self._selected_uploaded_pdf)

    def _open_selected_pdf(self):
        """Open the selected uploaded PDF."""
        if self._selected_uploaded_pdf:
            self._open_file(self._selected_uploaded_pdf)

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

                title = part_row.title if part_row else ""
                description = part_row.description if part_row else ""
                mass = part_row.mass if part_row else ""
                qty = part_row.qty if part_row else ""

                pdf_files = match_result.pdf_files
                model_files = match_result.model_files
                status = match_result.status
                no_pdf_required = match_result.no_pdf_required

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
            # Don't clear if we have an uploaded PDF selected
            if not self._selected_uploaded_pdf:
                self._clear_matched_preview()
            return

        data = self._item_data[item]
        if data["pdf_files"]:
            self._show_matched_preview(data["pdf_files"][0])
        elif not self._selected_uploaded_pdf:
            self._clear_matched_preview()

    def _on_tree_leave(self, event):
        """Handle mouse leaving tree widget."""
        self._current_preview_item = None
        # Restore uploaded PDF preview if one was selected
        if self._selected_uploaded_pdf:
            self._show_uploaded_pdf_preview(self._selected_uploaded_pdf)
        else:
            self._clear_matched_preview()

    def _show_matched_preview(self, pdf_path: Path):
        """Show preview for a matched PDF from results."""
        if not PIL_AVAILABLE:
            self.preview_label.config(image="", text="Preview not available\n(Pillow required)")
            self.preview_source_label.config(text="")
            return

        size = self._preview_size.get()
        photo = self._preview_cache.get(str(pdf_path), size=(size, int(size * 1.4)))

        if photo:
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo
            self.preview_source_label.config(text=f"Match: {pdf_path.name}")
        else:
            self.preview_label.config(image="", text="Loading...")
            self.preview_source_label.config(text="")
            self.root.after(10, lambda: self._refresh_matched_preview(pdf_path))

    def _refresh_matched_preview(self, pdf_path: Path):
        """Refresh matched PDF preview."""
        size = self._preview_size.get()
        photo = self._preview_cache.get(str(pdf_path), size=(size, int(size * 1.4)))

        if photo and self._current_preview_item:
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo
            self.preview_source_label.config(text=f"Match: {pdf_path.name}")

    def _clear_matched_preview(self):
        """Clear matched PDF preview."""
        self.preview_label.config(image="", text="Select a PDF to preview\nor hover over results")
        self.preview_label.image = None
        self.preview_source_label.config(text="")

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
