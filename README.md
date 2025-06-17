# SolarEdge API Data Fetcher

This application provides a user-friendly graphical interface (GUI) to interact with the SolarEdge monitoring API. It allows users to fetch site details, real-time data, and historical energy information, and export it for local analysis.

## Features

*   **Site Management:**
    *   Fetch and list all sites associated with a SolarEdge Account API Key.
    *   Select a site to view its detailed information.
*   **Real-time Site Data:**
    *   Display site overview, including current power and recent energy generation.
    *   Show detailed site inventory (inverters, batteries, meters).
    *   Visualize current power flow between production, consumption, grid, and storage.
    *   Fetch and display site alerts within a specified date range.
*   **Data Export:**
    *   Export detailed energy production data (Production, Consumption, Self-Consumption, Feed-In, Purchased).
    *   Export inverter telemetry data (e.g., DC voltage, current, power per phase).
    *   Customizable date ranges for data export.
    *   Selectable time units for energy data (Hour, Day, Week, Month).
*   **Robust & User-Friendly:**
    *   Graphical User Interface (GUI) for ease of use.
    *   Smart data chunking automatically handles API limitations for large data requests, preventing timeouts and reducing manual effort.
    *   Export data to CSV or Microsoft Excel (`.xlsx`) formats.
    *   Support for cancelling ongoing data fetching operations.
    *   Status bar and progress indicators for ongoing operations.

## Project Structure

The project is organized into several key modules:

