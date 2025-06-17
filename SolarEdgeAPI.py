import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import requests # Keep for now, might be fully removed if client handles all
import json # Keep for now
import pandas as pd
import os
import time
import threading
# import openpyxl # No longer directly used in this file

# Assuming app_ui.py is in a subdirectory 'ui'
from ui.app_ui import AppUI
from api.solaredge_client import SolarEdgeClient
from utils import data_processor
from utils import file_exporter
from utils import helpers
from utils.helpers import OperationCancelledError # Centralized OperationCancelledError


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
        
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.account_api_key_entry = None
        self.fetch_sites_button = None
        self.fetch_button = None
        self.cancel_button = None

        self.ui = AppUI(self.root, self)

        self.status_frame = ctk.CTkFrame(self.main_container)
        self.status_frame.pack(fill="x", side="bottom", padx=5, pady=5)
        self.create_status_section()

        self.site_name_to_id_map = {} 
        self.is_fetching = False 
        self.current_selected_site_id = None

        self.api_client = SolarEdgeClient(
            check_if_cancelled_callback=self.check_if_cancelled,
            status_update_callback=self.update_status_label_for_client
        )

    def update_status_label_for_client(self, message):
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.configure(text=message)
            self.root.update_idletasks()

    def fetch_sites_thread(self):
        account_key = self.account_api_key_entry.get()
        if not account_key: 
            messagebox.showerror("Missing API Key", "Please enter the Account API Key.")
            return
        if self.is_fetching: 
            messagebox.showwarning("In Progress", "Another operation is currently in progress.")
            return
        
        self.is_fetching = True 
        if hasattr(self, 'fetch_sites_button'): self.fetch_sites_button.configure(state="disabled")
        if hasattr(self, 'fetch_button'): self.fetch_button.configure(state="disabled")
        if hasattr(self, 'cancel_button'): self.cancel_button.pack(pady=5)
        if hasattr(self, 'status_label'): self.status_label.configure(text="Fetching site list...")
        if hasattr(self, 'progress_bar'):
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
        
        try:
            while True:
                data = self.api_client.get_sites_list(
                    api_key=account_api_key,
                    start_index=start_index,
                    size=max_results_per_call
                )
                if data and "sites" in data and "site" in data["sites"]:
                    current_batch = data["sites"]["site"]
                    all_sites.extend(current_batch)
                    if expected_total_sites == -1 :
                        expected_total_sites = data["sites"].get("count", 0)
                    total_sites_fetched += len(current_batch)
                    if expected_total_sites > 0:
                        if hasattr(self, 'progress_bar'): self.progress_bar.set(min(total_sites_fetched / expected_total_sites, 0.95))
                    else: 
                        if hasattr(self, 'progress_bar'): self.progress_bar.set(0.5)
                    if hasattr(self, 'status_label'): self.status_label.configure(text=f"Fetched {total_sites_fetched}/{expected_total_sites if expected_total_sites >0 else 'many'} sites...")
                    self.root.update()
                    if total_sites_fetched >= expected_total_sites or not current_batch or len(current_batch) < max_results_per_call:
                        break
                    start_index += len(current_batch)
                else: 
                    messagebox.showwarning("Site List Format", "API response for site list not in expected format (or no sites found).")
                    break
            
            self.site_name_to_id_map.clear()
            if all_sites:
                temp_display_list = [f"{site.get('name', 'N/A')} ({site.get('id', 'N/A')})" for site in all_sites]
                for site_info, display_name in zip(all_sites, temp_display_list): 
                    self.site_name_to_id_map[display_name] = site_info.get('id')
                self.ui.full_site_display_list = sorted(temp_display_list)
                self.ui.site_id_combobox.configure(values=self.ui.full_site_display_list)
                if self.ui.full_site_display_list:
                    self.ui.site_id_combobox.set(self.ui.full_site_display_list[0])
                    self.ui.on_site_selected(self.ui.full_site_display_list[0])
                if hasattr(self, 'status_label'): self.status_label.configure(text=f"Successfully fetched {len(self.ui.full_site_display_list)} sites.")
            else:
                self.ui.full_site_display_list = []
                self.ui.site_id_combobox.set("No sites found or error.")
                self.ui.site_id_combobox.configure(values=[])
                if expected_total_sites != -1 and hasattr(self, 'status_label'):
                    self.status_label.configure(text="No sites found for the API Key.")
                    
        except OperationCancelledError: 
            if hasattr(self, 'status_label'): self.status_label.configure(text="Site fetching cancelled.")
        except requests.exceptions.RequestException as e: 
            messagebox.showerror("Connection Error", f"Could not connect for site list: {e}")
            if hasattr(self, 'status_label'): self.status_label.configure(text="Error fetching sites: Connection failed.")
        except Exception as e: 
            messagebox.showerror("Error", f"Error fetching sites: {e}")
            if hasattr(self, 'status_label'): self.status_label.configure(text=f"Error fetching sites: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
        finally:
            if hasattr(self, 'progress_bar'): self.progress_bar.stop(); self.progress_bar.set(0)
            self.is_fetching = False 
            if hasattr(self, 'fetch_sites_button'): self.fetch_sites_button.configure(state="normal")
            if hasattr(self, 'fetch_button'): self.fetch_button.configure(state="normal")
            if hasattr(self, 'cancel_button'): self.cancel_button.pack_forget()
            if hasattr(self, 'status_label'):
                current_status = self.status_label.cget("text")
                if not any(s in current_status for s in ["Successfully fetched", "No sites found", "Error fetching sites", "cancelled"]):
                    self.status_label.configure(text="Ready.")

    def handle_site_selection_data(self, site_id):
        self.is_fetching = True
        if hasattr(self, 'fetch_button'): self.fetch_button.configure(state="disabled")
        if hasattr(self, 'fetch_sites_button'): self.fetch_sites_button.configure(state="disabled")
        if hasattr(self, 'cancel_button'): self.cancel_button.pack(pady=5)
        if hasattr(self, 'status_label'): self.status_label.configure(text=f"Fetching details for site {site_id}...")
        if hasattr(self, 'progress_bar'): self.progress_bar.start()
        thread = threading.Thread(target=self._execute_fetch_site_details, args=(site_id,))
        thread.daemon = True
        thread.start()

    def _execute_fetch_site_details(self, site_id):
        account_api_key = self.account_api_key_entry.get()
        if not account_api_key:
            self.root.after(0, lambda: messagebox.showerror("API Key Missing", "Account API Key is required to fetch site details."))
            self._finalize_site_details_fetch_ui()
            return
        all_details_fetched_successfully = True
        try:
            if hasattr(self, 'status_label'): self.root.after(0, lambda: self.status_label.configure(text=f"Fetching overview for site {site_id}..."))
            overview_data = self.api_client.get_site_overview(api_key=account_api_key, site_id=site_id)
            if hasattr(self, 'ui'): self.root.after(0, self.ui.populate_overview_tab, overview_data.get("overview") if overview_data else None)
        except OperationCancelledError: raise
        except Exception as e:
            all_details_fetched_successfully = False; print(f"Error fetching overview: {e}")
            if hasattr(self, 'ui'): self.root.after(0, self.ui.populate_overview_tab, {"error": str(e)})
        try:
            if hasattr(self, 'status_label'): self.root.after(0, lambda: self.status_label.configure(text=f"Fetching inventory for site {site_id}..."))
            inventory_data = self.api_client.get_site_inventory(api_key=account_api_key, site_id=site_id)
            if hasattr(self, 'ui'): self.root.after(0, self.ui.populate_inventory_tab, inventory_data.get("Inventory") if inventory_data else None)
        except OperationCancelledError: raise
        except Exception as e:
            all_details_fetched_successfully = False; print(f"Error fetching inventory: {e}")
            if hasattr(self, 'ui'): self.root.after(0, self.ui.populate_inventory_tab, {"error": str(e)})
        try:
            if hasattr(self, 'status_label'): self.root.after(0, lambda: self.status_label.configure(text=f"Fetching power flow for site {site_id}..."))
            power_flow_data = self.api_client.get_site_current_power_flow(api_key=account_api_key, site_id=site_id)
            if hasattr(self, 'ui'): self.root.after(0, self.ui.populate_power_flow_tab, power_flow_data.get("siteCurrentPowerFlow") if power_flow_data else None)
        except OperationCancelledError: raise
        except Exception as e:
            all_details_fetched_successfully = False; print(f"Error fetching power flow: {e}")
            if hasattr(self, 'ui'): self.root.after(0, self.ui.populate_power_flow_tab, {"error": str(e)})
        self.root.after(0, self._finalize_site_details_fetch_ui, all_details_fetched_successfully, site_id)

    def _finalize_site_details_fetch_ui(self, success=True, site_id=None):
        self.is_fetching = False
        if hasattr(self, 'progress_bar'): self.progress_bar.stop()
        if hasattr(self, 'fetch_button'): self.fetch_button.configure(state="normal")
        if hasattr(self, 'fetch_sites_button'): self.fetch_sites_button.configure(state="normal")
        if hasattr(self, 'cancel_button'): self.cancel_button.pack_forget()
        if not self.is_fetching:
            if success:
                if hasattr(self, 'status_label'): self.status_label.configure(text=f"Details loaded for site {site_id}.")
            else:
                if hasattr(self, 'status_label'): self.status_label.configure(text=f"Partial or no details loaded for site {site_id}. Check console for errors.")
        else:
            if hasattr(self, 'status_label'): self.status_label.configure(text="Operation cancelled.")
        if hasattr(self, 'status_label'):
            current_status = self.status_label.cget("text")
            if not self.is_fetching and not any(s in current_status for s in ["loaded", "Error", "cancelled"]):
                self.status_label.configure(text="Ready.")

    def fetch_site_alerts_thread_from_tab(self):
        if not self.current_selected_site_id:
            messagebox.showwarning("No Site Selected", "Please select a site first.")
            return
        if self.is_fetching:
            messagebox.showwarning("Busy", "Another operation is in progress. Please wait.")
            return
        self.is_fetching = True
        if hasattr(self, 'ui') and self.ui.fetch_alerts_button_tab:
            self.ui.fetch_alerts_button_tab.configure(state="disabled")
        if hasattr(self, 'cancel_button'): self.cancel_button.pack(pady=5)
        if hasattr(self, 'status_label'): self.status_label.configure(text=f"Fetching alerts for site {self.current_selected_site_id}...")
        if hasattr(self, 'progress_bar'): self.progress_bar.start()
        start_date = self.ui.alert_start_date_entry.get_date() if hasattr(self, 'ui') and self.ui.alert_start_date_entry else datetime.now() - timedelta(days=7)
        end_date = self.ui.alert_end_date_entry.get_date() if hasattr(self, 'ui') and self.ui.alert_end_date_entry else datetime.now()
        start_time_str = datetime.combine(start_date, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
        end_time_str = datetime.combine(end_date, datetime.max.time()).strftime("%Y-%m-%d %H:%M:%S")
        thread = threading.Thread(target=self._execute_fetch_site_alerts, 
                                  args=(self.current_selected_site_id, start_time_str, end_time_str))
        thread.daemon = True
        thread.start()

    def _execute_fetch_site_alerts(self, site_id, start_time, end_time):
        account_api_key = self.account_api_key_entry.get()
        alerts_list = None
        error_msg = None
        success_for_finalize = True
        try:
            alerts_data_response = self.api_client.get_site_alerts(
                api_key=account_api_key, site_id=site_id, start_time_str=start_time, end_time_str=end_time
            )
            alerts_list = alerts_data_response.get("alerts", {}).get("alert") if alerts_data_response and "alerts" in alerts_data_response else None
        except OperationCancelledError: 
            error_msg = "cancelled"
            success_for_finalize = True
        except Exception as e:
            print(f"Error fetching alerts: {e}")
            error_msg = str(e)
            success_for_finalize = False
        if hasattr(self, 'ui'):
            self.root.after(0, self.ui.populate_alerts_tab, alerts_list, error_msg)
        self.root.after(0, self._finalize_alerts_fetch_ui, success_for_finalize, site_id, error_msg)

    def _finalize_alerts_fetch_ui(self, success, site_id, error_msg=None):
        self.is_fetching = False
        if hasattr(self, 'progress_bar'): self.progress_bar.stop()
        if hasattr(self, 'ui') and self.ui.fetch_alerts_button_tab:
            self.ui.fetch_alerts_button_tab.configure(state="normal")
        main_fetch_busy = hasattr(self, 'fetch_button') and self.fetch_button.cget("state") == "disabled"
        sites_fetch_busy = hasattr(self, 'fetch_sites_button') and self.fetch_sites_button.cget("state") == "disabled"
        if not main_fetch_busy and not sites_fetch_busy:
             if hasattr(self, 'cancel_button'): self.cancel_button.pack_forget()
        if hasattr(self, 'status_label'):
            if success and error_msg == "cancelled":
                self.status_label.configure(text=f"Alert fetching cancelled for site {site_id}.")
            elif success:
                self.status_label.configure(text=f"Alerts updated for site {site_id}.")
            else:
                self.status_label.configure(text=f"Error fetching alerts for site {site_id}.")

    def start_fetch_thread(self): 
        if self.is_fetching: 
            messagebox.showwarning("In Progress","Another operation in progress.")
            return
        if not self.validate_inputs(): 
            return
        self.is_fetching=True
        if hasattr(self, 'fetch_button'): self.fetch_button.configure(state="disabled")
        if hasattr(self, 'fetch_sites_button'): self.fetch_sites_button.configure(state="disabled")
        if hasattr(self, 'cancel_button'): self.cancel_button.pack(pady=5)
        dtft=threading.Thread(target=self.fetch_and_save_data)
        dtft.daemon=True
        dtft.start()
        
    def cancel_fetch(self):
        if self.is_fetching: 
            self.is_fetching=False
            if hasattr(self, 'status_label'): self.status_label.configure(text="Cancelling...")
            self.root.update()
        else: 
            if hasattr(self, 'status_label'): self.status_label.configure(text="No operation running to cancel.")
            
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
        sel_site_disp=self.ui.site_id_combobox.get()
        site_id=self.site_name_to_id_map.get(sel_site_disp,sel_site_disp)
        data_type=self.ui.data_type_var.get()
        sdo=self.ui.start_date_calendar.get_date()
        edo=self.ui.end_date_calendar.get_date()
        sh=self.ui.start_hour_var.get()
        eh=self.ui.end_hour_var.get()
        sdt=datetime.combine(sdo,datetime.strptime(f"{sh}:00:00","%H:%M:%S").time())
        edt=datetime.combine(edo,datetime.strptime(f"{eh}:59:59","%H:%M:%S").time())
        time_unit=self.ui.time_unit_var.get() if data_type=="production" else None
        
        if data_type=="voltage": max_chunk_days = 7
        elif data_type=="production":
            if time_unit == "HOUR": max_chunk_days = 28
            elif time_unit == "DAY": max_chunk_days = 365
            elif time_unit in ["WEEK", "MONTH"]: max_chunk_days = 1095
            else: max_chunk_days = 28
        else: max_chunk_days = 28
            
        if hasattr(self, 'status_label'): self.status_label.configure(text="Calculating export chunks...")
        if hasattr(self, 'progress_bar'):
            self.progress_bar.set(0)
            self.progress_bar.start()
        self.root.update()
        
        date_chunks = helpers.calculate_smart_chunks(sdt, edt, max_chunk_days, self.check_if_cancelled)
        
        if hasattr(self, 'progress_bar'): self.progress_bar.stop()
        num_chunks=len(date_chunks)
        if num_chunks==0:
            messagebox.showinfo("Info","No export intervals calculated.")
            self._restore_ui_after_fetch(); return
            
        print(f"Debug: Date range: {sdt} to {edt}")
        print(f"Debug: Max chunk days: {max_chunk_days}")
        print(f"Debug: Calculated {num_chunks} chunks:")
        for i, (start, end) in enumerate(date_chunks):
            days_in_chunk = (end - start).days + 1
            print(f"  Chunk {i+1}: {start} to {end} ({days_in_chunk} days)")
            
        if hasattr(self, 'status_label'): self.status_label.configure(text=f"Preparing {num_chunks} export requests...")
        if hasattr(self, 'progress_bar'): self.progress_bar.set(0.1)
        self.root.update()
        
        cdf=None
        adws=False
        try:
            for ci,(cs,ce) in enumerate(date_chunks):
                self.check_if_cancelled()
                cpb=0.1+(ci/num_chunks)*0.8
                sts=cs.strftime("%Y-%m-%d %H:%M:%S")
                ets=ce.strftime("%Y-%m-%d %H:%M:%S")
                if hasattr(self, 'status_label'): self.status_label.configure(text=f"Fetching export chunk {ci+1}/{num_chunks}: {cs.strftime('%m/%d %H:%M')}-{ce.strftime('%m/%d %H:%M')}")
                if hasattr(self, 'progress_bar'): self.progress_bar.set(cpb)
                self.root.update()
                ad=None
                df=None
                if data_type=="voltage":
                    isn=self.ui.inverter_entry.get()
                    ad = self.api_client.get_equipment_data(
                        api_key=account_api_key, site_id=site_id, equipment_sn=isn, start_time_str=sts, end_time_str=ets
                    )
                    if ad and "data" in ad and "telemetries" in ad["data"]:
                        tel=ad["data"]["telemetries"]
                        df = data_processor.process_voltage_data(tel)
                    if df is not None and df.empty and not tel and not adws:
                        if hasattr(self, 'status_label'): self.status_label.configure(text=f"Chunk {ci+1} (V): No telemetries.")
                        adws=True;
                        if ci==0: messagebox.showwarning("Data Warn","Chunk (V): No telemetries.")
                    elif ad and not (df is not None and not df.empty):
                        if hasattr(self, 'status_label'): self.status_label.configure(text=f"Chunk {ci+1} (V): Bad API resp.")
                        adws=True;
                        if ci==0: messagebox.showwarning("API Warn","Chunk (V): Bad structure.")
                else:
                    msel_list=[mtype for var,mtype in [
                        (self.ui.production_var.get(),"PRODUCTION"), (self.ui.consumption_var.get(),"CONSUMPTION"),
                        (self.ui.self_consumption_var.get(),"SELFCONSUMPTION"), (self.ui.feed_in_var.get(),"FEEDIN"),
                        (self.ui.purchased_var.get(),"PURCHASED")] if var]
                    ad = self.api_client.get_energy_details(
                        api_key=account_api_key, site_id=site_id, start_time_str=sts, end_time_str=ets,
                        meters_str=",".join(msel_list), time_unit=time_unit
                    )
                    if ad and "energyDetails" in ad and "meters" in ad["energyDetails"]:
                        df = data_processor.process_production_data(ad["energyDetails"]["meters"],ad["energyDetails"]["timeUnit"])
                    if df is not None and df.empty and not adws and \
                       (not ad or not ad.get("energyDetails") or not ad["energyDetails"].get("meters") or \
                        all(not m.get("values") for m in ad["energyDetails"]["meters"])):
                        if hasattr(self, 'status_label'): self.status_label.configure(text=f"Chunk {ci+1}(P): No meter values.")
                        adws=True;
                        if ci==0: messagebox.showwarning("Data Warn","Chunk(P):No meter vals.")
                    elif ad and not (df is not None and not df.empty):
                        if hasattr(self, 'status_label'): self.status_label.configure(text=f"Chunk {ci+1}(P):Bad API resp.")
                        adws=True;
                        if ci==0: messagebox.showwarning("API Warn","Chunk(P):Bad struct.")
                if (df is None or df.empty) and not adws and ad:
                    if hasattr(self, 'status_label'): self.status_label.configure(text=f"Chunk {ci+1} processed,0 pts.")
                if hasattr(self, 'progress_bar'): self.progress_bar.set(cpb+(0.8/num_chunks)*0.5)
                self.root.update()
                if df is not None and not df.empty:
                    adws=False
                    cdf=pd.concat([cdf,df],ignore_index=True) if cdf is not None else df
                    if 'date' in cdf.columns:
                        cdf=cdf.drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
            self.check_if_cancelled()
            if cdf is None or cdf.empty:
                messagebox.showwarning("No Data","No data for export.")
                self._restore_ui_after_fetch(); return
            if hasattr(self, 'status_label'): self.status_label.configure(text="Saving export file...")
            if hasattr(self, 'progress_bar'): self.progress_bar.set(0.9)
            self.root.update()
            output_folder = self.ui.output_path_var.get()
            file_format_to_save = self.ui.file_format_var.get()
            saved_fp, export_message = file_exporter.save_data_to_file(
                dataframe=cdf, output_path=output_folder, site_id=site_id,
                data_type=data_type, start_date_obj=sdo, end_date_obj=edo, file_format=file_format_to_save
            )
            if export_message and "Excel export requires" in export_message:
                messagebox.showwarning("Excel Export Issue", export_message)
            elif not saved_fp and export_message:
                 messagebox.showerror("File Save Error", export_message)
                 if hasattr(self, 'status_label'): self.status_label.configure(text=f"Failed to save: {export_message[:100]}")
                 self._restore_ui_after_fetch(); return
            if saved_fp:
                total_records = len(cdf)
                date_range_str = f"{sdt.strftime('%Y-%m-%d')} to {edt.strftime('%Y-%m-%d')}"
                final_status_message = f"Saved {total_records} export records for {date_range_str} to {os.path.basename(saved_fp)}"
                if export_message and "Saved as CSV instead" in export_message:
                    final_status_message += f" (as CSV due to missing Excel engine)"
                if hasattr(self, 'status_label'): self.status_label.configure(text=final_status_message)
                if hasattr(self, 'progress_bar'): self.progress_bar.set(1.0)
                messagebox.showinfo("Success", f"Export data saved:\n{saved_fp}\n\n{total_records} data points.")
            else:
                messagebox.showerror("Save Error", "Failed to save file. Unknown error.")
                if hasattr(self, 'status_label'): self.status_label.configure(text="Failed to save file.")
        except OperationCancelledError:
            if hasattr(self, 'status_label'): self.status_label.configure(text="Export cancelled.")
            if hasattr(self, 'progress_bar'): self.progress_bar.set(0)
        except requests.exceptions.Timeout as e:
            messagebox.showerror("API Timeout",f"A timeout occurred: {e}.")
            if hasattr(self, 'status_label'): self.status_label.configure(text="Error: API Timeout.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("API Connection Error",f"Could not connect to API: {e}")
            if hasattr(self, 'status_label'): self.status_label.configure(text=f"API Connection Error: {str(e)[:100]}")
        except Exception as e:
            messagebox.showerror("Processing Error",f"An unexpected error occurred: {e}")
            if hasattr(self, 'status_label'): self.status_label.configure(text=f"Error: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
        finally:
            self._restore_ui_after_fetch()

    def _restore_ui_after_fetch(self):
        self.is_fetching=False
        if hasattr(self, 'fetch_button'): self.fetch_button.configure(state="normal")
        if hasattr(self, 'fetch_sites_button'): self.fetch_sites_button.configure(state="normal")
        if hasattr(self, 'cancel_button'): self.cancel_button.pack_forget()
        if hasattr(self, 'status_label'):
            cs = self.status_label.cget("text")
            if not any(s in cs for s in ["Saved","Error","Cancelled","No data","No sites","Successfully fetched","loaded"]):
                self.status_label.configure(text="Ready.")
        if hasattr(self, 'progress_bar'):
            pb_get = self.progress_bar.get()
            if pb_get <1.0 and "Error" not in (cs if 'cs' in locals() else "") and not any(s in (cs if 'cs' in locals() else "") for s in ["Saved","Cancelled","Successfully fetched","loaded"]):
                self.progress_bar.set(0)

    # def process_voltage_data(self, telemetries): # MOVED to utils.data_processor
    #     pass

    # def process_production_data(self, meters_data, time_unit): # MOVED to utils.data_processor
    #     pass

    def validate_inputs(self):
        if not self.account_api_key_entry.get():
            messagebox.showerror("Input Error","Account API Key required.")
            return False
        selected_site_display = self.ui.site_id_combobox.get()
        site_id_to_use = self.site_name_to_id_map.get(selected_site_display, selected_site_display)
        if not site_id_to_use or selected_site_display in ["Enter Site ID or select/search from list", "No match found...", "No sites found or error."]:
            messagebox.showerror("Input Error","Valid Site ID required for export.")
            return False
        try:
            if selected_site_display not in self.site_name_to_id_map:
                int(site_id_to_use)
        except ValueError:
            messagebox.showerror("Input Error",f"Manually entered Site ID '{site_id_to_use}' is not a valid integer ID.")
            return False
        start_date_obj = self.ui.start_date_calendar.get_date()
        end_date_obj = self.ui.end_date_calendar.get_date()
        start_hour_str = self.ui.start_hour_var.get()
        end_hour_str = self.ui.end_hour_var.get()
        start_datetime = datetime.combine(start_date_obj, datetime.strptime(f"{start_hour_str}:00:00", "%H:%M:%S").time())
        end_datetime = datetime.combine(end_date_obj, datetime.strptime(f"{end_hour_str}:59:59", "%H:%M:%S").time())
        if start_datetime > end_datetime:
            messagebox.showerror("Input Error","Start date/time cannot be after end date/time.")
            return False
        days_diff = (end_date_obj - start_date_obj).days
        current_data_type = self.ui.data_type_var.get()
        if current_data_type == "voltage":
            if not self.ui.inverter_entry.get():
                messagebox.showerror("Input Error","Inverter Serial Number is required for voltage data.")
                return False
            if days_diff > 30:
                 estimated_calls = (days_diff + 6) // 7
                 if not messagebox.askokcancel("Long Date Range Warning",
                                              f"Fetching voltage data for {days_diff+1} days will require approximately {estimated_calls} API calls. This may take a while. Continue?"):
                    return False
        else:
            selected_meters = any([self.ui.production_var.get(), self.ui.consumption_var.get(), self.ui.self_consumption_var.get(), self.ui.feed_in_var.get(), self.ui.purchased_var.get()])
            if not selected_meters:
                messagebox.showerror("Input Error","At least one meter type must be selected for production data.")
                return False
            current_time_unit = self.ui.time_unit_var.get()
            estimated_calls = helpers.estimate_chunks_needed(start_date_obj, end_date_obj, current_data_type, current_time_unit)
            if estimated_calls > 20 :
                if not messagebox.askokcancel("Many API Calls Warning",
                                             f"This export configuration will require approximately {estimated_calls} API calls. This could take significant time and API quota. Continue?"):
                    return False
        if not os.path.isdir(self.ui.output_path_var.get()):
            messagebox.showerror("Input Error","Selected output folder is not a valid directory.")
            return False
        return True

if __name__ == "__main__":
    try: 
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1) 
    except Exception: 
        pass 
    root = ctk.CTk()
    app = SolarEdgeAPIApp(root)
    root.mainloop()
