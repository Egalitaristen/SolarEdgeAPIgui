import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import requests
import json
import pandas as pd
import os
import time
import threading
import openpyxl

# Custom exception for cancellation
class OperationCancelledError(Exception):
    pass

class SolarEdgeAPIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SolarEdge API Data Fetcher")
        
        try:
            self.root.state('zoomed')
        except tk.TclError:
            try:
                self.root.attributes('-zoomed', True)
            except tk.TclError:
                print("Note: Could not maximize window automatically. Setting a default size.")
                self.root.geometry("1200x800") # Fallback size
        
        self.root.resizable(True, True)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        # Main container frame
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Top frame for controls
        self.top_frame = ctk.CTkFrame(self.main_container)
        self.top_frame.pack(fill="x", padx=5, pady=5)
        
        self.title_label = ctk.CTkLabel(self.top_frame, text="SolarEdge API Data Fetcher",
                                        font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=10)
        
        self.credentials_frame = ctk.CTkFrame(self.top_frame)
        self.credentials_frame.pack(fill="x", padx=10, pady=(5,0))
        
        self.data_type_choice_frame = ctk.CTkFrame(self.top_frame) # For "Production/Voltage" choice
        self.data_type_choice_frame.pack(fill="x", padx=10, pady=(5,0))

        self.data_specific_inputs_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent") # For meters/inverter SN
        self.data_specific_inputs_frame.pack(fill="x", padx=10, pady=0)

        self.date_range_frame = ctk.CTkFrame(self.top_frame) # For data export date range
        self.date_range_frame.pack(fill="x", padx=10, pady=(5,0))
        
        self.options_frame = ctk.CTkFrame(self.top_frame) # For file format/output folder
        self.options_frame.pack(fill="x", padx=10, pady=(5,0))
        
        self.action_frame = ctk.CTkFrame(self.top_frame) # For "Fetch and Save Data" button
        self.action_frame.pack(fill="x", padx=10, pady=(10,5))

        # Tabview for site-specific details
        self.site_details_tabview = ctk.CTkTabview(self.main_container)
        # Tabview will be packed later, or shown/hidden
        self.site_details_tabview.pack_forget() # Initially hidden

        self.tab_overview = None
        self.tab_inventory = None
        self.tab_power_flow = None
        self.tab_alerts = None
        self._create_site_details_tabs() # Create tabs but they might be empty initially

        self.status_frame = ctk.CTkFrame(self.main_container) # Status bar at the very bottom
        self.status_frame.pack(fill="x", side="bottom", padx=5, pady=5)

        self.site_name_to_id_map = {} 
        self.full_site_display_list = [] 
        self.is_fetching = False 
        self.current_selected_site_id = None # To track current site for auto-fetch

        self.create_credentials_section()
        self.create_data_type_sections() # For data export type
        self.create_date_range_section() # For data export
        self.create_options_section()    # For data export
        self.create_action_section()     # For data export
        self.create_status_section()

        self.update_ui_for_data_type() # For data export section

    def _create_site_details_tabs(self):
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
            
            self.fetch_alerts_button_tab = ctk.CTkButton(alerts_controls_frame, text="Fetch Alerts for Range", command=self.fetch_site_alerts_thread_from_tab)
            self.fetch_alerts_button_tab.grid(row=0, column=4, padx=10, pady=2)
            
            # Placeholder for alerts display (e.g., Treeview)
            self.alerts_treeview_frame = ctk.CTkFrame(self.tab_alerts)
            self.alerts_treeview_frame.pack(fill="both", expand=True, padx=5, pady=5)
            ctk.CTkLabel(self.alerts_treeview_frame, text="Alerts will be displayed here.").pack()

        except Exception as e:
            print(f"Error creating site details tabs: {e}")
            messagebox.showerror("UI Error", "Could not initialize site detail tabs.")

    def create_credentials_section(self):
        credentials_label = ctk.CTkLabel(self.credentials_frame, text="API Credentials & Site Selection", font=ctk.CTkFont(size=16, weight="bold"))
        credentials_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(5, 2))
        
        account_api_key_label = ctk.CTkLabel(self.credentials_frame, text="Account API Key:")
        account_api_key_label.grid(row=1, column=0, sticky="w", padx=10, pady=2)
        
        self.account_api_key_entry = ctk.CTkEntry(self.credentials_frame, width=300)
        self.account_api_key_entry.grid(row=1, column=1, sticky="we", padx=10, pady=2)
        
        self.fetch_sites_button = ctk.CTkButton(self.credentials_frame, text="Fetch Sites", command=self.fetch_sites_thread)
        self.fetch_sites_button.grid(row=1, column=2, sticky="w", padx=10, pady=2)
        
        site_id_label = ctk.CTkLabel(self.credentials_frame, text="Site ID (type to search):")
        site_id_label.grid(row=2, column=0, sticky="w", padx=10, pady=2)
        
        self.site_id_combobox = ctk.CTkComboBox(self.credentials_frame, width=400, values=[], command=self.on_site_selected)
        self.site_id_combobox.grid(row=2, column=1, columnspan=2, sticky="we", padx=10, pady=2)
        self.site_id_combobox.set("Enter Site ID or select/search from list")
        
        try:
            self.site_id_combobox._entry.bind("<KeyRelease>", self.filter_site_list_handler)
        except AttributeError:
            if self.site_id_combobox.winfo_children() and isinstance(self.site_id_combobox.winfo_children()[0], (tk.Entry, ctk.CTkEntry)):
                self.site_id_combobox.winfo_children()[0].bind("<KeyRelease>", self.filter_site_list_handler)
            else: 
                print("Warning: Could not bind KeyRelease to ComboBox for site filtering.")
        
        self.credentials_frame.grid_columnconfigure(1, weight=1)
        self.credentials_frame.grid_columnconfigure(2, weight=0)

    def filter_site_list_handler(self, event=None):
        current_text = self.site_id_combobox.get()
        if not self.full_site_display_list: 
            return
        if not current_text.strip(): 
            filtered_values = self.full_site_display_list
        else:
            search_term = current_text.lower()
            filtered_values = [name for name in self.full_site_display_list if search_term in name.lower()]
        self.site_id_combobox.configure(values=filtered_values if filtered_values else ["No match found..."])

    def fetch_sites_thread(self):
        account_key = self.account_api_key_entry.get()
        if not account_key: 
            messagebox.showerror("Missing API Key", "Please enter the Account API Key.")
            return
        if self.is_fetching: 
            messagebox.showwarning("In Progress", "Another operation is currently in progress.")
            return
        
        self.is_fetching = True 
        self.fetch_sites_button.configure(state="disabled")
        self.fetch_button.configure(state="disabled") 
        self.cancel_button.pack(pady=5)
        self.status_label.configure(text="Fetching site list...")
        self.progress_bar.set(0)
        self.progress_bar.start()
        self.root.update()
        
        thread = threading.Thread(target=self._execute_fetch_sites, args=(account_key,))
        thread.daemon = True
        thread.start()

    def _execute_fetch_sites(self, account_api_key):
        all_sites = []
        start_index = 0
        max_results_per_call = 100
        total_sites_fetched = 0
        expected_total_sites = -1
        self.full_site_display_list = [] 
        
        try:
            while True:
                self.check_if_cancelled() 
                api_url = "https://monitoringapi.solaredge.com/sites/list"
                params = {
                    "api_key": account_api_key, 
                    "size": max_results_per_call, 
                    "startIndex": start_index 
                }
                response = requests.get(api_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if "sites" in data and "site" in data["sites"]:
                        current_batch = data["sites"]["site"]
                        all_sites.extend(current_batch)
                        
                        if expected_total_sites == -1 : 
                            expected_total_sites = data["sites"].get("count", 0)
                        
                        total_sites_fetched += len(current_batch)
                        
                        if expected_total_sites > 0: 
                            self.progress_bar.set(min(total_sites_fetched / expected_total_sites, 0.95))
                        else: 
                            self.progress_bar.set(0.5)
                        
                        self.status_label.configure(text=f"Fetched {total_sites_fetched}/{expected_total_sites if expected_total_sites >0 else 'many'} sites...")
                        self.root.update()
                        
                        if total_sites_fetched >= expected_total_sites or not current_batch or len(current_batch) < max_results_per_call: 
                            break
                        
                        start_index += len(current_batch)
                        time.sleep(0.25)
                    else: 
                        messagebox.showwarning("Site List Format", "API response for site list not in expected format.")
                        break
                else: 
                    error_msg_prefix = f"Failed to fetch site list (Status: {response.status_code})"
                    error_details = ""
                    try:
                        json_error = response.json()
                        if "String" in json_error and isinstance(json_error["String"], dict) and "message" in json_error["String"]: 
                            error_details = json_error["String"]["message"]
                        elif "message" in json_error: 
                            error_details = json_error["message"]
                        elif "error" in json_error and "message" in json_error["error"]: 
                            error_details = json_error["error"]["message"]
                        else: 
                            error_details = response.text[:150] + "..." if response.text else "No error details."
                    except json.JSONDecodeError: 
                        error_details = response.text[:150] + "..." if response.text else "Non-JSON response."
                    
                    full_error_msg = f"{error_msg_prefix}\nDetails: {error_details}"
                    print(f"Site Fetch API Error: {full_error_msg}") 
                    
                    if response.status_code in [401, 403]: 
                        messagebox.showerror("API Key Error", f"Site list fetch failed: {response.status_code}.\nCheck Account API Key and permissions.\nDetails: {error_details}")
                    else: 
                        messagebox.showerror("API Error", f"Site list fetch failed: {response.status_code}.\nDetails: {error_details}")
                    break 
            
            self.site_name_to_id_map.clear()
            if all_sites:
                temp_display_list = [f"{site.get('name', 'N/A')} ({site.get('id', 'N/A')})" for site in all_sites]
                for site_info, display_name in zip(all_sites, temp_display_list): 
                    self.site_name_to_id_map[display_name] = site_info.get('id')
                
                self.full_site_display_list = sorted(temp_display_list)
                self.site_id_combobox.configure(values=self.full_site_display_list)
                
                if self.full_site_display_list: 
                    self.site_id_combobox.set(self.full_site_display_list[0])
                    self.on_site_selected(self.full_site_display_list[0])
                
                self.status_label.configure(text=f"Successfully fetched {len(self.full_site_display_list)} sites.")
            else:
                self.full_site_display_list = []
                self.site_id_combobox.set("No sites found or error.")
                self.site_id_combobox.configure(values=[])
                if expected_total_sites != -1 : 
                    self.status_label.configure(text="No sites found for the API Key.")
                    
        except OperationCancelledError: 
            self.status_label.configure(text="Site fetching cancelled.")
        except requests.exceptions.RequestException as e: 
            messagebox.showerror("Connection Error", f"Could not connect for site list: {e}")
            self.status_label.configure(text="Error fetching sites: Connection failed.")
        except Exception as e: 
            messagebox.showerror("Error", f"Error fetching sites: {e}")
            self.status_label.configure(text="Error fetching sites.")
            import traceback
            traceback.print_exc()
        finally:
            self.progress_bar.stop()
            self.progress_bar.set(0)
            self.is_fetching = False 
            self.fetch_sites_button.configure(state="normal")
            self.fetch_button.configure(state="normal")
            self.cancel_button.pack_forget()               
            
            current_status = self.status_label.cget("text")
            if not any(s in current_status for s in ["Successfully fetched", "No sites found", "Error fetching sites", "cancelled"]): 
                self.status_label.configure(text="Ready.")

    def on_site_selected(self, selected_site_display_name_event_arg):
        # The event argument might be the value itself if called from command
        # or an event object if bound differently. For CTkComboBox command, it's the value.
        selected_site_display_name = self.site_id_combobox.get() # Get current value from combobox
        
        site_id = self.site_name_to_id_map.get(selected_site_display_name)
        if not site_id:
            # Could be that user typed a raw ID. Try to use it.
            # Basic check if it "looks" like an ID (numeric) if it's not in the map
            if selected_site_display_name.isdigit():
                site_id = int(selected_site_display_name)
            else:
                self.clear_site_details_tabs_content()
                if selected_site_display_name != "Enter Site ID or select/search from list" and \
                   selected_site_display_name != "No match found..." and \
                   selected_site_display_name != "No sites found or error.":
                     messagebox.showwarning("Invalid Site", f"'{selected_site_display_name}' is not a recognized site.")
                return

        if self.is_fetching:
            # messagebox.showinfo("Busy", "An operation is already in progress. Site details will not be fetched now.")
            return

        self.current_selected_site_id = site_id # Store for other functions like alerts
        
        self.site_details_tabview.pack(fill="both", expand=True, padx=5, pady=5) # Show tabview
        self.clear_site_details_tabs_content(show_loading=True)

        self.is_fetching = True
        self.fetch_button.configure(state="disabled")
        self.fetch_sites_button.configure(state="disabled")
        self.cancel_button.pack(pady=5)
        self.status_label.configure(text=f"Fetching details for site {site_id}...")
        self.progress_bar.start()

        thread = threading.Thread(target=self._execute_fetch_site_details, args=(site_id,))
        thread.daemon = True
        thread.start()

    def clear_site_details_tabs_content(self, show_loading=False):
        tabs = [self.tab_overview, self.tab_inventory, self.tab_power_flow, self.alerts_treeview_frame] # Alerts treeview frame
        for tab_content_frame in tabs:
            if tab_content_frame: # Check if tab/frame exists
                for widget in tab_content_frame.winfo_children():
                    widget.destroy()
                if show_loading:
                    ctk.CTkLabel(tab_content_frame, text="Loading data...").pack(padx=10, pady=10)
        # For alerts tab, also reset the alerts treeview specifically if it was more complex
        if hasattr(self, 'alerts_tree') and self.alerts_tree:
             for i in self.alerts_tree.get_children(): 
                 self.alerts_tree.delete(i)

    def _execute_fetch_site_details(self, site_id):
        account_api_key = self.account_api_key_entry.get()
        if not account_api_key:
            self.root.after(0, lambda: messagebox.showerror("API Key Missing", "Account API Key is required to fetch site details."))
            self._finalize_site_details_fetch_ui()
            return

        all_details_fetched_successfully = True
        
        # 1. Fetch Overview
        try:
            self.check_if_cancelled()
            self.root.after(0, lambda: self.status_label.configure(text=f"Fetching overview for site {site_id}..."))
            overview_data = self.fetch_api_data(f"https://monitoringapi.solaredge.com/site/{site_id}/overview.json", {"api_key": account_api_key})
            self.root.after(0, self.populate_overview_tab, overview_data.get("overview") if overview_data else None)
        except OperationCancelledError: 
            raise # Propagate cancellation
        except Exception as e:
            all_details_fetched_successfully = False
            print(f"Error fetching overview: {e}")
            self.root.after(0, self.populate_overview_tab, {"error": str(e)})

        # 2. Fetch Inventory
        try:
            self.check_if_cancelled()
            self.root.after(0, lambda: self.status_label.configure(text=f"Fetching inventory for site {site_id}..."))
            inventory_data = self.fetch_api_data(f"https://monitoringapi.solaredge.com/site/{site_id}/inventory.json", {"api_key": account_api_key})
            self.root.after(0, self.populate_inventory_tab, inventory_data.get("Inventory") if inventory_data else None)
        except OperationCancelledError: 
            raise 
        except Exception as e:
            all_details_fetched_successfully = False
            print(f"Error fetching inventory: {e}")
            self.root.after(0, self.populate_inventory_tab, {"error": str(e)})

        # 3. Fetch Current Power Flow
        try:
            self.check_if_cancelled()
            self.root.after(0, lambda: self.status_label.configure(text=f"Fetching power flow for site {site_id}..."))
            power_flow_data = self.fetch_api_data(f"https://monitoringapi.solaredge.com/site/{site_id}/currentPowerFlow.json", {"api_key": account_api_key})
            self.root.after(0, self.populate_power_flow_tab, power_flow_data.get("siteCurrentPowerFlow") if power_flow_data else None)
        except OperationCancelledError: 
            raise 
        except Exception as e:
            all_details_fetched_successfully = False
            print(f"Error fetching power flow: {e}")
            self.root.after(0, self.populate_power_flow_tab, {"error": str(e)})
        
        self.root.after(0, self._finalize_site_details_fetch_ui, all_details_fetched_successfully, site_id)

    def _finalize_site_details_fetch_ui(self, success=True, site_id=None):
        self.is_fetching = False
        self.progress_bar.stop()
        self.fetch_button.configure(state="normal")
        self.fetch_sites_button.configure(state="normal")
        self.cancel_button.pack_forget()
        
        if not self.is_fetching: # If a cancel signal came in very late
            if success:
                self.status_label.configure(text=f"Details loaded for site {site_id}.")
            else:
                self.status_label.configure(text=f"Partial or no details loaded for site {site_id}. Check console for errors.")
        else:
            self.status_label.configure(text="Operation cancelled.")
            
        # If no other operation is pending and status is not specific, set to ready
        current_status = self.status_label.cget("text")
        if not self.is_fetching and not any(s in current_status for s in ["loaded", "Error", "cancelled"]):
            self.status_label.configure(text="Ready.")

    def populate_overview_tab(self, overview):
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
        style.theme_use("default") # Use a theme that allows configuration

        cols = ("Manufacturer", "Model", "Serial Number", "Name/Type") # Added Name/Type
        tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode="browse")
        for col in cols: 
            tree.heading(col, text=col)
        tree.pack(fill="both", expand=True)

        def add_inventory_items(items, item_type_name):
            if items:
                for item in items:
                    tree.insert("", "end", values=(
                        item.get("manufacturer", "N/A"),
                        item.get("model", "N/A"),
                        item.get("serialNumber", item.get("SN", "N/A")), # Some use SN
                        item.get("name", item_type_name) # Use item name if available
                    ))
        
        if "inverters" in inventory: 
            add_inventory_items(inventory["inverters"], "Inverter")
        if "batteries" in inventory: 
            add_inventory_items(inventory["batteries"], "Battery")
        if "meters" in inventory: 
            add_inventory_items(inventory["meters"], "Meter")
        # Add other types if present, e.g., gateways
        if not tree.get_children(): # If no items were added
            tree.insert("", "end", values=("No equipment data found in inventory.", "", "", ""))

    def populate_power_flow_tab(self, power_flow):
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
        
        connections = power_flow.get("connections", [])
        data_points = {} # Store PV, LOAD, GRID, STORAGE data

        for con in connections:
            # This part needs careful parsing based on actual API response structure for connections
            # Assuming `power_flow` directly has keys like PV, LOAD, GRID, STORAGE
            pass # The example structure is usually simpler

        def add_flow_item(label, source_data, status_key=None):
            item_frame = ctk.CTkFrame(frame, fg_color="transparent")
            item_frame.pack(fill="x", pady=1)
            ctk.CTkLabel(item_frame, text=f"{label}:", width=150, anchor="w").pack(side="left", padx=5)
            power_val = source_data.get("currentPower", "N/A") if source_data else "N/A"
            ctk.CTkLabel(item_frame, text=str(power_val), width=100, anchor="w").pack(side="left", padx=5)
            if status_key and source_data and source_data.get(status_key):
                ctk.CTkLabel(item_frame, text=f"({source_data.get(status_key)})", anchor="w").pack(side="left", padx=5)

        add_flow_item("PV Production", power_flow.get("PV"))
        add_flow_item("Consumption (Load)", power_flow.get("LOAD"))
        add_flow_item("Grid", power_flow.get("GRID"), status_key="status") # e.g. status: "Import" / "Export" / "Disconnected"
        add_flow_item("Storage (Battery)", power_flow.get("STORAGE"), status_key="status") # e.g. status: "Charging" / "Discharging" / "Idle"

    def fetch_site_alerts_thread_from_tab(self):
        if not self.current_selected_site_id:
            messagebox.showwarning("No Site Selected", "Please select a site first.")
            return
        if self.is_fetching: # Prevent multiple concurrent fetches
            messagebox.showwarning("Busy", "Another operation is in progress. Please wait.")
            return
        
        self.is_fetching = True
        self.fetch_alerts_button_tab.configure(state="disabled")
        self.cancel_button.pack(pady=5)
        self.status_label.configure(text=f"Fetching alerts for site {self.current_selected_site_id}...")
        self.progress_bar.start()

        start_date = self.alert_start_date_entry.get_date()
        end_date = self.alert_end_date_entry.get_date()
        
        # API requires time component, default to start of day / end of day
        start_time_str = datetime.combine(start_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
        end_time_str = datetime.combine(end_date, datetime.max.time()).strftime("%Y-%m-%d %H:%M:%S")
        
        thread = threading.Thread(target=self._execute_fetch_site_alerts, 
                                  args=(self.current_selected_site_id, start_time_str, end_time_str))
        thread.daemon = True
        thread.start()

    def _execute_fetch_site_alerts(self, site_id, start_time, end_time):
        account_api_key = self.account_api_key_entry.get()
        alerts_data = None
        error_msg = None
        try:
            self.check_if_cancelled()
            params = {"api_key": account_api_key, "startTime": start_time, "endTime": end_time}
            
            # Debug logging for alerts API call
            api_url = f"https://monitoringapi.solaredge.com/site/{site_id}/alerts.json"
            print(f"Debug: Calling alerts API: {api_url}")
            print(f"Debug: Params: startTime={start_time}, endTime={end_time}")
            print(f"Debug: Using API key: {account_api_key[:10]}..." if account_api_key else "Debug: No API key")
            
            alerts_data = self.fetch_api_data(api_url, params)
        except OperationCancelledError: 
            error_msg = "cancelled"
        except Exception as e:
            print(f"Error fetching alerts: {e}")
            error_msg = str(e)
        
        self.root.after(0, self.populate_alerts_tab, alerts_data.get("alerts", {}).get("alert") if alerts_data and "alerts" in alerts_data else None, error_msg)
        self.root.after(0, self._finalize_alerts_fetch_ui, error_msg is None or error_msg=="cancelled", site_id)

    def _finalize_alerts_fetch_ui(self, success, site_id):
        self.is_fetching = False # Critical to reset
        self.progress_bar.stop()
        self.fetch_alerts_button_tab.configure(state="normal")
        # Only hide cancel button if no other main operation is running
        # This needs more sophisticated state management if site detail fetch can run concurrently with alert fetch
        # For now, assume one "is_fetching" flag governs all major background tasks.
        # Check if the main fetch button is also disabled, if not, then this was the only operation.
        if self.fetch_button.cget("state") == "disabled" and self.fetch_sites_button.cget("state") == "disabled":
            pass # A main data export or site list fetch might still be active
        else:
            self.cancel_button.pack_forget()

        if success:
            self.status_label.configure(text=f"Alerts updated for site {site_id}.")
        else:
            self.status_label.configure(text=f"Error fetching alerts for site {site_id}.")

    def populate_alerts_tab(self, alerts_list, error=None):
        # Clear previous content from the specific frame for alerts treeview
        for widget in self.alerts_treeview_frame.winfo_children(): 
            widget.destroy()

        if error and error != "cancelled":
            # Provide more helpful error messages based on the actual error
            if "403" in error:
                if "Date format issues" in error or "Date range too large" in error:
                    error_text = "⚠️ Alerts Request Error\n\nPossible issues:\n• Date range might be too large (try smaller range)\n• Date format issue\n• API rate limiting\n\nTry selecting a shorter date range (1-7 days) and try again."
                else:
                    error_text = "⚠️ Alerts Access Error (403)\n\nThis could be due to:\n• API rate limiting\n• Temporary server issue\n• Date range restrictions\n\nSince you're using a company admin API key, try:\n1. Smaller date range\n2. Wait a few minutes and retry\n3. Check if other endpoints work normally"
                text_color = "orange"
            else:
                error_text = f"Error loading alerts: {error}"
                text_color = "red"
            
            ctk.CTkLabel(self.alerts_treeview_frame, text=error_text, text_color=text_color, wraplength=400, justify="center").pack(padx=10, pady=20)
            return
        if error == "cancelled":
            ctk.CTkLabel(self.alerts_treeview_frame, text="Alert fetching cancelled.", text_color="orange").pack(padx=10, pady=10)
            return
        if not alerts_list:
            ctk.CTkLabel(self.alerts_treeview_frame, text="No alerts found for the selected period or data not available.").pack(padx=10, pady=10)
            return

        cols = ("Timestamp", "Severity", "Code", "Description")
        self.alerts_tree = ttk.Treeview(self.alerts_treeview_frame, columns=cols, show='headings', selectmode="browse")
        for col_name in cols: 
            self.alerts_tree.heading(col_name, text=col_name)
            self.alerts_tree.column(col_name, width=150 if col_name != "Description" else 300, anchor="w")
        self.alerts_tree.pack(fill="both", expand=True)

        for alert in alerts_list:
            # Date can be in "yyyy-MM-dd HH:mm:ss" or just "yyyy-MM-dd"
            # Format it nicely if it's a full timestamp
            timestamp_str = alert.get("date", "N/A")
            try:
                dt_obj = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                timestamp_str = dt_obj.strftime("%Y-%m-%d %H:%M") # More readable
            except ValueError:
                pass # Keep original if not in expected format
            
            self.alerts_tree.insert("", "end", values=(
                timestamp_str,
                alert.get("severity", "N/A"),
                alert.get("id", "N/A"), # 'id' is often the alert code
                alert.get("description", alert.get("message", "N/A"))
            ))

    def create_data_type_sections(self):
        data_type_label = ctk.CTkLabel(self.data_type_choice_frame, text="Data Type (for Export)", font=ctk.CTkFont(size=16, weight="bold"))
        data_type_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        self.data_type_var = tk.StringVar(value="production")
        self.radio_buttons_frame = ctk.CTkFrame(self.data_type_choice_frame, fg_color="transparent")
        self.radio_buttons_frame.pack(fill="x", padx=10, pady=0)
        
        ctk.CTkRadioButton(self.radio_buttons_frame, text="Production Details (Energy)", variable=self.data_type_var, value="production", command=self.update_ui_for_data_type).grid(row=0, column=0, sticky="w", padx=10, pady=2)
        ctk.CTkRadioButton(self.radio_buttons_frame, text="Voltage Values (Equipment)", variable=self.data_type_var, value="voltage", command=self.update_ui_for_data_type).grid(row=0, column=1, sticky="w", padx=10, pady=2)
        
        # Inverter frame
        self.inverter_frame = ctk.CTkFrame(self.data_specific_inputs_frame)
        ctk.CTkLabel(self.inverter_frame, text="Inverter Serial Number:").grid(row=0, column=0, sticky="w", padx=10, pady=2)
        self.inverter_entry = ctk.CTkEntry(self.inverter_frame, width=200)
        self.inverter_entry.grid(row=0, column=1, sticky="we", padx=10, pady=2)
        self.inverter_frame.grid_columnconfigure(1, weight=1)
        
        # Meters frame
        self.meters_frame = ctk.CTkFrame(self.data_specific_inputs_frame)
        ctk.CTkLabel(self.meters_frame, text="Select Meters:").grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=2)
        
        self.production_var = tk.BooleanVar(value=True)
        self.consumption_var = tk.BooleanVar(value=False)
        self.self_consumption_var = tk.BooleanVar(value=False)
        self.feed_in_var = tk.BooleanVar(value=False)
        self.purchased_var = tk.BooleanVar(value=False)
        
        ctk.CTkCheckBox(self.meters_frame, text="Production", variable=self.production_var).grid(row=1, column=0, sticky="w", padx=10, pady=1)
        ctk.CTkCheckBox(self.meters_frame, text="Consumption", variable=self.consumption_var).grid(row=1, column=1, sticky="w", padx=10, pady=1)
        ctk.CTkCheckBox(self.meters_frame, text="Self Consumption", variable=self.self_consumption_var).grid(row=2, column=0, sticky="w", padx=10, pady=1)
        ctk.CTkCheckBox(self.meters_frame, text="Feed In (Export)", variable=self.feed_in_var).grid(row=2, column=1, sticky="w", padx=10, pady=1)
        ctk.CTkCheckBox(self.meters_frame, text="Purchased (Import)", variable=self.purchased_var).grid(row=3, column=0, sticky="w", padx=10, pady=1)

    def update_ui_for_data_type(self):
        data_type = self.data_type_var.get()
        for w in self.data_specific_inputs_frame.winfo_children():
            w.pack_forget()
            
        if not hasattr(self, 'start_date_calendar'): 
            self.root.after(100, self.update_ui_for_data_type)
            return
            
        current_date = datetime.now()
        if data_type == "voltage": 
            self.inverter_frame.pack(in_=self.data_specific_inputs_frame, fill="x", padx=0, pady=2)
            self.end_date_calendar.set_date(current_date)
            self.start_date_calendar.set_date(current_date - timedelta(days=6))
        else: 
            self.meters_frame.pack(in_=self.data_specific_inputs_frame, fill="x", padx=0, pady=2)
            self.end_date_calendar.set_date(current_date)
            self.start_date_calendar.set_date(current_date - timedelta(days=29))

    def create_date_range_section(self):
        ctk.CTkLabel(self.date_range_frame, text="Date Range (for Data Export)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(5,2))
        
        ctk.CTkLabel(self.date_range_frame, text="Start Date:").grid(row=1, column=0, sticky="w", padx=10, pady=2)
        sdf = tk.Frame(self.date_range_frame)
        sdf.grid(row=1, column=1, sticky="w", padx=10, pady=2)
        
        today = datetime.now()
        isd = today - timedelta(days=29)
        self.start_date_calendar = DateEntry(sdf, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', year=isd.year, month=isd.month, day=isd.day, maxdate=today)
        self.start_date_calendar.pack(fill="both", expand=True)
        
        ctk.CTkLabel(self.date_range_frame, text="Hour:").grid(row=1, column=2, sticky="w", padx=(20,5), pady=2)
        self.start_hour_var = tk.StringVar(value="00")
        ctk.CTkOptionMenu(self.date_range_frame, values=[f"{i:02d}" for i in range(24)], variable=self.start_hour_var, width=60).grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        ctk.CTkLabel(self.date_range_frame, text="End Date:").grid(row=2, column=0, sticky="w", padx=10, pady=2)
        edf = tk.Frame(self.date_range_frame)
        edf.grid(row=2, column=1, sticky="w", padx=10, pady=2)
        self.end_date_calendar = DateEntry(edf, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', year=today.year, month=today.month, day=today.day, maxdate=today)
        self.end_date_calendar.pack(fill="both", expand=True)
        
        ctk.CTkLabel(self.date_range_frame, text="Hour:").grid(row=2, column=2, sticky="w", padx=(20,5), pady=2)
        self.end_hour_var = tk.StringVar(value="23")
        ctk.CTkOptionMenu(self.date_range_frame, values=[f"{i:02d}" for i in range(24)], variable=self.end_hour_var, width=60).grid(row=2, column=3, sticky="w", padx=5, pady=2)
        
        ctk.CTkLabel(self.date_range_frame, text="Time Unit (Prod. Data):").grid(row=3, column=0, sticky="w", padx=10, pady=2)
        self.time_unit_var = tk.StringVar(value="HOUR")
        ctk.CTkOptionMenu(self.date_range_frame, values=["HOUR","DAY","WEEK","MONTH"], variable=self.time_unit_var).grid(row=3, column=1, sticky="we", padx=10, pady=2)

    def create_options_section(self):
        ctk.CTkLabel(self.options_frame, text="Output Options (for Data Export)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0,column=0,columnspan=3,sticky="w",padx=10,pady=(5,2))
        
        ctk.CTkLabel(self.options_frame, text="File Format:").grid(row=1,column=0,sticky="w",padx=10,pady=2)
        self.file_format_var=tk.StringVar(value="csv")
        ffrf=ctk.CTkFrame(self.options_frame,fg_color="transparent")
        ffrf.grid(row=1,column=1,columnspan=2,sticky="w",pady=0)
        ctk.CTkRadioButton(ffrf,text="CSV",variable=self.file_format_var,value="csv").pack(side="left",padx=10,pady=0)
        ctk.CTkRadioButton(ffrf,text="Excel",variable=self.file_format_var,value="excel").pack(side="left",padx=10,pady=0)
        
        ctk.CTkLabel(self.options_frame, text="Output Folder:").grid(row=2,column=0,sticky="w",padx=10,pady=2)
        self.output_path_var=tk.StringVar(value=os.path.expanduser("~"))
        ctk.CTkEntry(self.options_frame,textvariable=self.output_path_var,width=300).grid(row=2,column=1,sticky="we",padx=10,pady=2)
        ctk.CTkButton(self.options_frame,text="Browse...",command=self.browse_output_folder,width=100).grid(row=2,column=2,sticky="w",padx=10,pady=2)
        self.options_frame.grid_columnconfigure(1,weight=1)

    def browse_output_folder(self):
        fp = filedialog.askdirectory(initialdir=self.output_path_var.get())
        if fp:
            self.output_path_var.set(fp)

    def create_action_section(self):
        self.fetch_button = ctk.CTkButton(self.action_frame,text="Fetch and Save Export Data",command=self.start_fetch_thread,font=ctk.CTkFont(size=14,weight="bold"),height=40)
        self.fetch_button.pack(pady=10)
        self.cancel_button = ctk.CTkButton(self.action_frame,text="Cancel Current Operation",command=self.cancel_fetch,font=ctk.CTkFont(size=14),height=30,fg_color="#D32F2F",hover_color="#C62828")

    def start_fetch_thread(self): 
        if self.is_fetching: 
            messagebox.showwarning("In Progress","Another operation in progress.")
            return
        if not self.validate_inputs(): 
            return
        
        self.is_fetching=True
        self.fetch_button.configure(state="disabled")
        self.fetch_sites_button.configure(state="disabled")
        self.cancel_button.pack(pady=5)
        
        dtft=threading.Thread(target=self.fetch_and_save_data)
        dtft.daemon=True
        dtft.start()
        
    def cancel_fetch(self):
        if self.is_fetching: 
            self.is_fetching=False
            self.status_label.configure(text="Cancelling...")
            self.root.update()
        else: 
            self.status_label.configure(text="No operation running to cancel.")
            
    def check_if_cancelled(self):
        if not self.is_fetching: 
            raise OperationCancelledError("Cancelled by user")

    def create_status_section(self):
        self.status_label=ctk.CTkLabel(self.status_frame,text="Ready.",font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=5)
        self.progress_bar=ctk.CTkProgressBar(self.status_frame,width=400)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)

    def fetch_and_save_data(self):
        account_api_key=self.account_api_key_entry.get()
        sel_site_disp=self.site_id_combobox.get()
        site_id=self.site_name_to_id_map.get(sel_site_disp,sel_site_disp)
        data_type=self.data_type_var.get()
        sdo=self.start_date_calendar.get_date()
        edo=self.end_date_calendar.get_date()
        sh=self.start_hour_var.get()
        eh=self.end_hour_var.get()
        
        sdt=datetime.combine(sdo,datetime.strptime(f"{sh}:00:00","%H:%M:%S").time())
        edt=datetime.combine(edo,datetime.strptime(f"{eh}:59:59","%H:%M:%S").time())
        time_unit=self.time_unit_var.get() if data_type=="production" else None
        
        # Define optimal chunk sizes based on data type and time unit
        if data_type=="voltage":
            max_chunk_days = 7
        elif data_type=="production":
            if time_unit == "HOUR":
                max_chunk_days = 28  # Reduced to be safe with SolarEdge's "one month" limit
            elif time_unit == "DAY":
                max_chunk_days = 365  # Can handle more days for daily data
            elif time_unit in ["WEEK", "MONTH"]:
                max_chunk_days = 1095  # ~3 years for weekly/monthly data
            else:
                max_chunk_days = 28  # Default fallback
        else:
            max_chunk_days = 28
            
        self.status_label.configure(text="Calculating export chunks...")
        self.progress_bar.set(0)
        self.progress_bar.start()
        self.root.update()
        
        # Smart chunking algorithm that works with any date range
        date_chunks = self._calculate_smart_chunks(sdt, edt, max_chunk_days)
        
        self.progress_bar.stop()
        num_chunks=len(date_chunks)
        if num_chunks==0:
            messagebox.showinfo("Info","No export intervals calculated.")
            self._restore_ui_after_fetch()
            return
            
        # Debug: Show chunking info
        print(f"Debug: Date range: {sdt} to {edt}")
        print(f"Debug: Max chunk days: {max_chunk_days}")
        print(f"Debug: Calculated {num_chunks} chunks:")
        for i, (start, end) in enumerate(date_chunks):
            days_in_chunk = (end - start).days + 1
            print(f"  Chunk {i+1}: {start} to {end} ({days_in_chunk} days)")
            
        self.status_label.configure(text=f"Preparing {num_chunks} export requests...")
        self.progress_bar.set(0.1)
        self.root.update()
        
        cdf=None
        adws=False
        try:
            for ci,(cs,ce) in enumerate(date_chunks):
                self.check_if_cancelled()
                cpb=0.1+(ci/num_chunks)*0.8
                sts=cs.strftime("%Y-%m-%d %H:%M:%S")
                ets=ce.strftime("%Y-%m-%d %H:%M:%S")
                
                self.status_label.configure(text=f"Fetching export chunk {ci+1}/{num_chunks}: {cs.strftime('%m/%d %H:%M')}-{ce.strftime('%m/%d %H:%M')}")
                self.progress_bar.set(cpb)
                self.root.update()
                
                params={"api_key":account_api_key,"startTime":sts,"endTime":ets}
                ad=None
                df=None
                
                if data_type=="voltage":
                    isn=self.inverter_entry.get()
                    api_url=f"https://monitoringapi.solaredge.com/equipment/{site_id}/{isn}/data.json"
                    ad=self.fetch_api_data(api_url,params)
                    if ad and "data" in ad and "telemetries" in ad["data"]:
                        tel=ad["data"]["telemetries"]
                        df=self.process_voltage_data(tel)
                    if df is not None and df.empty and not tel and not adws:
                        self.status_label.configure(text=f"Chunk {ci+1} (V): No telemetries.")
                        adws=True
                        if ci==0:
                            messagebox.showwarning("Data Warn","Chunk (V): No telemetries.")
                    elif ad and not (df is not None and not df.empty):
                        self.status_label.configure(text=f"Chunk {ci+1} (V): Bad API resp.")
                        adws=True
                        if ci==0:
                            messagebox.showwarning("API Warn","Chunk (V): Bad structure.")
                else:
                    msel=[m for v,m in [(self.production_var.get(),"PRODUCTION"),(self.consumption_var.get(),"CONSUMPTION"),(self.self_consumption_var.get(),"SELFCONSUMPTION"),(self.feed_in_var.get(),"FEEDIN"),(self.purchased_var.get(),"PURCHASED")] if v]
                    params.update({"meters":",".join(msel),"timeUnit":time_unit})
                    api_url=f"https://monitoringapi.solaredge.com/site/{site_id}/energyDetails.json"
                    ad=self.fetch_api_data(api_url,params)
                    if ad and "energyDetails" in ad and "meters" in ad["energyDetails"]:
                        df=self.process_production_data(ad["energyDetails"]["meters"],ad["energyDetails"]["timeUnit"])
                    if df is not None and df.empty and not adws and (not ad["energyDetails"]["meters"] or all(not m.get("values") for m in ad["energyDetails"]["meters"])):
                        self.status_label.configure(text=f"Chunk {ci+1}(P): No meter vals.")
                        adws=True
                        if ci==0:
                            messagebox.showwarning("Data Warn","Chunk(P):No meter vals.")
                    elif ad and not (df is not None and not df.empty):
                        self.status_label.configure(text=f"Chunk {ci+1}(P):Bad API resp.")
                        adws=True
                        if ci==0:
                            messagebox.showwarning("API Warn","Chunk(P):Bad struct.")
                            
                if (df is None or df.empty) and not adws and ad:
                    self.status_label.configure(text=f"Chunk {ci+1} processed,0 pts.")
                    
                self.progress_bar.set(cpb+(0.8/num_chunks)*0.5)
                self.root.update()
                
                if df is not None and not df.empty:
                    adws=False
                    cdf=pd.concat([cdf,df],ignore_index=True) if cdf is not None else df
                    if 'date' in cdf.columns:
                        cdf=cdf.drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
                        
            self.check_if_cancelled()
            if cdf is None or cdf.empty:
                messagebox.showwarning("No Data","No data for export.")
                self._restore_ui_after_fetch()
                return
                
            self.status_label.configure(text="Saving export file...")
            self.progress_bar.set(0.9)
            self.root.update()
            
            op,ff=self.output_path_var.get(),self.file_format_var.get()
            ts=datetime.now().strftime("%Y%m%d_%H%M%S")
            sis=str(site_id).replace("/","-").replace("\\","-")
            fnb=f"SolarEdge_{data_type}_{sis}_{sdo.strftime('%Y%m%d')}_{edo.strftime('%Y%m%d')}_{ts}"
            
            # Fix file extension issue
            if ff == "excel":
                file_extension = "xlsx"
            else:
                file_extension = ff
            
            fp=os.path.join(op,f"{fnb}.{file_extension}")
            
            if ff=="csv":
                cdf.to_csv(fp,index=False)
            else:
                # Handle Excel export with proper error handling
                try:
                    cdf.to_excel(fp,index=False,engine='openpyxl')
                except ImportError as e:
                    if "openpyxl" in str(e) or "xlsxwriter" in str(e) or "engine" in str(e):
                        # Excel engine not available, fall back to CSV
                        csv_fp = fp.replace('.xlsx', '.csv')
                        cdf.to_csv(csv_fp, index=False)
                        messagebox.showwarning("Excel Export Issue", 
                                             f"Excel export requires 'openpyxl' or 'xlsxwriter' package.\n\n"
                                             f"Saved as CSV instead: {os.path.basename(csv_fp)}\n\n"
                                             f"To fix this, install: pip install openpyxl")
                        fp = csv_fp  # Update the file path for success message
                    else:
                        raise
                
            tr=len(cdf)
            drs=f"{sdt.strftime('%Y-%m-%d')} to {edt.strftime('%Y-%m-%d')}"
            
            self.status_label.configure(text=f"Saved {tr} export records for {drs} to {os.path.basename(fp)}")
            self.progress_bar.set(1.0)
            messagebox.showinfo("Success",f"Export data saved:\n{fp}\n\n{tr} data points.")
            
        except OperationCancelledError:
            self.status_label.configure(text="Export cancelled.")
            self.progress_bar.set(0)
        except requests.exceptions.Timeout as e:
            messagebox.showerror("API Timeout",f"API Timeout: {e}.")
            self.status_label.configure(text="Error: API Timeout.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("API Error",f"API Error: {e}")
            self.status_label.configure(text=f"API Error: {str(e)[:100]}")
        except Exception as e:
            messagebox.showerror("Proc Error",f"Error: {e}")
            self.status_label.configure(text=f"Error: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
        finally:
            self._restore_ui_after_fetch()

    def _restore_ui_after_fetch(self):
        self.is_fetching=False
        self.fetch_button.configure(state="normal")
        self.fetch_sites_button.configure(state="normal")
        self.cancel_button.pack_forget()
        
        cs=self.status_label.cget("text")
        if not any(s in cs for s in ["Saved","Error","Cancelled","No data","No sites","Successfully fetched","loaded"]):
            self.status_label.configure(text="Ready.")
        if self.progress_bar.get()<1.0 and "Error" not in cs and not any(s in cs for s in ["Saved","Cancelled","Successfully fetched","loaded"]):
            self.progress_bar.set(0)

    def fetch_api_data(self, url, params):
        mr=3
        brd=5
        for att in range(mr):
            self.check_if_cancelled()
            try:
                print(f"Debug: Making API request to {url} (attempt {att+1}/{mr})")
                res=requests.get(url,params=params,timeout=45)
                print(f"Debug: Response status: {res.status_code}")
                print(f"Debug: Response headers: {dict(res.headers)}")
                
                if res.status_code==200:
                    try:
                        json_data = res.json()
                        print(f"Debug: Successful JSON response received")
                        return json_data
                    except json.JSONDecodeError as je:
                        print(f"Debug: JSON decode error: {je}")
                        print(f"Debug: Response text: {res.text[:500]}")
                        raise Exception(f"API non-JSON (200, {url}): {res.text[:200]} Err: {je}")
                        
                ep=f"API Err (Status {res.status_code}, {url})"
                ed=""
                print(f"Debug: API error response, status {res.status_code}")
                print(f"Debug: Response content type: {res.headers.get('content-type', 'unknown')}")
                print(f"Debug: Response text (first 500 chars): {res.text[:500]}")
                
                try:
                    jr=res.json()
                    # Handle different error response formats more robustly
                    if isinstance(jr, dict):
                        # Try different paths for error messages
                        ed = jr.get("message", "")
                        if not ed and "String" in jr:
                            string_obj = jr["String"]
                            if isinstance(string_obj, dict):
                                ed = string_obj.get("message", "")
                            elif isinstance(string_obj, str):
                                ed = string_obj
                        if not ed and "error" in jr:
                            error_obj = jr["error"]
                            if isinstance(error_obj, dict):
                                ed = error_obj.get("message", "")
                            elif isinstance(error_obj, str):
                                ed = error_obj
                        if not ed:
                            ed = str(jr)
                    elif isinstance(jr, str):
                        ed = jr
                    else:
                        ed = str(jr)
                except json.JSONDecodeError:
                    # API returned HTML or non-JSON
                    ed = f"Non-JSON response: {res.text[:200]}..."
                except Exception as e:
                    ed = f"Error parsing response: {str(e)} - Raw response: {res.text[:200]}..."
                    
                fem=f"{ep}: {ed}"
                
                # Add specific debugging for 400 errors
                if res.status_code == 400:
                    print(f"Debug: 400 Bad Request details:")
                    print(f"Debug: URL: {url}")
                    print(f"Debug: Params: {params}")
                    print(f"Debug: Response content: {res.text[:1000]}")
                
                if res.status_code==429:
                    ra=int(res.headers.get('Retry-After',brd*(att+1)))
                    self.status_label.configure(text=f"Rate limit. Retry in {ra}s ({att+1})")
                    self.root.update()
                    for _ in range(ra):
                        self.check_if_cancelled()
                        time.sleep(1)
                    continue
                elif res.status_code in [400,401,403,404]:
                    # Add specific handling for 403 on alerts endpoint
                    if res.status_code == 403 and "alerts" in url.lower():
                        # Check if this might be a date format issue or other parameter problem
                        if "startTime" in str(params) and "endTime" in str(params):
                            raise Exception(f"403 error on alerts endpoint. This might be due to:\n1. Date format issues\n2. Date range too large\n3. Invalid site ID\n4. API rate limiting\n\nTry a smaller date range or check the date format.")
                        else:
                            raise Exception(f"Access denied to alerts endpoint. Status: {res.status_code}")
                    else:
                        raise Exception(fem)
                else:
                    if att<mr-1:
                        self.status_label.configure(text=f"{fem}. Retry in {brd*(att+1)}s")
                        self.root.update()
                        for _ in range(brd*(att+1)):
                            self.check_if_cancelled()
                            time.sleep(1)
                        continue
                    else:
                        raise Exception(fem)
            except requests.exceptions.Timeout:
                print(f"Debug: Timeout on attempt {att+1}")
                if att<mr-1:
                    self.status_label.configure(text=f"Timeout {url}.Retry")
                    self.root.update()
                    for _ in range(brd*(att+1)):
                        self.check_if_cancelled()
                        time.sleep(1)
                    continue
                else:
                    raise
            except requests.exceptions.RequestException as e:
                print(f"Debug: Request exception on attempt {att+1}: {e}")
                if att<mr-1:
                    self.status_label.configure(text=f"Conn err {url}.Retry")
                    self.root.update()
                    for _ in range(brd*(att+1)):
                        self.check_if_cancelled()
                        time.sleep(1)
                    continue
                else:
                    raise Exception(f"Failed {url} after {mr} attempts: {e}")
        raise Exception(f"Max retries for {url}.")

    def process_voltage_data(self, telemetries):
        if not telemetries:
            return pd.DataFrame()
        df=pd.DataFrame(telemetries)
        
        if 'date' not in df.columns:
            return df
        df['date']=pd.to_datetime(df['date'],errors='coerce')
        df=df.dropna(subset=['date'])
        df=df.fillna(0).sort_values('date').reset_index(drop=True)
        if 'date' in df.columns:
            df=df[['date']+[c for c in df.columns if c!='date']]
        return df

    def process_production_data(self, meters_data, time_unit):
        if not meters_data:
            return pd.DataFrame()
        amdfs=[]
        for me in meters_data:
            mt,v=me.get('type'),me.get('values')
            if not mt or not v:
                continue
            mdf=pd.DataFrame(v)
            if 'date' not in mdf.columns or 'value' not in mdf.columns:
                continue
            mdf['date']=pd.to_datetime(mdf['date'],errors='coerce')
            mdf=mdf.dropna(subset=['date'])
            mdf.rename(columns={'value':mt},inplace=True)
            mdf=mdf.fillna(0)
            amdfs.append(mdf[['date',mt]])
        if not amdfs:
            return pd.DataFrame()
        rdf=amdfs[0]
        for i in range(1,len(amdfs)):
            if 'date' not in amdfs[i].columns:
                continue
            rdf=pd.merge(rdf,amdfs[i],on='date',how='outer')
        return rdf.fillna(0).sort_values('date').reset_index(drop=True)

    def validate_inputs(self):
        if not self.account_api_key_entry.get():
            messagebox.showerror("Input Error","Account API Key required.")
            return False
        ssd=self.site_id_combobox.get()
        situ=self.site_name_to_id_map.get(ssd,ssd)
        if not situ or situ=="Enter Site ID or select/search from list" or situ=="No match found..." or situ=="No sites found or error.":
            messagebox.showerror("Input Error","Site ID required.")
            return False
        try:
            if ssd not in self.site_name_to_id_map:
                int(situ)
        except ValueError:
            messagebox.showerror("Input Error",f"Site ID '{situ}' not valid if manual.")
            return False
        sd,ed=self.start_date_calendar.get_date(),self.end_date_calendar.get_date()
        sdt=datetime.combine(sd,datetime.strptime(self.start_hour_var.get()+":00:00","%H:%M:%S").time())
        edt=datetime.combine(ed,datetime.strptime(self.end_hour_var.get()+":59:59","%H:%M:%S").time())
        if sdt>edt:
            messagebox.showerror("Input Error","Start date/time cannot be after end.")
            return False
        dd,dt=(ed-sd).days,self.data_type_var.get()
        if dt=="voltage":
            if not self.inverter_entry.get():
                messagebox.showerror("Input Error","Inverter SN for voltage data.")
                return False
            if dd>30 and not messagebox.askokcancel("Warn: Long Range (V)",f"Fetch voltage for {dd+1} days needs ~{(dd+6)//7} API calls. Continue?"):
                return False
        else:
            if not any(v.get() for v in [self.production_var,self.consumption_var,self.self_consumption_var,self.feed_in_var,self.purchased_var]):
                messagebox.showerror("Input Error","Select meter type for production.")
                return False
            tu=self.time_unit_var.get()
            estimated_chunks = self._estimate_chunks_needed(sd, ed, dt, tu)
            if estimated_chunks > 20 and not messagebox.askokcancel("Warn: Many API Calls",f"This date range will require approximately {estimated_chunks} API calls. Continue?"):
                return False
        if not os.path.isdir(self.output_path_var.get()):
            messagebox.showerror("Input Error","Output folder invalid.")
            return False
        return True

    def _calculate_smart_chunks(self, start_dt, end_dt, max_chunk_days):
        """
        Smart chunking algorithm that works with any date range.
        Breaks the date range into optimal chunks while respecting API limits.
        """
        chunks = []
        current_start = start_dt
        
        print(f"Debug: Starting chunking - Start: {start_dt}, End: {end_dt}, Max chunk days: {max_chunk_days}")
        
        while current_start <= end_dt:
            self.check_if_cancelled()
            
            # Calculate the ideal end time for this chunk
            ideal_end = current_start + timedelta(days=max_chunk_days - 1)  # -1 because we include the start day
            
            print(f"Debug: Current start: {current_start}, Ideal end: {ideal_end}")
            
            # Ensure we don't go past the actual end time
            chunk_end = min(ideal_end, end_dt)
            
            # For intermediate chunks, end at 23:59:59 of the last day
            # For the final chunk, use the exact end time specified
            if chunk_end < end_dt:
                # This is not the final chunk, so end at end of day
                chunk_end = chunk_end.replace(hour=23, minute=59, second=59)
            
            chunks.append((current_start, chunk_end))
            print(f"Debug: Added chunk: {current_start} to {chunk_end}")
            
            # If this was the final chunk, we're done
            if chunk_end >= end_dt:
                break
                
            # Next chunk starts at the beginning of the next day
            current_start = (chunk_end + timedelta(seconds=1)).replace(hour=0, minute=0, second=0)
            print(f"Debug: Next chunk will start at: {current_start}")
        
        print(f"Debug: Chunking complete. Created {len(chunks)} chunks.")
        return chunks

    def _estimate_chunks_needed(self, start_date, end_date, data_type, time_unit=None):
        """
        Estimate the number of API calls needed for a given date range.
        """
        total_days = (end_date - start_date).days + 1
        
        if data_type == "voltage":
            return max(1, (total_days + 6) // 7)  # 7 days per chunk for voltage
        elif data_type == "production":
            if time_unit == "HOUR":
                return max(1, (total_days + 29) // 30)  # 30 days per chunk for hourly
            elif time_unit == "DAY":
                return max(1, (total_days + 364) // 365)  # 365 days per chunk for daily
            elif time_unit in ["WEEK", "MONTH"]:
                return max(1, (total_days + 1094) // 1095)  # ~3 years per chunk
            else:
                return max(1, (total_days + 29) // 30)  # Default to 30 days
        else:
            return max(1, (total_days + 29) // 30)  # Default fallback


if __name__ == "__main__":
    try: 
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1) 
    except Exception: 
        pass 
    root = ctk.CTk()
    app = SolarEdgeAPIApp(root)
    root.mainloop()
