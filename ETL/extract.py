import pandas as pd
import os

default_parquet_folder_path: str = "ETL/phase1_official_dataset"

def extract(parquet_file_path: str) -> pd.DataFrame:
    """Extracts data from a parquet file and returns a pandas DataFrame.

    Args:
        parquet_file_path (str): The path to the parquet file to extract data from.
    Returns:
        pd.DataFrame: A pandas DataFrame containing the extracted data.
    """
    print("+-+-+-+-+-+-+-+-+-+-+-+-+")
    print(f"Extracting data from {parquet_file_path}...")

    # Read the parquet file into a pandas DataFrame
    df = pd.read_parquet(parquet_file_path, engine='pyarrow')

    # Print the shape of the DataFrame and the data types of each column
    print(f"Done! Data extracted from {parquet_file_path}. Shape: {df.shape}")
    columns = df.columns.tolist()
    types = df.dtypes
    for col, dtype in zip(columns, types):
        print(f"Column: {col}, Type: {dtype}")
    return df

def extract_all(parquet_files_folder_path: str) -> list:
    """Extracts data from all parquet files in the given folder and returns a list of pandas DataFrames.
    
    Args:
        parquet_files_folder_path (str): The path to the folder containing the parquet files.
    Returns:
        list: A list of pandas DataFrames, each containing the extracted data from a parquet file
    """
    dataframes = []
    # Calls extract() for each parquet file in the folder and appends the resulting DataFrame to the dataframes list
    parquet_files: list = [f for f in os.listdir(parquet_files_folder_path) if f.endswith(".parquet")]
    for parquet_file in parquet_files:
        df = extract(os.path.join(parquet_files_folder_path, parquet_file))
        dataframes.append(df)
    return dataframes

# extract_all(default_parquet_folder_path)
# extract("ETL/phase1_official_dataset/driver.parquet")