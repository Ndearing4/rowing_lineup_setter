import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yaml
import io
import sys
from contextlib import redirect_stdout

# Assuming the script is run from the root directory
from rower import Rower, Boat
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

        single_defaults = {
            'side_preference_penalty': 100.0,
            'experience_mixing_penalty': 10.0,
            'power_variance_penalty': 0.1,
            'stern_loading_penalty': 15.0,
            'days_since_boated_penalty': 5.0
        }

        multi_defaults = {
            'side_preference_penalty': 100.0,
            'experience_mixing_penalty': 1000.0,
            'inter_boat_variance_penalty': 100.0
        }

        if not isinstance(self.scoring_config.get('single_boat'), dict):
            self.scoring_config['single_boat'] = single_defaults.copy()
        else:
            # Fill any missing keys with defaults
            for k, v in single_defaults.items():
                self.scoring_config['single_boat'].setdefault(k, v)

        if not isinstance(self.scoring_config.get('multi_boat'), dict):
            self.scoring_config['multi_boat'] = multi_defaults.copy()
        else:
            # Fill any missing keys with defaults
            for k, v in multi_defaults.items():
                self.scoring_config['multi_boat'].setdefault(k, v)

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

        # --- Results Tab ---
        results_tab = ttk.Frame(notebook, padding="10")
        notebook.add(results_tab, text="Results")
        self.results_text = tk.Text(results_tab, wrap=tk.WORD, font=("Courier New", 10))
        self.results_text.pack(fill=tk.BOTH, expand=True)

        # --- Action Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        save_button = ttk.Button(button_frame, text="Save Configurations", command=self.save_configs)
        save_button.pack(side=tk.RIGHT, padx=5)

        run_button = ttk.Button(button_frame, text="Run Optimizer", command=self.run_optimizer)
        run_button.pack(side=tk.RIGHT)

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
        
        for key, var in self.scoring_config_vars.items():
            prefix, sub_key = key.split('_', 1)
            if self.scoring_config.get(prefix) and sub_key in self.scoring_config[prefix]:
                 var.set(self.scoring_config[prefix][sub_key])

    def save_configs(self):
        """Save the current configuration values back to the YAML files."""
        # Update main config
        for key, var in self.config_vars.items():
            self.config[key] = self.convert_value(var.get())
        
        # Update scoring config
        for key, var in self.scoring_config_vars.items():
            prefix, sub_key = key.split('_', 1)
            if prefix in self.scoring_config and sub_key in self.scoring_config[prefix]:
                self.scoring_config[prefix][sub_key] = self.convert_value(var.get())

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
