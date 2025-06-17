from datetime import timedelta, datetime

class OperationCancelledError(Exception):
    """Custom exception for when an operation is cancelled by the user."""
    pass

def calculate_smart_chunks(start_dt, end_dt, max_chunk_days, check_if_cancelled_callback=None):
    """
    Smart chunking algorithm that works with any date range.
    Breaks the date range into optimal chunks while respecting API limits.
    Requires a callback function `check_if_cancelled_callback` which should raise
    OperationCancelledError if cancellation is requested.
    """
    chunks = []
    current_start = start_dt

    # print(f"Debug: Starting chunking - Start: {start_dt}, End: {end_dt}, Max chunk days: {max_chunk_days}")

    while current_start <= end_dt:
        if check_if_cancelled_callback:
            check_if_cancelled_callback() # Check for cancellation at the start of each chunk calculation

        ideal_end = current_start + timedelta(days=max_chunk_days - 1)
        chunk_end = min(ideal_end, end_dt)

        if chunk_end < end_dt: # Not the final chunk
            chunk_end = chunk_end.replace(hour=23, minute=59, second=59)
        # Else: it's the final chunk, use the exact end_dt which includes time

        chunks.append((current_start, chunk_end))
        # print(f"Debug: Added chunk: {current_start} to {chunk_end}")

        if chunk_end >= end_dt:
            break

        current_start = (chunk_end + timedelta(seconds=1)).replace(hour=0, minute=0, second=0)
        # print(f"Debug: Next chunk will start at: {current_start}")

    # print(f"Debug: Chunking complete. Created {len(chunks)} chunks.")
    return chunks

def estimate_chunks_needed(start_date, end_date, data_type, time_unit=None):
    """
    Estimate the number of API calls needed for a given date range.
    start_date, end_date are date objects (not datetime).
    """
    total_days = (end_date - start_date).days + 1

    if data_type == "voltage":
        return max(1, (total_days + 6) // 7)  # 7 days per chunk for voltage
    elif data_type == "production":
        if time_unit == "HOUR":
            # SolarEdge API: "The period for hourly resolution is limited to one month."
            # Assuming 30 days for safety, though some months are 31.
            return max(1, (total_days + 29) // 30)
        elif time_unit == "DAY":
            # SolarEdge API: "The period for daily resolution is limited to one year."
            return max(1, (total_days + 364) // 365)
        elif time_unit in ["WEEK", "MONTH"]:
            # SolarEdge API: "The period for weekly and monthly resolution is limited to the entire site's lifetime."
            # For practical purposes, let's assume a very large number (e.g. 10 years) isn't one chunk.
            # A 3-year limit per call seems reasonable if not specified otherwise.
            return max(1, (total_days + (3*365 -1)) // (3*365) )
        else: # Default for unknown production time_unit
            return max(1, (total_days + 29) // 30)
    else: # Default fallback for unknown data_type
        return max(1, (total_days + 29) // 30)
