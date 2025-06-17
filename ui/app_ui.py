import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import os

class AppUI:
    def __init__(self, root, app):
        self.root = root
        self.app = app  # Reference to the main SolarEdgeAPIApp instance

        # Initialize UI elements (will be populated by moved methods)
        self.site_id_combobox = None
        self.full_site_display_list = [] # This might be managed by AppUI or synced from app

        # References to frames that will be created by moved methods
        self.credentials_frame = None
        self.data_type_choice_frame = None
        self.data_specific_inputs_frame = None
        self.date_range_frame = None
        self.options_frame = None
        self.action_frame = None
        self.status_frame = None # This might stay in main app or be passed

        # Site details tabs
        self.site_details_tabview = None
        self.tab_overview = None
        self.tab_inventory = None
        self.tab_power_flow = None
        self.tab_alerts = None
        self.alerts_treeview_frame = None # Specific frame for alerts treeview
        self.alert_start_date_entry = None
        self.alert_end_date_entry = None
        self.fetch_alerts_button_tab = None

        # Data export UI elements
        self.data_type_var = tk.StringVar(value="production")
        self.inverter_frame = None
        self.inverter_entry = None
        self.meters_frame = None
        self.production_var = tk.BooleanVar(value=True)
        self.consumption_var = tk.BooleanVar(value=False)
        self.self_consumption_var = tk.BooleanVar(value=False)
        self.feed_in_var = tk.BooleanVar(value=False)
        self.purchased_var = tk.BooleanVar(value=False)

        self.start_date_calendar = None
        self.start_hour_var = tk.StringVar(value="00")
        self.end_date_calendar = None
        self.end_hour_var = tk.StringVar(value="23")
        self.time_unit_var = tk.StringVar(value="HOUR")

        self.file_format_var = tk.StringVar(value="csv")
        self.output_path_var = tk.StringVar(value=os.path.expanduser("~"))

        self.fetch_button = None # For data export
        self.cancel_button = None # For cancelling operations

        # Status elements (might be controlled by main app and passed or managed here)
        self.status_label = None
        self.progress_bar = None

        # Call UI creation methods
        self._create_main_layout() # To setup frames similar to original __init__
        self.create_credentials_section(self.credentials_frame)
        self.create_data_type_sections(self.data_type_choice_frame, self.data_specific_inputs_frame)
        self.create_date_range_section(self.date_range_frame)
        self.create_options_section(self.options_frame)
        self.create_action_section(self.action_frame)
        # self.create_status_section(self.status_frame) # Status section might be better handled by main app
        self._create_site_details_tabs(self.app.main_container) # Pass parent for tabview

        self.update_ui_for_data_type()


    def _create_main_layout(self):
        # This method recreates the frame structure from SolarEdgeAPIApp.__init__
        # Main container is already in self.app.main_container

        # Top frame for controls
        self.top_frame = ctk.CTkFrame(self.app.main_container)
        self.top_frame.pack(fill="x", padx=5, pady=5)

        self.title_label = ctk.CTkLabel(self.top_frame, text="SolarEdge API Data Fetcher",
                                        font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=10)

        self.credentials_frame = ctk.CTkFrame(self.top_frame)
        self.credentials_frame.pack(fill="x", padx=10, pady=(5,0))

        self.data_type_choice_frame = ctk.CTkFrame(self.top_frame)
        self.data_type_choice_frame.pack(fill="x", padx=10, pady=(5,0))

        self.data_specific_inputs_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.data_specific_inputs_frame.pack(fill="x", padx=10, pady=0)

        self.date_range_frame = ctk.CTkFrame(self.top_frame)
        self.date_range_frame.pack(fill="x", padx=10, pady=(5,0))

        self.options_frame = ctk.CTkFrame(self.top_frame)
        self.options_frame.pack(fill="x", padx=10, pady=(5,0))

        self.action_frame = ctk.CTkFrame(self.top_frame)
        self.action_frame.pack(fill="x", padx=10, pady=(10,5))

        # Tabview for site-specific details - will be created in _create_site_details_tabs
        # self.site_details_tabview will be parented to self.app.main_container

        # Status frame is likely managed by the main app, so not recreated here
        # self.status_frame = ctk.CTkFrame(self.app.main_container)
        # self.status_frame.pack(fill="x", side="bottom", padx=5, pady=5)

    # Placeholder for methods to be moved
    def _create_site_details_tabs(self, parent_container):
        self.site_details_tabview = ctk.CTkTabview(parent_container)
        # Tabview will be packed later, or shown/hidden by on_site_selected
        self.site_details_tabview.pack_forget() # Initially hidden

        try:
            self.tab_overview = self.site_details_tabview.add("Overview")
            self.tab_inventory = self.site_details_tabview.add("Inventory")
            self.tab_power_flow = self.site_details_tabview.add("Power Flow")
            self.tab_alerts = self.site_details_tabview.add("Alerts")

            # Placeholder content or setup for each tab
            ctk.CTkLabel(self.tab_overview, text="Select a site to view its overview.", padx=10, pady=10).pack()
            ctk.CTkLabel(self.tab_inventory, text="Select a site to view its inventory.", padx=10, pady=10).pack()
            ctk.CTkLabel(self.tab_power_flow, text="Select a site to view its current power flow.", padx=10, pady=10).pack()

            # Setup for Alerts Tab
            alerts_controls_frame = ctk.CTkFrame(self.tab_alerts)
            alerts_controls_frame.pack(fill="x", padx=5, pady=5)
            ctk.CTkLabel(alerts_controls_frame, text="Start Date:").grid(row=0, column=0, padx=5, pady=2)
            self.alert_start_date_entry = DateEntry(alerts_controls_frame, width=12, date_pattern='yyyy-mm-dd')
            self.alert_start_date_entry.grid(row=0, column=1, padx=5, pady=2)
            self.alert_start_date_entry.set_date(datetime.now() - timedelta(days=7))

            ctk.CTkLabel(alerts_controls_frame, text="End Date:").grid(row=0, column=2, padx=5, pady=2)
            self.alert_end_date_entry = DateEntry(alerts_controls_frame, width=12, date_pattern='yyyy-mm-dd')
            self.alert_end_date_entry.grid(row=0, column=3, padx=5, pady=2)
            self.alert_end_date_entry.set_date(datetime.now())

            self.fetch_alerts_button_tab = ctk.CTkButton(alerts_controls_frame, text="Fetch Alerts for Range", command=self.app.fetch_site_alerts_thread_from_tab) # Call app method
            self.fetch_alerts_button_tab.grid(row=0, column=4, padx=10, pady=2)

            # Placeholder for alerts display (e.g., Treeview)
            self.alerts_treeview_frame = ctk.CTkFrame(self.tab_alerts) # Store as instance variable
            self.alerts_treeview_frame.pack(fill="both", expand=True, padx=5, pady=5)
            ctk.CTkLabel(self.alerts_treeview_frame, text="Alerts will be displayed here.").pack()

        except Exception as e:
            print(f"Error creating site details tabs: {e}")
            messagebox.showerror("UI Error", "Could not initialize site detail tabs.")

    def create_credentials_section(self, parent_frame):
        credentials_label = ctk.CTkLabel(parent_frame, text="API Credentials & Site Selection", font=ctk.CTkFont(size=16, weight="bold"))
        credentials_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(5, 2))

        account_api_key_label = ctk.CTkLabel(parent_frame, text="Account API Key:")
        account_api_key_label.grid(row=1, column=0, sticky="w", padx=10, pady=2)

        # The main app will need access to this entry's value.
        # It can be accessed via self.app.ui.account_api_key_entry if ui is stored on app
        self.app.account_api_key_entry = ctk.CTkEntry(parent_frame, width=300) # Store on app
        self.app.account_api_key_entry.grid(row=1, column=1, sticky="we", padx=10, pady=2)

        # The main app will need access to this button's state.
        self.app.fetch_sites_button = ctk.CTkButton(parent_frame, text="Fetch Sites", command=self.app.fetch_sites_thread) # Store on app
        self.app.fetch_sites_button.grid(row=1, column=2, sticky="w", padx=10, pady=2)

        site_id_label = ctk.CTkLabel(parent_frame, text="Site ID (type to search):")
        site_id_label.grid(row=2, column=0, sticky="w", padx=10, pady=2)

        self.site_id_combobox = ctk.CTkComboBox(parent_frame, width=400, values=[], command=self.on_site_selected) # Uses self.on_site_selected
        self.site_id_combobox.grid(row=2, column=1, columnspan=2, sticky="we", padx=10, pady=2)
        self.site_id_combobox.set("Enter Site ID or select/search from list")

        try:
            self.site_id_combobox._entry.bind("<KeyRelease>", self.filter_site_list_handler) # Uses self.filter_site_list_handler
        except AttributeError:
            if self.site_id_combobox.winfo_children() and isinstance(self.site_id_combobox.winfo_children()[0], (tk.Entry, ctk.CTkEntry)):
                self.site_id_combobox.winfo_children()[0].bind("<KeyRelease>", self.filter_site_list_handler)
            else:
                print("Warning: Could not bind KeyRelease to ComboBox for site filtering.")

        parent_frame.grid_columnconfigure(1, weight=1)
        parent_frame.grid_columnconfigure(2, weight=0)

    def filter_site_list_handler(self, event=None):
        current_text = self.site_id_combobox.get()
        if not self.full_site_display_list: # Uses self.full_site_display_list (local to AppUI)
            return
        if not current_text.strip():
            filtered_values = self.full_site_display_list
        else:
            search_term = current_text.lower()
            filtered_values = [name for name in self.full_site_display_list if search_term in name.lower()]

        # Update combobox values. If filtered_values is empty, show "No match found..."
        # otherwise, if current_text is also empty (meaning user cleared the search),
        # show all values again.
        if not filtered_values and current_text:
            self.site_id_combobox.configure(values=["No match found..."])
        elif not current_text: # Cleared search
             self.site_id_combobox.configure(values=self.full_site_display_list if self.full_site_display_list else [])
        else:
            self.site_id_combobox.configure(values=filtered_values)


    def on_site_selected(self, selected_site_display_name_event_arg=None):
        # selected_site_display_name_event_arg is the value from combobox command
        selected_site_display_name = self.site_id_combobox.get()

        site_id = self.app.site_name_to_id_map.get(selected_site_display_name)
        if not site_id:
            if selected_site_display_name.isdigit():
                site_id = int(selected_site_display_name)
            else:
                self.clear_site_details_tabs_content()
                # Do not show messagebox if it's an initial placeholder or no match
                if selected_site_display_name not in ["Enter Site ID or select/search from list", "No match found...", "No sites found or error."]:
                     messagebox.showwarning("Invalid Site", f"'{selected_site_display_name}' is not a recognized site.")
                return

        if self.app.is_fetching: # Check main app's fetching status
            # messagebox.showinfo("Busy", "An operation is already in progress. Site details will not be fetched now.")
            return

        self.app.current_selected_site_id = site_id # Update current_selected_site_id in main app

        if self.site_details_tabview:
            self.site_details_tabview.pack(fill="both", expand=True, padx=5, pady=5) # Show tabview

        self.clear_site_details_tabs_content(show_loading=True)

        # Call the main app's method to handle data fetching and further UI updates
        self.app.handle_site_selection_data(site_id)


    def clear_site_details_tabs_content(self, show_loading=False):
        # Ensure all tab attributes are checked for existence before clearing
        tabs_to_clear = []
        if hasattr(self, 'tab_overview') and self.tab_overview:
            tabs_to_clear.append(self.tab_overview)
        if hasattr(self, 'tab_inventory') and self.tab_inventory:
            tabs_to_clear.append(self.tab_inventory)
        if hasattr(self, 'tab_power_flow') and self.tab_power_flow:
            tabs_to_clear.append(self.tab_power_flow)

        # Special handling for alerts_treeview_frame as it's a direct frame, not a tab object from TabView
        if hasattr(self, 'alerts_treeview_frame') and self.alerts_treeview_frame:
            # This frame is inside the self.tab_alerts. We are clearing its content.
            for widget in self.alerts_treeview_frame.winfo_children():
                widget.destroy()
            if show_loading: # Add loading label specifically to alerts_treeview_frame
                 ctk.CTkLabel(self.alerts_treeview_frame, text="Loading data...").pack(padx=10, pady=10)

        # For overview, inventory, power_flow tabs
        for tab_content_frame in tabs_to_clear:
            for widget in tab_content_frame.winfo_children():
                widget.destroy()
            if show_loading:
                ctk.CTkLabel(tab_content_frame, text="Loading data...").pack(padx=10, pady=10)

        # For alerts tab, also reset the alerts tree specifically if it was more complex
        # This is done by clearing alerts_treeview_frame above.
        # If alerts_tree is a specific widget that needs individual clearing beyond destroying children of its parent:
        if hasattr(self, 'alerts_tree') and self.alerts_tree:
             # Assuming alerts_tree is a ttk.Treeview. If it's None or already destroyed, this might error.
             try:
                 for i in self.alerts_tree.get_children():
                     self.alerts_tree.delete(i)
             except tk.TclError: # Widget might be destroyed already
                 self.alerts_tree = None # Reset it


    def populate_overview_tab(self, overview):
        # Ensure self.tab_overview exists
        if not hasattr(self, 'tab_overview') or not self.tab_overview:
            print("Error: tab_overview is not initialized in AppUI.")
            return

        for widget in self.tab_overview.winfo_children():
            widget.destroy()
        if not overview:
            ctk.CTkLabel(self.tab_overview, text="Failed to load overview data or no data available.", text_color="orange").pack(padx=10,pady=10)
            return
        if overview.get("error"):
            ctk.CTkLabel(self.tab_overview, text=f"Error loading overview: {overview['error']}", text_color="orange", wraplength=400).pack(padx=10,pady=10)
            return

        frame = ctk.CTkScrollableFrame(self.tab_overview)
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        def add_overview_item(label_text, value_data, unit=""):
            item_frame = ctk.CTkFrame(frame, fg_color="transparent")
            item_frame.pack(fill="x", pady=1)
            ctk.CTkLabel(item_frame, text=f"{label_text}:", width=200, anchor="w").pack(side="left", padx=5)
            val_text = str(value_data) if value_data is not None else "N/A"
            ctk.CTkLabel(item_frame, text=f"{val_text} {unit}", anchor="w").pack(side="left", padx=5)

        add_overview_item("Last Update Time", overview.get("lastUpdateTime", "N/A"))
        if overview.get("currentPower"):
            add_overview_item("Current Power", overview["currentPower"].get("power"), "W")
        if overview.get("lastDayData"):
            add_overview_item("Energy - Last Day", overview["lastDayData"].get("energy"), "Wh")
        if overview.get("lastMonthData"):
            add_overview_item("Energy - Last Month", overview["lastMonthData"].get("energy"), "Wh")
        if overview.get("lastYearData"):
            add_overview_item("Energy - Last Year", overview["lastYearData"].get("energy"), "Wh")
        if overview.get("lifeTimeData"):
            add_overview_item("Energy - Lifetime", overview["lifeTimeData"].get("energy"), "Wh")

    def populate_inventory_tab(self, inventory):
        if not hasattr(self, 'tab_inventory') or not self.tab_inventory:
            print("Error: tab_inventory is not initialized in AppUI.")
            return

        for widget in self.tab_inventory.winfo_children():
            widget.destroy()
        if not inventory:
            ctk.CTkLabel(self.tab_inventory, text="Failed to load inventory data or no data available.", text_color="orange").pack(padx=10,pady=10)
            return
        if inventory.get("error"):
            ctk.CTkLabel(self.tab_inventory, text=f"Error loading inventory: {inventory['error']}", text_color="orange", wraplength=400).pack(padx=10,pady=10)
            return

        tree_frame = ctk.CTkFrame(self.tab_inventory)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Using ttk.Treeview as CTk doesn't have a direct equivalent yet
        style = ttk.Style()
        # TODO: Consider better styling that works with CTk themes if possible, or a CTkTable widget if available
        style.theme_use("default") # Use a theme that allows configuration for Treeview
        # Configure Treeview colors to be more aligned with CustomTkinter theme if needed
        # style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#343638", bordercolor="#565b5e")
        # style.configure("Treeview.Heading", background="#565b5e", foreground="white", relief="flat")
        # style.map("Treeview.Heading", relief=[('active','groove'),('pressed','sunken')])


        cols = ("Manufacturer", "Model", "Serial Number", "Name/Type")
        tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode="browse")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor="w") # Adjust width as needed
        tree.pack(fill="both", expand=True)

        def add_inventory_items(items, item_type_name):
            if items:
                for item in items:
                    tree.insert("", "end", values=(
                        item.get("manufacturer", "N/A"),
                        item.get("model", "N/A"),
                        item.get("serialNumber", item.get("SN", "N/A")), # Some use SN
                        item.get("name", item_type_name)
                    ))

        if "inverters" in inventory:
            add_inventory_items(inventory["inverters"], "Inverter")
        if "batteries" in inventory:
            add_inventory_items(inventory["batteries"], "Battery")
        if "meters" in inventory:
            add_inventory_items(inventory["meters"], "Meter")
        # Add other types if present, e.g., gateways, sensors
        if "sensors" in inventory:
            add_inventory_items(inventory["sensors"], "Sensor")
        if "gateways" in inventory:
            add_inventory_items(inventory["gateways"], "Gateway")

        if not tree.get_children(): # If no items were added
            tree.insert("", "end", values=("No equipment data found in inventory.", "", "", ""))


    def populate_power_flow_tab(self, power_flow):
        if not hasattr(self, 'tab_power_flow') or not self.tab_power_flow:
            print("Error: tab_power_flow is not initialized in AppUI.")
            return

        for widget in self.tab_power_flow.winfo_children():
            widget.destroy()
        if not power_flow:
            ctk.CTkLabel(self.tab_power_flow, text="Failed to load power flow data or no data available.", text_color="orange").pack(padx=10,pady=10)
            return
        if power_flow.get("error"):
            ctk.CTkLabel(self.tab_power_flow, text=f"Error loading power flow: {power_flow['error']}", text_color="orange", wraplength=400).pack(padx=10,pady=10)
            return

        frame = ctk.CTkScrollableFrame(self.tab_power_flow)
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(frame, text=f"Unit of Power: {power_flow.get('unit', 'N/A')}", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=2)

        # The connections array itself is usually less important for display than the summarized values.
        # data_points = {} # This was for a more complex parsing of 'connections'

        def add_flow_item(label, source_data_dict_key, status_key=None):
            # source_data_dict_key is the key like "PV", "LOAD", "GRID", "STORAGE" in the power_flow dict
            source_data = power_flow.get(source_data_dict_key)

            item_frame = ctk.CTkFrame(frame, fg_color="transparent")
            item_frame.pack(fill="x", pady=1)
            ctk.CTkLabel(item_frame, text=f"{label}:", width=150, anchor="w").pack(side="left", padx=5)

            power_val_text = "N/A"
            status_text = ""

            if isinstance(source_data, dict): # Standard format like "LOAD": {"currentPower": 0.84, "status": "Active"}
                power_val_text = str(source_data.get("currentPower", "N/A"))
                if status_key and source_data.get(status_key):
                    status_text = f"({source_data.get(status_key)})"
            elif isinstance(source_data, list) and source_data: # Alternative format like "PV": [{"currentPower": 3.5}]
                 # Assuming the first element in the list is the relevant one for PV
                pv_entry = source_data[0]
                if isinstance(pv_entry, dict):
                    power_val_text = str(pv_entry.get("currentPower", "N/A"))
                    # Status for PV usually isn't provided this way, but handle if it were
                    if status_key and pv_entry.get(status_key):
                         status_text = f"({pv_entry.get(status_key)})"
            elif source_data is None: # Key exists but value is null
                 power_val_text = "N/A (Not reported)"
            # Else: if source_data is something else, power_val_text remains "N/A"

            ctk.CTkLabel(item_frame, text=power_val_text, width=100, anchor="w").pack(side="left", padx=5)
            if status_text:
                ctk.CTkLabel(item_frame, text=status_text, anchor="w").pack(side="left", padx=5)

        add_flow_item("PV Production", "PV")
        add_flow_item("Consumption (Load)", "LOAD") # Typically has currentPower directly if site has consumption meter
        add_flow_item("Grid", "GRID", status_key="status") # e.g. status: "Import" / "Export" / "Disconnected"
        add_flow_item("Storage (Battery)", "STORAGE", status_key="status") # e.g. status: "Charging" / "Discharging" / "Idle" / "Disconnected"

    def populate_alerts_tab(self, alerts_list, error=None):
        # Ensure self.alerts_treeview_frame exists
        if not hasattr(self, 'alerts_treeview_frame') or not self.alerts_treeview_frame:
            print("Error: alerts_treeview_frame is not initialized in AppUI.")
            return

        # Clear previous content from the specific frame for alerts treeview
        for widget in self.alerts_treeview_frame.winfo_children():
            widget.destroy()
        self.alerts_tree = None # Reset tree view reference

        if error and error != "cancelled":
            if "403" in error and ("Date format issues" in error or "Date range too large" in error or "alerts" in error.lower()): # Be more specific for 403
                error_text = "⚠️ Alerts Request Error (403)\n\nCommon causes:\n• Date range too large (try < 1 month).\n• Invalid date format or server-side issue.\n• API key lacks permissions for alerts endpoint.\n• Frequent requests leading to rate limiting.\n\nSuggestions:\n1. Reduce the date range significantly.\n2. Wait a moment and try again.\n3. Verify API key permissions if possible."
            elif "403" in error: # Generic 403
                 error_text = f"⚠️ Access Denied (403)\n\nCould not fetch alerts. This may be due to API key restrictions or temporary server issues.\nDetails: {error}"
            elif "timeout" in error.lower():
                error_text = f"⏳ Timeout Error\n\nFetching alerts took too long to respond. Check your internet connection or try again later.\nDetails: {error}"
            else:
                error_text = f"❌ Error Loading Alerts\n\nAn unexpected error occurred.\nDetails: {error}"
            text_color = "orange" if "403" in error or "timeout" in error.lower() else "red"

            ctk.CTkLabel(self.alerts_treeview_frame, text=error_text, text_color=text_color, wraplength=self.alerts_treeview_frame.winfo_width() - 20, justify="center").pack(padx=10, pady=20)
            return
        if error == "cancelled":
            ctk.CTkLabel(self.alerts_treeview_frame, text="Alert fetching cancelled.", text_color="orange").pack(padx=10, pady=10)
            return
        if not alerts_list:
            ctk.CTkLabel(self.alerts_treeview_frame, text="No alerts found for the selected period or data not available.").pack(padx=10, pady=10)
            return

        cols = ("Timestamp", "Severity", "Code", "Description")
        # Consider adding a ttk.Style configuration here if not done globally and if needed for theming Treeview
        self.alerts_tree = ttk.Treeview(self.alerts_treeview_frame, columns=cols, show='headings', selectmode="browse")

        for col_name in cols:
            self.alerts_tree.heading(col_name, text=col_name)
            col_width = 120
            if col_name == "Description": col_width = 300
            elif col_name == "Timestamp": col_width = 140
            elif col_name == "Code": col_width = 80
            self.alerts_tree.column(col_name, width=col_width, anchor="w")

        # Add scrollbars
        ysb = ttk.Scrollbar(self.alerts_treeview_frame, orient="vertical", command=self.alerts_tree.yview)
        xsb = ttk.Scrollbar(self.alerts_treeview_frame, orient="horizontal", command=self.alerts_tree.xview)
        self.alerts_tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        ysb.pack(side='right', fill='y')
        xsb.pack(side='bottom', fill='x')
        self.alerts_tree.pack(fill="both", expand=True)


        for alert in alerts_list:
            timestamp_str = alert.get("date", "N/A")
            try: # Try to parse and reformat if it's a full timestamp
                dt_obj = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                timestamp_str = dt_obj.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError): # Keep original if not in expected format or not a string
                pass

            self.alerts_tree.insert("", "end", values=(
                timestamp_str,
                alert.get("severity", "N/A"),
                alert.get("id", "N/A"),
                alert.get("description", alert.get("message", "N/A"))
            ))

    def create_data_type_sections(self, choice_parent_frame, specific_inputs_parent_frame):
        data_type_label = ctk.CTkLabel(choice_parent_frame, text="Data Type (for Export)", font=ctk.CTkFont(size=16, weight="bold"))
        data_type_label.pack(anchor="w", padx=10, pady=(5, 2))

        # self.data_type_var is already initialized in __init__
        self.radio_buttons_frame = ctk.CTkFrame(choice_parent_frame, fg_color="transparent")
        self.radio_buttons_frame.pack(fill="x", padx=10, pady=0)

        ctk.CTkRadioButton(self.radio_buttons_frame, text="Production Details (Energy)", variable=self.data_type_var, value="production", command=self.update_ui_for_data_type).grid(row=0, column=0, sticky="w", padx=10, pady=2)
        ctk.CTkRadioButton(self.radio_buttons_frame, text="Voltage Values (Equipment)", variable=self.data_type_var, value="voltage", command=self.update_ui_for_data_type).grid(row=0, column=1, sticky="w", padx=10, pady=2)

        # Inverter frame - self.inverter_frame and self.inverter_entry are initialized in __init__
        # specific_inputs_parent_frame is self.data_specific_inputs_frame
        self.inverter_frame = ctk.CTkFrame(specific_inputs_parent_frame) # Parent is data_specific_inputs_frame
        ctk.CTkLabel(self.inverter_frame, text="Inverter Serial Number:").grid(row=0, column=0, sticky="w", padx=10, pady=2)
        self.inverter_entry = ctk.CTkEntry(self.inverter_frame, width=200)
        self.inverter_entry.grid(row=0, column=1, sticky="we", padx=10, pady=2)
        self.inverter_frame.grid_columnconfigure(1, weight=1)

        # Meters frame - self.meters_frame and boolean vars are initialized in __init__
        self.meters_frame = ctk.CTkFrame(specific_inputs_parent_frame) # Parent is data_specific_inputs_frame
        ctk.CTkLabel(self.meters_frame, text="Select Meters:").grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=2)

        # self.production_var etc. are already initialized
        ctk.CTkCheckBox(self.meters_frame, text="Production", variable=self.production_var).grid(row=1, column=0, sticky="w", padx=10, pady=1)
        ctk.CTkCheckBox(self.meters_frame, text="Consumption", variable=self.consumption_var).grid(row=1, column=1, sticky="w", padx=10, pady=1)
        ctk.CTkCheckBox(self.meters_frame, text="Self Consumption", variable=self.self_consumption_var).grid(row=2, column=0, sticky="w", padx=10, pady=1)
        ctk.CTkCheckBox(self.meters_frame, text="Feed In (Export)", variable=self.feed_in_var).grid(row=2, column=1, sticky="w", padx=10, pady=1)
        ctk.CTkCheckBox(self.meters_frame, text="Purchased (Import)", variable=self.purchased_var).grid(row=3, column=0, sticky="w", padx=10, pady=1)

    def update_ui_for_data_type(self):
        data_type = self.data_type_var.get()

        # Ensure data_specific_inputs_frame is available
        if not hasattr(self, 'data_specific_inputs_frame') or not self.data_specific_inputs_frame:
            # This might happen if called too early, defer if necessary.
            # However, it's called at the end of AppUI.__init__, so frames should exist.
            print("Warning: data_specific_inputs_frame not ready for update_ui_for_data_type")
            self.root.after(50, self.update_ui_for_data_type) # Try again shortly
            return

        for w in self.data_specific_inputs_frame.winfo_children():
            w.pack_forget() # Hide all children first

        # Ensure date calendars are initialized before trying to set their dates
        # This method is called at the end of AppUI.__init__, after create_date_range_section
        # So, self.start_date_calendar and self.end_date_calendar should exist.
        if not hasattr(self, 'start_date_calendar') or not self.start_date_calendar or \
           not hasattr(self, 'end_date_calendar') or not self.end_date_calendar:
            # If calendars aren't ready, defer this call.
            # This indicates create_date_range_section hasn't fully run or initialized them.
            print("Warning: Date calendars not ready for update_ui_for_data_type. Retrying...")
            self.root.after(100, self.update_ui_for_data_type) # Defer and retry
            return

        current_date = datetime.now()
        if data_type == "voltage":
            if self.inverter_frame: # Ensure it exists
                self.inverter_frame.pack(in_=self.data_specific_inputs_frame, fill="x", padx=0, pady=2)
            self.end_date_calendar.set_date(current_date) # Default 7 days for voltage
            self.start_date_calendar.set_date(current_date - timedelta(days=6))
        else: # "production"
            if self.meters_frame: # Ensure it exists
                self.meters_frame.pack(in_=self.data_specific_inputs_frame, fill="x", padx=0, pady=2)
            self.end_date_calendar.set_date(current_date) # Default 30 days for production
            self.start_date_calendar.set_date(current_date - timedelta(days=29))


    def create_date_range_section(self, parent_frame):
        ctk.CTkLabel(parent_frame, text="Date Range (for Data Export)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(5,2))

        ctk.CTkLabel(parent_frame, text="Start Date:").grid(row=1, column=0, sticky="w", padx=10, pady=2)
        # Using tk.Frame for DateEntry parent to avoid potential CTk theming issues with DateEntry's internal tk widgets
        # Alternatively, DateEntry could be styled directly if its options allow full CTk compatibility
        sdf_container = tk.Frame(parent_frame)
        sdf_container.grid(row=1, column=1, sticky="w", padx=10, pady=2)

        today = datetime.now()
        initial_start_date = today - timedelta(days=29) # Default for production
        # self.start_date_calendar, self.start_hour_var etc. are already initialized in __init__
        self.start_date_calendar = DateEntry(sdf_container, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', year=initial_start_date.year, month=initial_start_date.month, day=initial_start_date.day, maxdate=today)
        self.start_date_calendar.pack(fill="both", expand=True)

        ctk.CTkLabel(parent_frame, text="Hour:").grid(row=1, column=2, sticky="w", padx=(20,5), pady=2)
        # self.start_hour_var is tk.StringVar initialized in __init__
        ctk.CTkOptionMenu(parent_frame, values=[f"{i:02d}" for i in range(24)], variable=self.start_hour_var, width=60).grid(row=1, column=3, sticky="w", padx=5, pady=2)

        ctk.CTkLabel(parent_frame, text="End Date:").grid(row=2, column=0, sticky="w", padx=10, pady=2)
        edf_container = tk.Frame(parent_frame)
        edf_container.grid(row=2, column=1, sticky="w", padx=10, pady=2)
        self.end_date_calendar = DateEntry(edf_container, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', year=today.year, month=today.month, day=today.day, maxdate=today)
        self.end_date_calendar.pack(fill="both", expand=True)

        ctk.CTkLabel(parent_frame, text="Hour:").grid(row=2, column=2, sticky="w", padx=(20,5), pady=2)
        # self.end_hour_var is tk.StringVar initialized in __init__
        ctk.CTkOptionMenu(parent_frame, values=[f"{i:02d}" for i in range(24)], variable=self.end_hour_var, width=60).grid(row=2, column=3, sticky="w", padx=5, pady=2)

        ctk.CTkLabel(parent_frame, text="Time Unit (Prod. Data):").grid(row=3, column=0, sticky="w", padx=10, pady=2)
        # self.time_unit_var is tk.StringVar initialized in __init__
        ctk.CTkOptionMenu(parent_frame, values=["HOUR","DAY","WEEK","MONTH"], variable=self.time_unit_var).grid(row=3, column=1, sticky="we", padx=10, pady=2)


    def create_options_section(self, parent_frame):
        ctk.CTkLabel(parent_frame, text="Output Options (for Data Export)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0,column=0,columnspan=3,sticky="w",padx=10,pady=(5,2))

        ctk.CTkLabel(parent_frame, text="File Format:").grid(row=1,column=0,sticky="w",padx=10,pady=2)
        # self.file_format_var is tk.StringVar initialized in __init__
        ffrf=ctk.CTkFrame(parent_frame,fg_color="transparent")
        ffrf.grid(row=1,column=1,columnspan=2,sticky="w",pady=0)
        ctk.CTkRadioButton(ffrf,text="CSV",variable=self.file_format_var,value="csv").pack(side="left",padx=10,pady=0)
        ctk.CTkRadioButton(ffrf,text="Excel",variable=self.file_format_var,value="excel").pack(side="left",padx=10,pady=0)

        ctk.CTkLabel(parent_frame, text="Output Folder:").grid(row=2,column=0,sticky="w",padx=10,pady=2)
        # self.output_path_var is tk.StringVar initialized in __init__
        ctk.CTkEntry(parent_frame,textvariable=self.output_path_var,width=300).grid(row=2,column=1,sticky="we",padx=10,pady=2)
        ctk.CTkButton(parent_frame,text="Browse...",command=self.browse_output_folder,width=100).grid(row=2,column=2,sticky="w",padx=10,pady=2)
        parent_frame.grid_columnconfigure(1,weight=1)

    def browse_output_folder(self):
        # self.output_path_var is a tk.StringVar
        fp = filedialog.askdirectory(initialdir=self.output_path_var.get())
        if fp: # If a folder was selected (fp is not empty or None)
            self.output_path_var.set(fp)

    def create_action_section(self, parent_frame):
        # These buttons are for the "Data Export" functionality.
        # The main app (self.app) will have its methods (start_fetch_thread, cancel_fetch) called.
        # We store references to these buttons on self.app so the main app can control their state if needed,
        # though state changes are often initiated from main app logic already.

        # self.fetch_button is initialized to None in __init__
        self.fetch_button = ctk.CTkButton(parent_frame,text="Fetch and Save Export Data",command=self.app.start_fetch_thread,font=ctk.CTkFont(size=14,weight="bold"),height=40)
        self.fetch_button.pack(pady=10)
        # Make it accessible by the main app if it needs to change its state, e.g. self.app.ui.fetch_button
        # Or, more directly if SolarEdgeAPIApp refers to these as self.fetch_button
        self.app.fetch_button = self.fetch_button


        # self.cancel_button is initialized to None in __init__
        self.cancel_button = ctk.CTkButton(parent_frame,text="Cancel Current Operation",command=self.app.cancel_fetch,font=ctk.CTkFont(size=14),height=30,fg_color="#D32F2F",hover_color="#C62828")
        # This button is initially not packed; it's packed by the main app when an operation starts.
        # self.cancel_button.pack_forget()
        self.app.cancel_button = self.cancel_button


    # def create_status_section(self, parent_frame): # Likely stays in main app
    #     pass

pass
