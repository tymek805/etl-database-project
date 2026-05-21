import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import traceback

import etl_products


SCENARIOS = {
    "Products Import": "products",
    "Customers Import": "customers",
}


class ETLApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETL Products Importer")
        self.root.geometry("600x550")
        self.root.minsize(1000, 800)

        self.input_file_var = tk.StringVar(value=str(etl_products.DEFAULT_INPUT_FILE))
        self.rejects_file_var = tk.StringVar(value=str(etl_products.DEFAULT_REJECTS_FILE))
        self.dry_run_var = tk.BooleanVar(value=False)
        self.scenario_var = tk.StringVar(value="products")

        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- Scenario Selection Section ---
        scenario_frame = ttk.LabelFrame(
            main_frame,
            text=" ETL Scenario ",
            padding="10"
        )

        scenario_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            scenario_frame,
            text="Scenario:"
        ).pack(side=tk.LEFT)

        scenario_dropdown = ttk.Combobox(
            scenario_frame,
            textvariable=self.scenario_var,
            values=[
                "products",
                "customers"
            ],
            state="readonly",
            width=30
        )

        scenario_dropdown.pack(side=tk.LEFT, padx=10)

        # --- File Selection Section ---
        file_frame = ttk.LabelFrame(main_frame, text=" File Configuration ", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 15))

        # Input File
        ttk.Label(file_frame, text="Input File (.csv / .json):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.input_file_var, width=40).grid(row=0, column=1, padx=10, pady=5,
                                                                               sticky=tk.EW)
        ttk.Button(file_frame, text="Browse...", command=self._browse_input).grid(row=0, column=2, pady=5)

        # Rejects File
        ttk.Label(file_frame, text="Rejects Report (.csv):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.rejects_file_var, width=40).grid(row=1, column=1, padx=10, pady=5,
                                                                                 sticky=tk.EW)
        ttk.Button(file_frame, text="Browse...", command=self._browse_rejects).grid(row=1, column=2, pady=5)

        file_frame.columnconfigure(1, weight=1)

        # --- Execution Options Section ---
        options_frame = ttk.LabelFrame(main_frame, text=" Execution Options ", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Checkbutton(
            options_frame,
            text="Dry Run (Extract & Transform only, no database saving)",
            variable=self.dry_run_var
        ).pack(anchor=tk.W)

        # --- Action Buttons ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 15))

        self.run_btn = ttk.Button(btn_frame, text="🚀 Run ETL Process", command=self._run_etl)
        self.run_btn.pack(side=tk.RIGHT, ipadx=10, ipady=5)

        # --- Console Output Section ---
        log_frame = ttk.LabelFrame(main_frame, text=" Results / Logs ", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED, bg="#f4f4f4", font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _browse_input(self):
        filename = filedialog.askopenfilename(
            title="Select Input Data",
            filetypes=(("Data Files", "*.csv *.json"), ("All Files", "*.*"))
        )
        if filename:
            self.input_file_var.set(filename)

    def _browse_rejects(self):
        filename = filedialog.asksaveasfilename(
            title="Select Rejects File Destination",
            defaultextension=".csv",
            filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*"))
        )
        if filename:
            self.rejects_file_var.set(filename)

    def _log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_logs(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _run_etl(self):
        input_file = self.input_file_var.get()
        rejects_file = self.rejects_file_var.get()
        is_dry_run = self.dry_run_var.get()

        if not input_file:
            messagebox.showwarning("Missing Information", "Please select an input file.")
            return

        self._clear_logs()
        self._log(
            f"Starting ETL Process...\nMode: {'DRY RUN' if is_dry_run else 'PRODUCTION (DB Save)'}\nInput: {input_file}")
        self.run_btn.config(state=tk.DISABLED)
        self.root.update()

        try:
            scenario = self.scenario_var.get()
            
            if scenario == "products":
                import etl_products as etl_module

            elif scenario == "customers":
                import etl_customers as etl_module

            else:
                raise ValueError(f"Unknown scenario: {scenario}")
                
            result = etl_module.run_etl(
                file_path=input_file,
                dry_run=is_dry_run,
                rejects_file=rejects_file
            )

            self._log("\n--- ETL Scenario Completed Successfully ---")

            for line in result.summary():
                self._log(line)

            if is_dry_run:
                self._log(
                    "\n(Database operations skipped due to Dry Run)"
                )

            messagebox.showinfo("Success", "ETL Process completed successfully!")

        except Exception as e:
            self._log("\n!!! AN ERROR OCCURRED !!!\n")
            self._log(traceback.format_exc())
            messagebox.showerror("Error", f"An error occurred during ETL:\n{str(e)}")

        finally:
            self.run_btn.config(state=tk.NORMAL)


if __name__ == "__main__":
    root = tk.Tk()
    app = ETLApp(root)
    root.mainloop()
