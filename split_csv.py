#!/usr/bin/env python3
"""
Script to split a CSV file into individual documents.
Each document will contain the header row and one data row.
"""

import csv
import os
from pathlib import Path


def split_csv_to_documents(csv_file_path: str, output_dir: str):
    """
    Split a CSV file into individual documents.
    
    Args:
        csv_file_path: Path to the input CSV file
        output_dir: Directory to save individual documents
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        # Read the CSV file
        csv_reader = csv.reader(csvfile)
        
        # Get the header row
        header = next(csv_reader)
        
        # Process each data row
        for row_num, row in enumerate(csv_reader, start=1):
            # Create filename for this document
            filename = f"document_{row_num:05d}.txt"
            filepath = os.path.join(output_dir, filename)
            
            # Create document content with header and data row
            with open(filepath, 'w', encoding='utf-8') as doc_file:
                # Write header
                doc_file.write(','.join(header) + '\n')
                # Write data row
                doc_file.write(','.join(row) + '\n')
            
            # Print progress every 1000 documents
            if row_num % 1000 == 0:
                print(f"Processed {row_num} documents...")
    
    print(f"Successfully split CSV into {row_num} individual documents in '{output_dir}'")


if __name__ == "__main__":
    input_csv = "catalogo_CIE10_ehCOS.csv"
    output_directory = "catalog_documents"
    
    print(f"Splitting '{input_csv}' into individual documents...")
    split_csv_to_documents(input_csv, output_directory)
