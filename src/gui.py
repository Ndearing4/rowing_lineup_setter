import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yaml
import io
import sys
import json
from contextlib import redirect_stdout
from typing import List

# Assuming the script is run from the root directory
from rower import Rower, Boat, Side, Experience
from simulated_annealing import LineupOptimizer
from multi_boat_optimizer import MultiBoatOptimizer
from lineup_setter import load_rowers_from_json, print_lineup_details, print_multi_lineup_details

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Rowing Lineup Setter")
        self.geometry("850x650")

        self.config_vars = {}
        self.scoring_config_vars = {}

        self.load_configs()
        self.create_widgets()
        self.populate_config_forms()

    def load_configs(self):
        """Load main and scoring configurations from YAML files."""
        try:
            with open('config.yaml', 'r') as f:
                self.config = yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError):
            self.config = {}

        try:
            with open('scoring_config.yaml', 'r') as f:
                self.scoring_config = yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError):
            self.scoring_config = {}

        # Ensure scoring config has defaults for both single and multi-boat
        if self.scoring_config is None:
            self.scoring_config = {}

        # Use the keys and order from scoring_config.yaml for the scoring tabs
        single_defaults = {
            'days_since_boated_penalty': 5.0,
            'experience_mixing_penalty': 1000.0,
            'power_variance_penalty': 0.1,
            'side_preference_penalty': 1000.0,
            'stern_loading_penalty': 60.0
        }

        # Multi-boat uses all single-boat parameters plus inter_boat_variance_penalty
        multi_defaults = dict(single_defaults)
        multi_defaults['inter_boat_variance_penalty'] = 100.0

        if not isinstance(self.scoring_config.get('single_boat'), dict):
            self.scoring_config['single_boat'] = single_defaults.copy()
        else:
            for k, v in single_defaults.items():
                self.scoring_config['single_boat'].setdefault(k, v)
            for k in list(self.scoring_config['single_boat'].keys()):
                if k not in single_defaults:
                    del self.scoring_config['single_boat'][k]

        # Multi-boat: copy all single-boat params, add inter_boat_variance_penalty, remove any extras
        if not isinstance(self.scoring_config.get('multi_boat'), dict):
            self.scoring_config['multi_boat'] = multi_defaults.copy()
        else:
            # Start with single_boat params
            for k, v in single_defaults.items():
                self.scoring_config['multi_boat'].setdefault(k, v)
            # Add inter_boat_variance_penalty
            self.scoring_config['multi_boat'].setdefault('inter_boat_variance_penalty', 100.0)
            # Remove any extras
            for k in list(self.scoring_config['multi_boat'].keys()):
                if k not in multi_defaults:
                    del self.scoring_config['multi_boat'][k]

    def create_widgets(self):
        """Create the main widgets for the application."""
        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Rowing Lineup Optimizer", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)

        # Notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        # --- Settings Tabs ---
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="Settings")
        
        settings_notebook = ttk.Notebook(settings_tab)
        settings_notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        general_tab = ttk.Frame(settings_notebook, padding="10")
        settings_notebook.add(general_tab, text="General")
        self.create_form_widgets(general_tab, self.config, self.config_vars)

        scoring_tab = ttk.Frame(settings_notebook, padding="10")
        settings_notebook.add(scoring_tab, text="Scoring Weights")
        
        scoring_notebook = ttk.Notebook(scoring_tab)
        scoring_notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        single_boat_tab = ttk.Frame(scoring_notebook, padding="10")
        multi_boat_tab = ttk.Frame(scoring_notebook, padding="10")
        
        scoring_notebook.add(single_boat_tab, text="Single Boat")
        scoring_notebook.add(multi_boat_tab, text="Multi-Boat")

        if self.scoring_config.get('single_boat'):
            self.create_form_widgets(single_boat_tab, self.scoring_config['single_boat'], self.scoring_config_vars, 'single_boat')
        if self.scoring_config.get('multi_boat'):
            self.create_form_widgets(multi_boat_tab, self.scoring_config['multi_boat'], self.scoring_config_vars, 'multi_boat')

        # --- Data Management Tab ---
        data_mgmt_tab = ttk.Frame(notebook, padding="10")
        notebook.add(data_mgmt_tab, text="Data Management")
        self.create_data_management_page(data_mgmt_tab)

        # --- Results Tab ---
        results_tab = ttk.Frame(notebook, padding="10")
        notebook.add(results_tab, text="Results")
        self.results_text = tk.Text(results_tab, wrap=tk.WORD, font=("Courier New", 10))
        self.results_text.pack(fill=tk.BOTH, expand=True)

        # --- Action Buttons and Lineup Type Dropdown ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        # Lineup type dropdown
        ttk.Label(button_frame, text="Lineup Type:").pack(side=tk.LEFT, padx=5)
        self.lineup_type_var = tk.StringVar(value="both")
        lineup_type_combo = ttk.Combobox(button_frame, textvariable=self.lineup_type_var, values=["varsity", "novice", "both"], state="readonly", width=10)
        lineup_type_combo.pack(side=tk.LEFT, padx=5)

        save_button = ttk.Button(button_frame, text="Save Configurations", command=self.save_configs)
        save_button.pack(side=tk.RIGHT, padx=5)

        run_button = ttk.Button(button_frame, text="Run Optimizer", command=self.run_optimizer)
        run_button.pack(side=tk.RIGHT)

    def create_data_management_page(self, parent):
        """Create the data management page for viewing and editing rower data."""
        # Top frame for file selection and buttons
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=10)

        ttk.Label(control_frame, text="Data File:").pack(side=tk.LEFT, padx=5)
        
        self.data_file_var = tk.StringVar(value=self.config.get('rower_data_file', 'sample_rowers.json'))
        file_entry = ttk.Entry(control_frame, textvariable=self.data_file_var, width=40)
        file_entry.pack(side=tk.LEFT, padx=5)

        browse_btn = ttk.Button(control_frame, text="Browse...", 
                                command=lambda: self.browse_file(self.data_file_var))
        browse_btn.pack(side=tk.LEFT, padx=5)

        load_btn = ttk.Button(control_frame, text="Load Data", command=self.load_data_management)
        load_btn.pack(side=tk.LEFT, padx=5)

        # Main content frame with canvas for scrolling
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(content_frame, bg="white")
        scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.data_frame = ttk.Frame(canvas, padding="10")

        self.data_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.data_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.rower_entries = []  # Store references to entry widgets and variables

        # Bottom frame for save buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)

        save_data_btn = ttk.Button(button_frame, text="Save Rower Data", 
                                   command=self.save_rower_data, style="Accent.TButton")
        save_data_btn.pack(side=tk.RIGHT, padx=5)

        add_rower_btn = ttk.Button(button_frame, text="Add New Rower", 
                                   command=self.add_new_rower_row)
        add_rower_btn.pack(side=tk.RIGHT, padx=5)

    def load_data_management(self):
        """Load rower data from JSON file and display in the data management page."""
        filepath = self.data_file_var.get()
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {filepath}")
            return
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON: {e}")
            return

        # Clear existing entries
        for widget in self.data_frame.winfo_children():
            widget.destroy()
        self.rower_entries = []

        # Create headers
        header_frame = ttk.Frame(self.data_frame)
        header_frame.pack(fill=tk.X, pady=10)

        headers = ["Name", "Erg Score", "Side Pref", "Experience", "Present Today", "Days Since Boated", ""]
        for i, header in enumerate(headers):
            label = ttk.Label(header_frame, text=header, font=("Helvetica", 10, "bold"))
            label.grid(row=0, column=i, padx=5, pady=5, sticky=tk.W)

        # Create entry widgets for each rower
        if 'rowers' in data:
            for rower_data in data['rowers']:
                self.add_rower_row(rower_data)

    def add_rower_row(self, rower_data=None):
        """Add a row of entry widgets for a rower."""
        row_frame = ttk.Frame(self.data_frame)
        row_frame.pack(fill=tk.X, pady=5)

        # Initialize default values
        if rower_data is None:
            rower_data = {
                'name': '',
                'erg_score': '',
                'side_preference': 'both',
                'experience': 'novice',
                'present_today': True,
                'days_since_boated': 0
            }

        # Name entry
        name_var = tk.StringVar(value=rower_data.get('name', ''))
        name_entry = ttk.Entry(row_frame, textvariable=name_var, width=15)
        name_entry.grid(row=0, column=0, padx=5, pady=5)

        # Erg score entry
        erg_var = tk.StringVar(value=str(rower_data.get('erg_score', '')))
        erg_entry = ttk.Entry(row_frame, textvariable=erg_var, width=12)
        erg_entry.grid(row=0, column=1, padx=5, pady=5)

        # Side preference dropdown
        side_var = tk.StringVar(value=rower_data.get('side_preference', 'both'))
        side_combo = ttk.Combobox(row_frame, textvariable=side_var, 
                                   values=['port', 'starboard', 'both'], width=10, state='readonly')
        side_combo.grid(row=0, column=2, padx=5, pady=5)

        # Experience dropdown
        exp_var = tk.StringVar(value=rower_data.get('experience', 'novice'))
        exp_combo = ttk.Combobox(row_frame, textvariable=exp_var, 
                                  values=['novice', 'varsity'], width=10, state='readonly')
        exp_combo.grid(row=0, column=3, padx=5, pady=5)

        # Present today checkbox
        present_var = tk.BooleanVar(value=rower_data.get('present_today', True))
        present_check = ttk.Checkbutton(row_frame, variable=present_var)
        present_check.grid(row=0, column=4, padx=5, pady=5)

        # Days since boated entry
        days_var = tk.StringVar(value=str(rower_data.get('days_since_boated', 0)))
        days_entry = ttk.Entry(row_frame, textvariable=days_var, width=8)
        days_entry.grid(row=0, column=5, padx=5, pady=5)

        # Delete button
        delete_btn = ttk.Button(row_frame, text="Delete", 
                               command=lambda: self.delete_rower_row(row_frame))
        delete_btn.grid(row=0, column=6, padx=5, pady=5)

        # Store references
        self.rower_entries.append({
            'frame': row_frame,
            'name_var': name_var,
            'erg_var': erg_var,
            'side_var': side_var,
            'exp_var': exp_var,
            'present_var': present_var,
            'days_var': days_var
        })

    def add_new_rower_row(self):
        """Add a new empty rower row."""
        self.add_rower_row()

    def delete_rower_row(self, row_frame):
        """Delete a rower row from the display."""
        for entry_dict in self.rower_entries:
            if entry_dict['frame'] == row_frame:
                self.rower_entries.remove(entry_dict)
                break
        row_frame.destroy()

    def save_rower_data(self):
        """Save the edited rower data back to the JSON file."""
        filepath = self.data_file_var.get()
        
        rowers_list = []
        for entry_dict in self.rower_entries:
            name = entry_dict['name_var'].get().strip()
            
            # Skip empty rows
            if not name:
                continue
            
            try:
                erg_score = float(entry_dict['erg_var'].get())
            except ValueError:
                messagebox.showerror("Error", f"Invalid erg score for {name}")
                return

            try:
                days_since_boated = int(entry_dict['days_var'].get())
            except ValueError:
                messagebox.showerror("Error", f"Invalid days since boated for {name}")
                return

            rower_dict = {
                'name': name,
                'erg_score': erg_score,
                'side_preference': entry_dict['side_var'].get(),
                'experience': entry_dict['exp_var'].get(),
                'present_today': entry_dict['present_var'].get(),
                'days_since_boated': days_since_boated
            }
            rowers_list.append(rower_dict)

        # Save to JSON file
        data = {'rowers': rowers_list}
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Success", f"Rower data saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save rower data:\n{e}")

    def create_form_widgets(self, parent, config_data, var_dict, prefix=''):
        """Create label and entry widgets for configuration data."""
        row = 0
        for key, value in config_data.items():
            label = ttk.Label(parent, text=f"{key.replace('_', ' ').title()}:")
            label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
            
            # Render 'multi_boat' as a checkbox instead of a text entry
            if prefix == '' and key == 'multi_boat':
                var = tk.BooleanVar(value=bool(value))
                check = ttk.Checkbutton(parent, variable=var)
                check.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
            else:
                var = tk.StringVar()
                entry = ttk.Entry(parent, textvariable=var, width=30)
                entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
            
            if key == 'rower_data_file':
                browse_button = ttk.Button(parent, text="Browse...", command=lambda v=var: self.browse_file(v))
                browse_button.grid(row=row, column=2, padx=5)

            full_key = f"{prefix}_{key}" if prefix else key
            var_dict[full_key] = var
            row += 1

    def browse_file(self, var):
        """Open a file dialog to select a file."""
        filepath = filedialog.askopenfilename(
            title="Select Rower Data File",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
        )
        if filepath:
            var.set(filepath)

    def populate_config_forms(self):
        """Populate the entry widgets with loaded configuration values."""
        for key, var in self.config_vars.items():
            if isinstance(var, tk.BooleanVar):
                var.set(bool(self.config.get(key, False)))
            else:
                var.set(self.config.get(key, ''))

        # Populate scoring weights from scoring_config.yaml
        for key, var in self.scoring_config_vars.items():
            prefix, sub_key = key.split('_', 1)
            if self.scoring_config.get(prefix) and sub_key in self.scoring_config[prefix]:
                var.set(str(self.scoring_config[prefix][sub_key]))

    def save_configs(self):
        """Save the current configuration values back to the YAML files."""
        # Update main config
        for key, var in self.config_vars.items():
            self.config[key] = self.convert_value(var.get())

        # Update scoring config: single_boat gets all except inter_boat_variance_penalty, multi_boat gets only inter_boat_variance_penalty
        single_boat = {}
        multi_boat = {}
        for key, var in self.scoring_config_vars.items():
            prefix, sub_key = key.split('_', 1)
            value = self.convert_value(var.get())
            if sub_key == 'inter_boat_variance_penalty':
                multi_boat[sub_key] = value
            else:
                single_boat[sub_key] = value
        # Only keep inter_boat_variance_penalty in multi_boat
        self.scoring_config['single_boat'] = single_boat
        self.scoring_config['multi_boat'] = {}
        if 'inter_boat_variance_penalty' in multi_boat:
            self.scoring_config['multi_boat']['inter_boat_variance_penalty'] = multi_boat['inter_boat_variance_penalty']

        try:
            with open('config.yaml', 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            with open('scoring_config.yaml', 'w') as f:
                yaml.dump(self.scoring_config, f, default_flow_style=False)
            messagebox.showinfo("Success", "Configurations saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configurations:\n{e}")

    def convert_value(self, value_str):
        """Try to convert string value to int, float, or bool."""
        if isinstance(value_str, (bool, int, float)):
            return value_str
        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False
        try:
            return int(value_str)
        except ValueError:
            try:
                return float(value_str)
            except ValueError:
                return value_str

    def get_current_config(self):
        """Get the current configuration from the GUI."""
        current_config = {}
        for key, var in self.config_vars.items():
            current_config[key] = self.convert_value(var.get())
        
        current_scoring_config = {'single_boat': {}, 'multi_boat': {}}
        invalid_keys = []
        for key, var in self.scoring_config_vars.items():
            if key.startswith('single_boat_'):
                prefix = 'single_boat'
                sub_key = key.replace('single_boat_', '', 1)
            elif key.startswith('multi_boat_'):
                prefix = 'multi_boat'
                sub_key = key.replace('multi_boat_', '', 1)
            else:
                continue  # Should not happen with current setup

            value_str = var.get().strip()
            # If empty, fall back to current stored config default
            if value_str == '':
                value = self.scoring_config.get(prefix, {}).get(sub_key)
            else:
                try:
                    value = float(value_str)
                except ValueError:
                    invalid_keys.append(f"{prefix}.{sub_key}='{value_str}'")
                    value = None

            if value is not None:
                current_scoring_config[prefix][sub_key] = value

        if invalid_keys:
            raise ValueError(
                "Invalid scoring values (must be numeric): " + ", ".join(invalid_keys)
            )

        return current_config, current_scoring_config

    def run_optimizer(self):
        """Gathers config, runs the optimizer, and displays the result."""
        self.results_text.delete('1.0', tk.END)
        
        try:
            config, scoring_config = self.get_current_config()
        except ValueError as e:
            messagebox.showerror("Invalid Scoring Configuration", str(e))
            return


        try:
            rowers = load_rowers_from_json(config['rower_data_file'], config.get('convert_6k', False))
        except FileNotFoundError:
            messagebox.showerror("Error", f"Rower data file not found: {config['rower_data_file']}")
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load rower data:\n{e}")
            return

        # Filter to only include rowers marked as present today
        rowers = [r for r in rowers if getattr(r, 'present_today', True)]

        # Further filter by lineup type
        lineup_type = self.lineup_type_var.get()
        if lineup_type == "varsity":
            rowers = [r for r in rowers if getattr(r, 'experience', None) == Experience.VARSITY]
        elif lineup_type == "novice":
            rowers = [r for r in rowers if getattr(r, 'experience', None) == Experience.NOVICE]

        if not rowers:
            messagebox.showerror("Error", "No rowers match the selected criteria.")
            return

        # Determine which optimizer to use
        if config.get('multi_boat'):
            optimizer_class = MultiBoatOptimizer
            num_boats = len(rowers) // config['boat_type']
            if num_boats == 0:
                messagebox.showerror("Error", "Not enough rowers to create any boats.")
                return
            scoring_config_to_use = scoring_config['multi_boat']
            print(f"Optimizing for {num_boats} boats of {config['boat_type']}...")
        else:
            optimizer_class = LineupOptimizer
            scoring_config_to_use = scoring_config['single_boat']

        # Redirect stdout to capture print statements
        output_stream = io.StringIO()
        with redirect_stdout(output_stream):
            # Respect runs parameter: perform multiple runs and pick best
            runs = config.get('runs', 1)
            try:
                runs = int(runs)
            except (ValueError, TypeError):
                runs = 1

            best_optimizer = None
            best_cost = float('inf')

            for i in range(max(1, runs)):
                optimizer = optimizer_class(
                    rowers=rowers,
                    boat_type=config['boat_type'],
                    config=config,
                    scoring_config=scoring_config_to_use
                )
                _, current_cost = optimizer.optimize()
                if runs > 1:
                    try:
                        print(f"--- Running optimization {i+1}/{runs} Cost: {current_cost:.2f} ---")
                    except Exception:
                        print(f"--- Running optimization {i+1}/{runs} Cost: {current_cost} ---")
                if current_cost < best_cost:
                    best_optimizer = optimizer
                    best_cost = current_cost

            # Print results from the best run
            if best_optimizer is not None:
                best_optimizer.print_results()
        
        # Display the captured output
        self.results_text.insert(tk.END, output_stream.getvalue())
        # Switch to the results tab
        for i, tab_text in enumerate(self.results_text.master.master.tabs()):
            if self.results_text.master.master.tab(i, "text") == "Results":
                self.results_text.master.master.select(i)
                break


if __name__ == "__main__":
    app = App()
    app.mainloop()
