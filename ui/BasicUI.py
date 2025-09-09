import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import json
import os
import sys
import threading
from datetime import datetime
from typing import Optional

# Add the engine_core directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'engine_core'))

try:
    from RuleCore import CriminalBackgroundRuleEngine, RuleEngineError, RuleEngineResult
except ImportError as e:
    print(f"Error importing RuleCore: {e}")
    print("Make sure RuleCore.py, CheckrAPI.py, and CriminalCheck.py are in the engine_core directory")

class BackgroundCheckUI:
    """Tkinter GUI for the Criminal Background Check Rule Engine."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Criminal Background Check System")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Initialize rule engine (will be done when first needed)
        self.rule_engine = None
        self.current_result = None
        
        self.setup_ui()
        self.update_status("Ready")
    
    def setup_ui(self):
        """Setup the main UI components."""
        
        # Create main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Criminal Background Check System", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Person Information Section
        self.setup_person_info_section(main_frame, start_row=1)
        
        # Action Buttons Section
        self.setup_action_buttons(main_frame, start_row=8)
        
        # Results Section
        self.setup_results_section(main_frame, start_row=10)
        
        # Status Bar
        self.setup_status_bar(main_frame, start_row=12)
    
    def setup_person_info_section(self, parent, start_row):
        """Setup the person information input section."""
        
        # Section label
        info_label = ttk.Label(parent, text="Person Information", font=("Arial", 12, "bold"))
        info_label.grid(row=start_row, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        # Create input fields
        self.fields = {}
        
        # Required fields
        required_fields = [
            ("First Name*", "first_name"),
            ("Last Name*", "last_name")
        ]
        
        # Optional fields
        optional_fields = [
            ("Date of Birth (YYYY-MM-DD)", "dob"),
            ("Middle Name", "middle_name"),
            ("SSN (XXX-XX-XXXX)", "ssn"),
            ("Email", "email"),
            ("Phone (+1XXXXXXXXXX)", "phone"),
            ("Reference ID", "reference_id")
        ]
        
        row = start_row + 1
        
        # Add required fields
        for label_text, field_name in required_fields:
            label = ttk.Label(parent, text=label_text)
            label.grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)
            
            entry = ttk.Entry(parent, width=30)
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
            
            self.fields[field_name] = entry
            row += 1
        
        # Add optional fields
        for label_text, field_name in optional_fields:
            label = ttk.Label(parent, text=label_text)
            label.grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)
            
            entry = ttk.Entry(parent, width=30)
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
            
            self.fields[field_name] = entry
            row += 1
        
        # Address section (simplified)
        address_label = ttk.Label(parent, text="Address (Optional)")
        address_label.grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        address_frame = ttk.Frame(parent)
        address_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        
        # Address fields in a compact layout
        self.address_fields = {}
        address_entries = [
            ("Street", "street", 0, 0, 2),
            ("City", "city", 1, 0, 1),
            ("State", "state", 1, 1, 1),
            ("ZIP", "zip_code", 2, 0, 1)
        ]
        
        for i, (addr_label, addr_field, addr_row, addr_col, addr_span) in enumerate(address_entries):
            ttk.Label(address_frame, text=f"{addr_label}:").grid(
                row=addr_row*2, column=addr_col, sticky=tk.W, padx=(0, 5), pady=1
            )
            entry = ttk.Entry(address_frame, width=20)
            entry.grid(row=addr_row*2+1, column=addr_col, columnspan=addr_span, 
                      sticky=(tk.W, tk.E), padx=(0, 5), pady=1)
            self.address_fields[addr_field] = entry
    
    def setup_action_buttons(self, parent, start_row):
        """Setup action buttons."""
        
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=start_row, column=0, columnspan=3, pady=20)
        
        # Run Check Button
        self.run_button = ttk.Button(button_frame, text="Run Background Check", 
                                    command=self.run_background_check, style="Accent.TButton")
        self.run_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Clear Form Button
        clear_button = ttk.Button(button_frame, text="Clear Form", command=self.clear_form)
        clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Export Results Button
        self.export_button = ttk.Button(button_frame, text="Export Results", 
                                       command=self.export_results, state="disabled")
        self.export_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Load Test Data Button
        test_button = ttk.Button(button_frame, text="Load Test Data", command=self.load_test_data)
        test_button.pack(side=tk.LEFT)
    
    def setup_results_section(self, parent, start_row):
        """Setup the results display section."""
        
        # Results label
        results_label = ttk.Label(parent, text="Background Check Results", 
                                 font=("Arial", 12, "bold"))
        results_label.grid(row=start_row, column=0, columnspan=3, sticky=tk.W, pady=(20, 10))
        
        # Create notebook for tabbed results
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=start_row+1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Configure grid weight for notebook
        parent.rowconfigure(start_row+1, weight=1)
        
        # Summary Tab
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="Summary")
        
        self.summary_text = scrolledtext.ScrolledText(self.summary_frame, height=15, wrap=tk.WORD)
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Detailed Results Tab
        self.details_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.details_frame, text="Detailed Results")
        
        self.details_text = scrolledtext.ScrolledText(self.details_frame, height=15, wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Raw Data Tab
        self.raw_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.raw_frame, text="Raw API Data")
        
        self.raw_text = scrolledtext.ScrolledText(self.raw_frame, height=15, wrap=tk.WORD)
        self.raw_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def setup_status_bar(self, parent, start_row):
        """Setup status bar."""
        
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(parent, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.grid(row=start_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def update_status(self, message):
        """Update status bar message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_var.set(f"[{timestamp}] {message}")
        self.root.update_idletasks()
    
    def initialize_rule_engine(self):
        """Initialize the rule engine if not already done."""
        if self.rule_engine is None:
            try:
                self.update_status("Initializing rule engine...")
                
                # Look for config files in engine_core directory
                engine_core_dir = os.path.join(os.path.dirname(__file__), '..', 'engine_core')
                checkr_config = os.path.join(engine_core_dir, 'checkr_config.json')
                risk_config = os.path.join(engine_core_dir, 'config.json')
                
                self.rule_engine = CriminalBackgroundRuleEngine(
                    checkr_config_path=checkr_config,
                    risk_config_path=risk_config
                )
                self.update_status("Rule engine initialized successfully")
                
            except Exception as e:
                error_msg = f"Failed to initialize rule engine: {str(e)}"
                self.update_status(error_msg)
                messagebox.showerror("Initialization Error", error_msg)
                return False
        return True
    
    def get_form_data(self):
        """Extract form data and validate required fields."""
        
        # Get basic person data
        data = {}
        for field_name, entry in self.fields.items():
            value = entry.get().strip()
            if value:
                data[field_name] = value
        
        # Validate required fields
        if not data.get('first_name'):
            raise ValueError("First name is required")
        if not data.get('last_name'):
            raise ValueError("Last name is required")
        
        # Get address data if any fields are filled
        address_data = {}
        for addr_field, entry in self.address_fields.items():
            value = entry.get().strip()
            if value:
                address_data[addr_field] = value
        
        if address_data:
            data['address'] = address_data
        
        return data
    
    def run_background_check(self):
        """Run the background check in a separate thread."""
        
        try:
            # Validate form data
            form_data = self.get_form_data()
            
            # Initialize rule engine if needed
            if not self.initialize_rule_engine():
                return
            
            # Disable the run button
            self.run_button.config(state="disabled")
            self.update_status("Running background check...")
            
            # Clear previous results
            self.clear_results()
            
            # Run in separate thread to prevent UI freezing
            def run_check():
                try:
                    result = self.rule_engine.run_complete_background_check(**form_data)
                    
                    # Update UI in main thread
                    self.root.after(0, lambda: self.display_results(result))
                    
                except Exception as e:
                    error_msg = f"Background check failed: {str(e)}"
                    self.root.after(0, lambda: self.handle_error(error_msg))
            
            # Start background thread
            thread = threading.Thread(target=run_check, daemon=True)
            thread.start()
            
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            self.handle_error(f"Error starting background check: {str(e)}")
    
    def display_results(self, result: RuleEngineResult):
        """Display the background check results."""
        
        self.current_result = result
        
        # Enable export button
        self.export_button.config(state="normal")
        
        # Re-enable run button
        self.run_button.config(state="normal")
        
        # Display summary
        self.display_summary(result)
        
        # Display detailed results
        self.display_detailed_results(result)
        
        # Display raw API data
        self.display_raw_data(result)
        
        # Update status with recommendation
        risk_color = {
            "Clean": "green",
            "Low": "blue", 
            "Medium": "orange",
            "High": "red"
        }.get(result.overall_risk_level.value, "black")
        
        self.update_status(f"Background check completed - Risk: {result.overall_risk_level.value}")
        
        # Show completion message
        messagebox.showinfo("Background Check Complete", 
                           f"Risk Level: {result.overall_risk_level.value}\n\n{result.recommendation}")
    
    def display_summary(self, result: RuleEngineResult):
        """Display summary results."""
        
        summary = f"""BACKGROUND CHECK SUMMARY
{'='*50}

Person: {result.person_info['first_name']} {result.person_info['last_name']}
Check ID: {result.checkr_check_id}
Processed: {result.person_info['processed_at']}
Execution Time: {result.execution_time_seconds:.2f} seconds

OVERALL ASSESSMENT:
Risk Level: {result.overall_risk_level.value}
Recommendation: {result.recommendation}

CASE DISTRIBUTION:
"""
        
        for risk_level, cases in result.processed_cases.items():
            summary += f"  {risk_level}: {len(cases)} case(s)\n"
        
        summary += f"\nTOTAL CASES PROCESSED: {result.summary['total_cases']}\n"
        summary += f"HIGHEST RISK SCORE: {result.summary['highest_risk_score']}\n"
        
        if result.summary.get('recommendations'):
            summary += f"\nADDITIONAL NOTES:\n"
            for rec in result.summary['recommendations']:
                summary += f"  - {rec}\n"
        
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(1.0, summary)
    
    def display_detailed_results(self, result: RuleEngineResult):
        """Display detailed case-by-case results."""
        
        details = f"""DETAILED CASE ANALYSIS
{'='*50}

"""
        
        for risk_level, cases in result.processed_cases.items():
            if cases:
                details += f"{risk_level.upper()} RISK CASES ({len(cases)}):\n"
                details += f"{'-'*40}\n"
                
                for i, case in enumerate(cases, 1):
                    details += f"{i}. Case: {case.case_number}\n"
                    details += f"   Description: {case.charge_description}\n"
                    details += f"   Date: {case.offense_date}\n"
                    details += f"   Type: {case.charge_type}\n"
                    details += f"   Disposition: {case.disposition}\n"
                    details += f"   Category: {case.category}\n"
                    if case.subcategory:
                        details += f"   Subcategory: {case.subcategory}\n"
                    details += f"   Risk Score: {case.risk_score}\n"
                    details += f"   Reason: {case.reason}\n\n"
                
                details += "\n"
        
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, details)
    
    def display_raw_data(self, result: RuleEngineResult):
        """Display raw API response data."""
        
        raw_data = json.dumps(result.checkr_response, indent=2)
        self.raw_text.delete(1.0, tk.END)
        self.raw_text.insert(1.0, raw_data)
    
    def clear_results(self):
        """Clear all result displays."""
        self.summary_text.delete(1.0, tk.END)
        self.details_text.delete(1.0, tk.END)
        self.raw_text.delete(1.0, tk.END)
        self.current_result = None
        self.export_button.config(state="disabled")
    
    def handle_error(self, error_msg):
        """Handle errors and re-enable UI."""
        self.run_button.config(state="normal")
        self.update_status("Error occurred")
        messagebox.showerror("Error", error_msg)
    
    def clear_form(self):
        """Clear all form fields."""
        for entry in self.fields.values():
            entry.delete(0, tk.END)
        
        for entry in self.address_fields.values():
            entry.delete(0, tk.END)
        
        self.clear_results()
        self.update_status("Form cleared")
    
    def load_test_data(self):
        """Load test data for demonstration."""
        test_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'dob': '1990-01-15',
            'middle_name': 'Michael',
            'ssn': '123-45-6789',
            'email': 'john.doe@example.com',
            'phone': '+14155552671',
            'reference_id': 'test-ui-001'
        }
        
        address_data = {
            'street': '123 Main St',
            'city': 'Anytown',
            'state': 'CA',
            'zip_code': '12345'
        }
        
        # Fill form fields
        for field_name, value in test_data.items():
            if field_name in self.fields:
                self.fields[field_name].delete(0, tk.END)
                self.fields[field_name].insert(0, value)
        
        for field_name, value in address_data.items():
            if field_name in self.address_fields:
                self.address_fields[field_name].delete(0, tk.END)
                self.address_fields[field_name].insert(0, value)
        
        self.update_status("Test data loaded")
    
    def export_results(self):
        """Export results to JSON file."""
        if not self.current_result:
            messagebox.showwarning("No Results", "No results to export")
            return
        
        try:
            # Ask user for save location
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Background Check Results"
            )
            
            if filename:
                exported_file = self.rule_engine.export_results_json(self.current_result, filename)
                self.update_status(f"Results exported to {exported_file}")
                messagebox.showinfo("Export Successful", f"Results exported to:\n{exported_file}")
        
        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            self.update_status(error_msg)
            messagebox.showerror("Export Error", error_msg)


def main():
    """Main function to run the UI."""
    
    # Create and configure the main window
    root = tk.Tk()
    
    # Configure styling
    style = ttk.Style()
    style.theme_use('clam')  # Use a modern theme
    
    # Create the application
    app = BackgroundCheckUI(root)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    # Start the GUI
    root.mainloop()


if __name__ == "__main__":
    main()