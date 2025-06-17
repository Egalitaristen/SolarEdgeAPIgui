import pandas as pd
# No specific from pandas import needed if using pd.DataFrame, pd.to_datetime, pd.merge

def process_voltage_data(telemetries):
    if not telemetries: return pd.DataFrame()
    df=pd.DataFrame(telemetries)
    if 'date' not in df.columns: return df
    df['date']=pd.to_datetime(df['date'],errors='coerce')
    df=df.dropna(subset=['date'])
    df=df.fillna(0).sort_values('date').reset_index(drop=True)
    if 'date' in df.columns: # Re-check because previous dropna might remove it if all dates were bad
        df=df[['date']+[c for c in df.columns if c!='date']]
    return df

def process_production_data(meters_data, time_unit):
    if not meters_data: return pd.DataFrame()
    all_meter_dfs=[]
    for meter_entry in meters_data:
        meter_type, values = meter_entry.get('type'), meter_entry.get('values')
        if not meter_type or not values: continue

        meter_df=pd.DataFrame(values)
        if 'date' not in meter_df.columns or 'value' not in meter_df.columns: continue

        meter_df['date']=pd.to_datetime(meter_df['date'],errors='coerce')
        meter_df=meter_df.dropna(subset=['date'])
        meter_df.rename(columns={'value':meter_type},inplace=True)
        meter_df[meter_type] = meter_df[meter_type].fillna(0)
        all_meter_dfs.append(meter_df[['date',meter_type]])

    if not all_meter_dfs: return pd.DataFrame()

    result_df = all_meter_dfs[0]
    for i in range(1,len(all_meter_dfs)):
        if 'date' not in all_meter_dfs[i].columns: continue
        result_df=pd.merge(result_df,all_meter_dfs[i],on='date',how='outer')

    return result_df.fillna(0).sort_values('date').reset_index(drop=True)
