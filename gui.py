# gui.py 
# Created by SuperGrok and Sir_Cornealious on X

import json
import os
import shutil
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import requests
from datetime import datetime
import logging
import time
from utils import API_URL, TIMEOUT, API_KEY_FILE

class CaseCrackerGUI:
    def __init__(self):
        self.api_key = None
        self.input_paths = []
        self.save_dir = None
        self.query = "Analyze this text for insights related to the investigation of this crime. Identify crimes committed or evidence of conspiracy"
        self.processing_mode = "ocr_and_analysis"  # Default mode
        self.temp_dir = None
        self.logger = logging.getLogger(__name__)
        self.root = None
        self.pdf_paths_file = None

    def setup_temp_dir(self):
        self.temp_dir = tempfile.mkdtemp()
        self.pdf_paths_file = os.path.join(self.temp_dir, "pdf_paths.json")
        self.logger.debug(f"Temporary directory created: {self.temp_dir}")

    def cleanup_temp_dir(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.logger.debug(f"Temporary directory cleaned up: {self.temp_dir}")

    def save_input_paths(self):
        if self.pdf_paths_file:
            if self.input_paths:
                with open(self.pdf_paths_file, "w") as f:
                    json.dump(self.input_paths, f)
                self.logger.debug(f"Saved input_paths to {self.pdf_paths_file}")
            else:
                self.logger.debug("No input_paths to save")
        else:
            self.logger.debug("pdf_paths_file is None, cannot save")

    def restore_input_paths(self):
        if self.pdf_paths_file and os.path.exists(self.pdf_paths_file):
            with open(self.pdf_paths_file, "r") as f:
                self.input_paths = json.load(f)
            self.logger.debug(f"Restored input_paths: {self.input_paths}")
        else:
            self.logger.debug("No pdf_paths file to restore or pdf_paths_file is None")

    def run_gui(self):
        self.root = tk.Tk()
        self.root.title("Case Cracker")
        self.root.geometry("600x400")

        # Set up temporary directory and pdf_paths_file
        self.setup_temp_dir()

        try:
            notebook = ttk.Notebook(self.root)
            notebook.pack(pady=10, expand=True)

            # API Key Tab (Index 0)
            api_frame = ttk.Frame(notebook)
            notebook.add(api_frame, text="API Key")
            ttk.Label(api_frame, text="Enter xAI API key:").pack(pady=10)
            api_entry = ttk.Entry(api_frame, width=50, show="*")
            api_entry.pack(pady=10)

            def load_saved_key():
                self.logger.debug("Loading saved API key")
                if os.path.exists(API_KEY_FILE):
                    with open(API_KEY_FILE, "r") as f:
                        saved_key = f.read().strip()
                    if saved_key and messagebox.askyesno("Saved API Key", f"Found saved API key: {saved_key[:4]}...{saved_key[-4:]}\nUse this key?", parent=self.root):
                        self.api_key = saved_key
                        self.logger.debug("Using saved API key")
                        notebook.select(1)

            def save_api_key():
                self.logger.debug("Saving API key")
                key = api_entry.get().strip()
                if not key:
                    messagebox.showerror("Error", "API key cannot be empty.", parent=self.root)
                    return
                try:
                    headers = {"Authorization": f"Bearer {key}"}
                    response = requests.post(API_URL, headers=headers, json={
                        "model": "grok-3-fast-latest",
                        "messages": [{"role": "user", "content": "Test"}],
                        "temperature": 0.01
                    }, timeout=TIMEOUT)
                    response.raise_for_status()
                    with open(API_KEY_FILE, "w") as f:
                        f.write(key)
                    self.api_key = key
                    self.logger.debug("API key validated and saved")
                    notebook.select(1)
                except requests.RequestException as e:
                    messagebox.showerror("Error", f"Invalid API key: {str(e)}", parent=self.root)
                    self.logger.error(f"API key validation failed: {str(e)}")

            ttk.Button(api_frame, text="Load Saved Key", command=load_saved_key).pack(pady=5)
            ttk.Button(api_frame, text="Submit", command=save_api_key).pack(pady=5)

            # Processing Mode Tab (Index 1)
            mode_frame = ttk.Frame(notebook)
            notebook.add(mode_frame, text="Processing Mode")
            ttk.Label(mode_frame, text="Choose processing mode:").pack(pady=10)
            mode_var = tk.StringVar(value="ocr_and_analysis")
            ttk.Radiobutton(mode_frame, text="OCR Only (Extract Text)", variable=mode_var, value="ocr_only").pack(anchor=tk.W, padx=20)
            ttk.Radiobutton(mode_frame, text="OCR + Analysis", variable=mode_var, value="ocr_and_analysis").pack(anchor=tk.W, padx=20)
            ttk.Radiobutton(mode_frame, text="Analyze Only (Text File)", variable=mode_var, value="analyze_only").pack(anchor=tk.W, padx=20)

            def confirm_mode():
                self.logger.debug("Confirming processing mode")
                new_mode = mode_var.get()
                if new_mode != self.processing_mode:
                    self.processing_mode = new_mode
                    self.input_paths = []
                    input_display.config(text="Selected: None")
                    if self.processing_mode == "analyze_only":
                        messagebox.showinfo("Mode Changed", "Please select a .txt file for analysis.", parent=self.root)
                        input_label.config(text="Select text file for analysis:")
                    else:
                        messagebox.showinfo("Mode Changed", "Please select PDF, JPEG, JPG, or PNG files for OCR.", parent=self.root)
                        input_label.config(text="Select PDF, JPEG, JPG, or PNG files for OCR:")
                    self.logger.debug(f"Processing mode selected: {self.processing_mode}")
                    notebook.select(2)  # Go to Input Files tab (now index 2)
                else:
                    self.processing_mode = new_mode
                    self.logger.debug(f"Processing mode selected: {self.processing_mode}")
                    notebook.select(2)

            ttk.Button(mode_frame, text="Confirm", command=confirm_mode).pack(pady=20)

            # Input Files Tab (Index 2)
            input_frame = ttk.Frame(notebook)
            notebook.add(input_frame, text="Input Files")
            input_label = ttk.Label(input_frame, text="Select input files (PDFs or images for OCR, text for analysis):")
            input_label.pack(pady=10)
            input_display = ttk.Label(input_frame, text="Selected: None")
            input_display.pack(pady=5)

            def select_input_files():
                self.logger.debug(f"Opening file picker, current input_paths: {self.input_paths}")
                try:
                    if self.processing_mode == "analyze_only":
                        filetypes = [("Text files", "*.txt")]
                        title = "Select Text File for Analysis"
                        input_label.config(text="Select text file for analysis:")
                    else:
                        filetypes = [
                            ("PDF and Image files", "*.pdf *.jpeg *.jpg *.png"),
                            ("PDF files", "*.pdf"),
                            ("Image files", "*.jpeg *.jpg *.png")
                        ]
                        title = "Select PDF, JPEG, JPG, or PNG Files to Process"
                        input_label.config(text="Select PDF, JPEG, JPG, or PNG files for OCR:")
                    input_paths = filedialog.askopenfilenames(
                        title=title,
                        filetypes=filetypes,
                        parent=self.root
                    )
                    self.logger.debug(f"File picker returned: {input_paths}")
                    if not input_paths:
                        messagebox.showerror("Error", f"Please select at least one {filetypes[0][0].lower()}.", parent=self.root)
                        return
                    self.input_paths = list(input_paths)
                    display_text = "Selected: " + ", ".join(os.path.basename(p) for p in self.input_paths)
                    input_display.config(text=display_text)
                    messagebox.showinfo("Files Selected", f"Selected Files:\n{display_text}", parent=self.root)
                    self.logger.debug(f"Updated input_paths: {self.input_paths}")
                    notebook.select(3)
                except (OSError, IOError) as e:
                    messagebox.showerror("Error", f"File picker error: {str(e)}", parent=self.root)
                    self.logger.error(f"File picker error: {str(e)}")

            ttk.Button(input_frame, text="Select Files", command=select_input_files).pack(pady=10)

            # Save Location Tab (Index 3)
            save_frame = ttk.Frame(notebook)
            notebook.add(save_frame, text="Save Location")
            ttk.Label(save_frame, text="Select save directory:").pack(pady=10)
            save_display = ttk.Label(save_frame, text="Selected: None")
            save_display.pack(pady=5)

            def select_save_dir():
                self.logger.debug(f"Opening save directory picker, current save_dir: {self.save_dir}")
                if not self.input_paths:
                    messagebox.showerror("Error", "Please select input files first.", parent=self.root)
                    return
                # Validate file extensions match the mode
                if self.processing_mode == "analyze_only":
                    if not all(p.endswith('.txt') for p in self.input_paths):
                        messagebox.showerror("Error", "Please select only .txt files for 'Analyze Only' mode.", parent=self.root)
                        self.input_paths = []
                        input_display.config(text="Selected: None")
                        notebook.select(2)
                        return
                else:
                    if not all(p.lower().endswith(('.pdf', '.jpeg', '.jpg', '.png')) for p in self.input_paths):
                        messagebox.showerror("Error", "Please select only PDF, JPEG, JPG, or PNG files for OCR modes.", parent=self.root)
                        self.input_paths = []
                        input_display.config(text="Selected: None")
                        notebook.select(2)
                        return
                save_dir = filedialog.askdirectory(title="Select Directory to Save Output Files", parent=self.root)
                if not save_dir:
                    save_dir = os.path.expanduser("~/Desktop/CaseCracker/")
                    messagebox.showinfo("Info", f"No directory selected. Using default: {save_dir}", parent=self.root)
                os.makedirs(save_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d%H%M")
                timestamp_dir = os.path.join(save_dir, timestamp)
                os.makedirs(timestamp_dir, exist_ok=True)
                for subdir in ["JPEG", "OCR", "ANALYSIS", "QUARRY", "logs"]:
                    os.makedirs(os.path.join(timestamp_dir, subdir), exist_ok=True)
                self.save_dir = timestamp_dir
                save_display.config(text=f"Selected: {self.save_dir}")
                self.logger.debug(f"Selected save location: {self.save_dir}")
                notebook.select(4)

            ttk.Button(save_frame, text="Select Save Directory", command=select_save_dir).pack(pady=10)

            # Query Tab (Index 4)
            query_frame = ttk.Frame(notebook)
            notebook.add(query_frame, text="Query")
            ttk.Label(query_frame, text="Edit the analysis query:").pack(pady=10)
            query_text = tk.Text(query_frame, height=5, width=50)
            query_text.insert(tk.END, self.query)
            query_text.pack(pady=10)

            def start_processing():
                self.logger.debug("Starting processing")
                if self.processing_mode != "ocr_only":
                    self.query = query_text.get("1.0", tk.END).strip()
                    self.logger.debug("Query updated")
                if not (self.api_key and self.save_dir):
                    messagebox.showerror("Error", "Incomplete configuration. Please complete API Key and Save Location tabs.", parent=self.root)
                    self.logger.debug(f"Incomplete configuration: api_key={bool(self.api_key)}, save_dir={self.save_dir}")
                    return
                if len(self.input_paths) == 0:
                    messagebox.showerror("Error", "No files selected. Please select at least one file.", parent=self.root)
                    self.logger.debug(f"No files selected: input_paths={self.input_paths}")
                    return
                self.logger.debug(f"Starting processing with input_paths: {self.input_paths}")
                self.root.quit()

            ttk.Button(query_frame, text="Start Processing", command=start_processing).pack(pady=10)

            # Save input_paths before mainloop
            self.save_input_paths()

            self.logger.debug(f"Starting mainloop, input_paths: {self.input_paths}")
            self.root.mainloop()
            self.logger.debug(f"Mainloop ended, input_paths: {self.input_paths}")

            # Restore input_paths after mainloop
            self.restore_input_paths()

            self.logger.debug(f"Post-mainloop validation, input_paths: {self.input_paths}")
            if not (self.api_key and self.save_dir):
                raise ValueError("Incomplete configuration")
            if len(self.input_paths) == 0:
                raise ValueError("No files selected")
            self.logger.debug(f"Returning from GUI: input_paths={self.input_paths}")
            try:
                input_dir = os.path.dirname(self.input_paths[0])
            except IndexError:
                self.logger.error(f"IndexError in input_dir calculation, input_paths: {self.input_paths}")
                raise ValueError("No files selected after validation")
            input_files = [os.path.basename(p) for p in self.input_paths]
            return self.api_key, input_dir, input_files, self.save_dir, self.query, self.processing_mode

        except requests.RequestException as e:
            self.logger.exception(f"API request error: {str(e)}")
            raise
        except (OSError, IOError) as e:
            self.logger.exception(f"File operation error: {str(e)}")
            raise
        except ValueError as e:
            self.logger.exception(f"Configuration error: {str(e)}")
            raise
        except Exception as e:
            self.logger.exception(f"Unexpected error: {str(e)}")
            raise
        finally:
            if self.root and self.root.winfo_exists():
                self.logger.debug("Closing GUI")
                self.root.quit()
                self.root.destroy()