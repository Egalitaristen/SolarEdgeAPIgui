import requests
import json
import time

# Custom exception for cancellation, can be shared or defined here if not already accessible
# For now, assume it might be defined elsewhere or SolarEdgeAPIApp.OperationCancelledError can be imported if needed.
# If SolarEdgeClient is to be truly independent, it should define its own or expect a generic one.
# Using the centralized one from utils.helpers
from utils.helpers import OperationCancelledError

class SolarEdgeClient:
    BASE_URL = "https://monitoringapi.solaredge.com"

    def __init__(self, check_if_cancelled_callback=None, status_update_callback=None):
        """
        Initializes the SolarEdge API client.
        :param check_if_cancelled_callback: A function to call to check if the operation should be cancelled.
        :param status_update_callback: An optional function to call for updating status messages (e.g., for rate limit waits).
        """
        self.check_if_cancelled = check_if_cancelled_callback
        self.status_update_callback = status_update_callback

    def _request_data(self, endpoint, params):
        """
        Internal method to handle the actual HTTP request.
        This is what fetch_api_data will become, more or less.
        """
        max_retries = 3
        base_retry_delay = 5  # seconds

        for attempt in range(max_retries):
            if self.check_if_cancelled:
                self.check_if_cancelled() # Will raise OperationCancelledError if cancelled

            try:
                # print(f"Debug: Client making API request to {self.BASE_URL}{endpoint} (attempt {attempt+1}/{max_retries})")
                # print(f"Debug: Client params: {params}")
                response = requests.get(f"{self.BASE_URL}{endpoint}", params=params, timeout=45)
                # print(f"Debug: Client response status: {response.status_code}")

                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        return json_data
                    except json.JSONDecodeError as je:
                        raise Exception(f"API returned invalid JSON (Status 200, URL: {self.BASE_URL}{endpoint})\nResponse: {response.text[:200]}...\nError: {je}")

                error_prefix = f"API Error (Status {response.status_code}, URL: {self.BASE_URL}{endpoint})"
                error_details = ""
                try:
                    json_error = response.json()
                    if isinstance(json_error, dict):
                        error_details = json_error.get("message", "")
                        if not error_details and "String" in json_error:
                            string_obj = json_error["String"]
                            if isinstance(string_obj, dict): error_details = string_obj.get("message", "")
                            elif isinstance(string_obj, str): error_details = string_obj
                        if not error_details and "error" in json_error:
                            error_obj = json_error["error"]
                            if isinstance(error_obj, dict): error_details = error_obj.get("message", "")
                            elif isinstance(error_obj, str): error_details = error_obj
                        if not error_details: error_details = str(json_error)
                    elif isinstance(json_error, str): error_details = json_error
                    else: error_details = str(json_error)
                except json.JSONDecodeError:
                    error_details = f"Non-JSON response: {response.text[:200]}..."
                except Exception as e_parse:
                    error_details = f"Error parsing error response: {str(e_parse)} - Raw: {response.text[:200]}..."

                full_error_message = f"{error_prefix}: {error_details}"

                if response.status_code == 429: # Rate limiting
                    retry_after = int(response.headers.get('Retry-After', base_retry_delay * (attempt + 1)))
                    if self.status_update_callback:
                        self.status_update_callback(f"Rate limit. Retrying in {retry_after}s (Attempt {attempt+1}/{max_retries})")

                    for _ in range(retry_after):
                        if self.check_if_cancelled: self.check_if_cancelled()
                        time.sleep(1)
                    continue
                elif response.status_code in [400, 401, 403, 404]:
                    # Specific handling for 403 on alerts
                    if response.status_code == 403 and "alerts" in endpoint.lower() and ("startTime" in params and "endTime" in params):
                         raise Exception(f"Access Denied (403) for alerts.\nThis might be due to date range limits (try <1 month) or API key permissions.\nDetails: {error_details}")
                    raise Exception(full_error_message)
                else: # Server-side errors or other unexpected issues
                    if attempt < max_retries - 1:
                        wait_time = base_retry_delay * (attempt + 1)
                        if self.status_update_callback:
                            self.status_update_callback(f"{full_error_message}. Retrying in {wait_time}s (Attempt {attempt+1}/{max_retries})")
                        for _ in range(wait_time):
                            if self.check_if_cancelled: self.check_if_cancelled()
                            time.sleep(1)
                        continue
                    else: # Last attempt failed
                        raise Exception(full_error_message)

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = base_retry_delay * (attempt + 1)
                    if self.status_update_callback:
                        self.status_update_callback(f"Request timed out for {self.BASE_URL}{endpoint}. Retrying in {wait_time}s (Attempt {attempt+1}/{max_retries})")
                    for _ in range(wait_time):
                        if self.check_if_cancelled: self.check_if_cancelled()
                        time.sleep(1)
                    continue
                else:
                    raise Exception(f"Request timed out after {max_retries} attempts for {self.BASE_URL}{endpoint}.")

            except requests.exceptions.RequestException as e_req: # Other connection errors
                if attempt < max_retries - 1:
                    wait_time = base_retry_delay * (attempt + 1)
                    if self.status_update_callback:
                         self.status_update_callback(f"Connection error for {self.BASE_URL}{endpoint}. Retrying in {wait_time}s (Attempt {attempt+1}/{max_retries})")
                    for _ in range(wait_time):
                        if self.check_if_cancelled: self.check_if_cancelled()
                        time.sleep(1)
                    continue
                else:
                    raise Exception(f"Failed to connect to {self.BASE_URL}{endpoint} after {max_retries} attempts: {e_req}")

        raise Exception(f"Max retries exceeded for {self.BASE_URL}{endpoint} without explicit error handling completion.")

    # --- Specific API Call Methods ---

    def get_sites_list(self, api_key, start_index, size):
        """Fetches the list of sites."""
        endpoint = "/sites/list"
        params = {
            "api_key": api_key,
            "startIndex": start_index,
            "size": size
        }
        return self._request_data(endpoint, params)

    def get_site_overview(self, api_key, site_id):
        """Fetches overview data for a specific site."""
        endpoint = f"/site/{site_id}/overview.json"
        params = {"api_key": api_key}
        return self._request_data(endpoint, params)

    def get_site_inventory(self, api_key, site_id):
        """Fetches inventory data for a specific site."""
        endpoint = f"/site/{site_id}/inventory.json"
        params = {"api_key": api_key}
        return self._request_data(endpoint, params)

    def get_site_current_power_flow(self, api_key, site_id):
        """Fetches current power flow data for a specific site."""
        endpoint = f"/site/{site_id}/currentPowerFlow.json"
        params = {"api_key": api_key}
        return self._request_data(endpoint, params)

    def get_site_alerts(self, api_key, site_id, start_time_str, end_time_str):
        """Fetches alerts for a specific site within a date range."""
        endpoint = f"/site/{site_id}/alerts.json"
        params = {
            "api_key": api_key,
            "startTime": start_time_str,
            "endTime": end_time_str
        }
        return self._request_data(endpoint, params)

    def get_equipment_data(self, api_key, site_id, equipment_sn, start_time_str, end_time_str):
        """Fetches equipment telemetry data (e.g., inverter voltage)."""
        # Note: The original code used `/equipment/{site_id}/{isn}/data.json`
        # Standard SolarEdge might be `/equipment/{site_id}/{equipment_sn}/data` - check API docs
        # For now, using the structure from the original code.
        endpoint = f"/equipment/{site_id}/{equipment_sn}/data.json"
        params = {
            "api_key": api_key,
            "startTime": start_time_str,
            "endTime": end_time_str
        }
        return self._request_data(endpoint, params)

    def get_energy_details(self, api_key, site_id, start_time_str, end_time_str, meters_str, time_unit):
        """Fetches detailed energy information for a site."""
        endpoint = f"/site/{site_id}/energyDetails.json"
        params = {
            "api_key": api_key,
            "startTime": start_time_str,
            "endTime": end_time_str,
            "meters": meters_str, # Comma-separated string of meter types
            "timeUnit": time_unit
        }
        return self._request_data(endpoint, params)
