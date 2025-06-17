import os
import pandas as pd
from datetime import datetime

def save_data_to_file(dataframe, output_path, site_id, data_type, start_date_obj, end_date_obj, file_format):
    """
    Saves the given DataFrame to a file (CSV or Excel).

    Args:
        dataframe (pd.DataFrame): The data to save.
        output_path (str): The directory to save the file in.
        site_id (str): The site ID, used for generating the filename.
        data_type (str): The type of data (e.g., "production", "voltage"), used for the filename.
        start_date_obj (datetime.date): The start date of the data range.
        end_date_obj (datetime.date): The end date of the data range.
        file_format (str): "csv" or "excel".

    Returns:
        tuple: (full_file_path, message)
               full_file_path (str): The absolute path to the saved file.
               message (str or None): An informational or warning message, e.g., if fallback to CSV occurred.
    """
    if dataframe is None or dataframe.empty:
        return None, "No data to save."

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_site_id = str(site_id).replace("/", "-").replace("\\", "-")
    base_filename = f"SolarEdge_{data_type}_{safe_site_id}_{start_date_obj.strftime('%Y%m%d')}_{end_date_obj.strftime('%Y%m%d')}_{timestamp_str}"

    file_extension = "xlsx" if file_format == "excel" else "csv"
    full_file_path = os.path.join(output_path, f"{base_filename}.{file_extension}")

    warning_message = None

    try:
        if file_format == "csv":
            dataframe.to_csv(full_file_path, index=False)
        elif file_format == "excel":
            try:
                dataframe.to_excel(full_file_path, index=False, engine='openpyxl')
            except ImportError:
                # Fallback to CSV if openpyxl is not installed
                old_full_file_path = full_file_path
                file_extension = "csv"
                full_file_path = os.path.join(output_path, f"{base_filename}.{file_extension}")
                dataframe.to_csv(full_file_path, index=False)
                warning_message = (
                    f"Excel export requires 'openpyxl'. Saved as CSV instead: {os.path.basename(full_file_path)}\n\n"
                    f"To enable Excel export, please install the package: pip install openpyxl"
                )
                # print(f"Warning: openpyxl not found. Falling back to CSV: {full_file_path}")
        else:
            return None, f"Unsupported file format: {file_format}"

        return full_file_path, warning_message

    except Exception as e:
        # Catch any other exception during file saving
        return None, f"Error saving file {os.path.basename(full_file_path)}: {e}"