*   \`SolarEdgeAPI.py\`: The main application script. It initializes the UI, handles user interactions, and orchestrates API calls and data processing.
*   \`api/solaredge_client.py\`: Contains the \`SolarEdgeClient\` class, responsible for all direct communication with the SolarEdge API, including request formatting, error handling, and rate limit awareness.
*   \`ui/app_ui.py\`: Defines the \`AppUI\` class, which builds and manages all elements of the graphical user interface using CustomTkinter.
*   \`utils/data_processor.py\`: Includes functions for processing raw data fetched from the API (e.g., converting to Pandas DataFrames, cleaning, and structuring).
*   \`utils/file_exporter.py\`: Provides the \`save_data_to_file\` function for saving processed data into CSV or Excel files.
*   \`utils/helpers.py\`: Contains utility functions, such as \`calculate_smart_chunks\` for breaking down large data requests and \`estimate_chunks_needed\`, as well as the custom \`OperationCancelledError\` exception.
*   \`README.md\`: This file – providing documentation for the project.
*   \`LICENSE\`: Contains the license information for the project.

## Setup and Usage

### Prerequisites

*   **Python:** Version 3.7 or higher.
*   **SolarEdge API Key:** You need an API key from your SolarEdge account (Site Monitoring > Admin > Site Access > API Access).
*   **Python Libraries:** The application relies on several external libraries. You can install them using pip.

### Installation

1.  **Clone the Repository (or Download Files):**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
    (Replace `<repository_url>` and `<repository_directory>` with actual values if applicable. If downloaded as a ZIP, extract it.)

2.  **Install Dependencies:**
    It's recommended to use a virtual environment.
    ```bash
    python -m venv .venv
    # On Windows
    .venv\Scripts\activate
    # On macOS/Linux
    source .venv/bin/activate
    ```
    Then, install the required packages:
    ```bash
    pip install customtkinter requests pandas tkcalendar openpyxl
    ```
    *(Note: A `requirements.txt` file would typically be provided for easier installation, e.g., `pip install -r requirements.txt`.)*

### Running the Application

Once the dependencies are installed, you can run the application using:

```bash
python SolarEdgeAPI.py
```

### Using the Application

1.  **Enter API Key:**
    *   Launch the application.
    *   In the "Account API Key" field, enter your SolarEdge account-level API key.

2.  **Fetch Sites:**
    *   Click the "Fetch Sites" button.
    *   The application will retrieve a list of all sites associated with your API key.
    *   The "Site ID" dropdown will be populated with your sites (usually in the format "Site Name (Site ID)").

3.  **View Site Details (Tabs):**
    *   Select a site from the "Site ID" dropdown.
    *   The tabs below ("Overview", "Inventory", "Power Flow", "Alerts") will automatically populate with data for the selected site.
    *   For the "Alerts" tab, you can specify a date range and click "Fetch Alerts for Range" to view alerts within that period.

4.  **Export Data:**
    *   **Site Selection:** Ensure the correct site is selected in the "Site ID" dropdown. You can also manually type a valid Site ID if it's not in the list (though fetching sites first is recommended).
    *   **Data Type:**
        *   Choose "Production Details (Energy)" for energy data.
        *   Choose "Voltage Values (Equipment)" for inverter telemetry.
    *   **Configure Specific Inputs:**
        *   If "Voltage Values" is selected, enter the "Inverter Serial Number" (you can find this in the "Inventory" tab).
        *   If "Production Details" is selected, check the boxes for the desired "Meters" (e.g., Production, Consumption).
    *   **Date Range:**
        *   Select the "Start Date" and "End Date" for your data export.
        *   Select the "Start Hour" and "End Hour".
        *   If exporting "Production Details", also select the "Time Unit" (e.g., HOUR, DAY, MONTH). The application will automatically adjust date ranges based on the selected data type to suggest common periods (e.g., 7 days for voltage, 30 days for hourly production).
    *   **Output Options:**
        *   Choose the "File Format" (CSV or Excel).
        *   Specify the "Output Folder" by typing the path or clicking "Browse...".
    *   **Fetch and Save:**
        *   Click the "Fetch and Save Export Data" button.
        *   The application will fetch the data in chunks (you'll see progress updates in the status bar). This might take some time depending on the date range and API responsiveness.
        *   Once complete, a success message will appear, and the file will be saved in your chosen output folder.

5.  **Cancel Operation:**
    *   If any data fetching process (site list, site details, or data export) is taking too long or was started by mistake, click the "Cancel Current Operation" button.

## Configuration

The primary configuration required is your **SolarEdge Account API Key**. This key is essential for the application to access your site data.

*   **API Key:** Obtain this from your SolarEdge monitoring portal under `Admin > Site Access > API Access`. Ensure the key has the necessary permissions to read site data and telemetry.

There are no other external configuration files needed for the application to run. Output settings (like file paths and formats) are configured directly within the application's UI.

## A Note on API Limits

The SolarEdge Monitoring API has daily and per-minute request limits. This application is designed to be respectful of these limits by:

*   Fetching data in optimized chunks, especially for large date ranges.
*   Providing warnings for export configurations that might result in a large number of API calls.

However, users should still be mindful of their usage, particularly when exporting very large datasets or making frequent requests, to avoid exceeding their API quota. If you encounter errors related to API limits (e.g., HTTP 429 errors), please wait for some time before trying again.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for full details.

## Future Improvements / Known Issues

*   **Create `requirements.txt`:** For easier installation of dependencies (`pip install -r requirements.txt`).
*   **Enhanced Error Handling:** Implement more specific error messages for different API responses or operational failures.
*   **Configuration File:** For advanced settings (e.g., custom API endpoints for testing, default date ranges).
*   **Theme Customization:** Allow users to switch between light/dark themes more explicitly if CustomTkinter supports it easily.
*   **Unit Tests:** Develop a suite of unit tests to ensure code reliability and facilitate easier refactoring.
*   **Internationalization (i18n):** Add support for multiple languages in the UI.
*   **Direct Charting/Visualization:** Incorporate basic charting of fetched data directly within the application.
*   **Known Issue - Excel Export on Some Systems:** The Excel export relies on `openpyxl`. If this library is not present or not correctly installed, the application will fall back to CSV export. A more explicit check or bundled dependency could improve this.
*   **Known Issue - UI Responsiveness during Initial Load:** On slower systems or with very large site lists, the UI might briefly freeze during the initial fetch. Further optimization of background tasks could be explored.
