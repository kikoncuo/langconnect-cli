#!/usr/bin/env python3
"""
Script to upload all documents from catalog_documents/ to the cie-10-ar collection.
"""

import asyncio
import os
import glob
from pathlib import Path

from langconnect_cli.client import LangConnectClient


async def upload_documents_batch():
    """Upload all documents in batches to avoid overwhelming the API."""
    
    # Collection UUID from the create-collection command
    collection_id = "706b5ed3-670f-4e58-95a5-35e3eb33351d"
    
    # Get all document files
    doc_files = sorted(glob.glob("catalog_documents/document_*.txt"))
    
    print(f"Found {len(doc_files)} documents to upload")
    print(f"Uploading to collection: {collection_id}")
    
    # Initialize client
    client = LangConnectClient()
    
    # Upload in batches of 50 files (adjust as needed)
    batch_size = 50
    total_batches = (len(doc_files) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(doc_files))
        batch_files = doc_files[start_idx:end_idx]
        
        print(f"Uploading batch {batch_num + 1}/{total_batches} (files {start_idx + 1}-{end_idx})")
        
        try:
            # Upload this batch
            result = await client.upload_documents(
                collection_id=collection_id,
                files=batch_files,
                chunk_size=1000,
                chunk_overlap=200
            )
            
            if result:
                print(f"✓ Batch {batch_num + 1} uploaded successfully")
            else:
                print(f"✗ Batch {batch_num + 1} failed to upload")
                
        except Exception as e:
            print(f"✗ Error uploading batch {batch_num + 1}: {e}")
        
        # Small delay between batches to be gentle on the API
        await asyncio.sleep(1)
    
    print("Upload process completed!")


if __name__ == "__main__":
    asyncio.run(upload_documents_batch())
