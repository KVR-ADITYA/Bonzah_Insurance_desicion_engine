import pandas as pd
import numpy as np
import os
from pathlib import Path

def clean_column_names(df):
    """
    Clean column names by removing line breaks, extra spaces, and empty names
    """
    # Create a mapping for column renaming
    column_mapping = {}
    
    for col in df.columns:
        # Replace line breaks with spaces and strip whitespace
        clean_name = str(col).replace('\n', ' ').replace('\r', ' ').strip()
        
        # Handle empty or generic column names
        if clean_name == '' or clean_name == 'nan' or clean_name.startswith('_'):
            clean_name = f'empty_col_{df.columns.get_loc(col)}'
        
        # Shorten very long column names
        if len(clean_name) > 50:
            clean_name = clean_name[:47] + '...'
            
        column_mapping[col] = clean_name
    
    return df.rename(columns=column_mapping)

def remove_empty_columns(df):
    """
    Remove columns that are completely empty or contain only null/empty values
    """
    # Identify columns that are completely empty
    empty_cols = []
    for col in df.columns:
        if df[col].isna().all() or (df[col] == '').all():
            empty_cols.append(col)
    
    # Remove empty columns
    df_cleaned = df.drop(columns=empty_cols)
    
    print(f"Removed {len(empty_cols)} empty columns: {empty_cols}")
    return df_cleaned

def clean_data_values(df):
    """
    Clean data values - handle missing values, trim whitespace, etc.
    """
    # Create a copy to avoid modifying original
    df_cleaned = df.copy()
    
    # Clean string columns
    for col in df_cleaned.columns:
        if df_cleaned[col].dtype == 'object':
            # Strip whitespace from string values
            df_cleaned[col] = df_cleaned[col].astype(str).str.strip()
            
            # Replace empty strings with NaN
            df_cleaned[col] = df_cleaned[col].replace(['', 'nan', 'None'], np.nan)
    
    return df_cleaned

def remove_empty_rows(df):
    """
    Remove rows that are completely empty
    """
    # Count rows before
    initial_rows = len(df)
    
    # Remove rows where all values are NaN
    df_cleaned = df.dropna(how='all')
    
    # Count rows after
    final_rows = len(df_cleaned)
    
    print(f"Removed {initial_rows - final_rows} completely empty rows")
    return df_cleaned

def clean_csv_file(file_path):
    """
    Clean a single CSV file
    """
    print(f"\n{'='*50}")
    print(f"Cleaning {file_path}")
    print(f"{'='*50}")
    
    try:
        # Read the CSV file
        df = pd.read_csv(file_path, encoding='utf-8')
        
        print(f"Original shape: {df.shape}")
        
        # Apply cleaning steps
        df = clean_column_names(df)
        df = remove_empty_columns(df)
        df = clean_data_values(df)
        df = remove_empty_rows(df)
        
        print(f"Final shape: {df.shape}")
        
        # Display column info
        print(f"\nColumn names after cleaning:")
        for i, col in enumerate(df.columns):
            non_null_count = df[col].notna().sum()
            print(f"  {i+1}. {col} ({non_null_count}/{len(df)} non-null)")
        
        return df
        
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return None

def main():
    """
    Main function to clean all CSV files and save them
    """
    # Define input files
    input_files = [
        'deposition.csv',
        'dob.csv', 
        'look_back.csv',
        'record_classes.csv',
        'risk_score.csv',
        'categories1.csv',
        'charge_type_class.csv'
    ]
    
    # Create output directory
    output_dir = Path('cleaned_data')
    output_dir.mkdir(exist_ok=True)
    
    # Dictionary to store cleaned dataframes
    cleaned_data = {}
    
    # Process each file
    for file_path in input_files:
        if os.path.exists(file_path):
            df_cleaned = clean_csv_file(file_path)
            if df_cleaned is not None:
                cleaned_data[file_path] = df_cleaned
        else:
            print(f"File not found: {file_path}")
    
    # Save cleaned files
    print(f"\n{'='*50}")
    print("Saving cleaned files...")
    print(f"{'='*50}")
    
    for file_name, df in cleaned_data.items():
        # Create output filename
        base_name = Path(file_name).stem
        output_file = output_dir / f"{base_name}_cleaned.csv"
        
        # Save cleaned CSV
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved: {output_file}")
    
    # Create a summary file
    summary_file = output_dir / "cleaning_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("CSV Data Cleaning Summary\n")
        f.write("=" * 30 + "\n\n")
        
        for file_name, df in cleaned_data.items():
            f.write(f"File: {file_name}\n")
            f.write(f"  Final shape: {df.shape}\n")
            f.write(f"  Columns: {list(df.columns)}\n")
            f.write(f"  Data types: {dict(df.dtypes)}\n\n")
    
    print(f"Summary saved: {summary_file}")
    
    # Create a combined Excel file with all cleaned data
    excel_file = output_dir / "all_cleaned_data.xlsx"
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        for file_name, df in cleaned_data.items():
            sheet_name = Path(file_name).stem[:31]  # Excel sheet name limit
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"Combined Excel file saved: {excel_file}")
    
    print(f"\nCleaning complete! All files saved to: {output_dir}")

if __name__ == "__main__":
    main()