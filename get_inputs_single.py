#!/usr/bin/python3 -u

import requests
import re
from urllib.parse import urljoin
import os
import time
import shutil
import tarfile
import subprocess


def unzip_files(directory="."):
    for filename in os.listdir(directory):
        if filename.endswith(".tar.gz"):
            print("Extracting", filename)
            # Using subprocess to run the tar command
            subprocess.run(["tar", "-xvzf", os.path.join(directory, filename), "-C", directory])
            print("Extracted", filename)

def get_links_from_page(url):
    # Send a GET request to the URL
    response = requests.get(url)
    
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Use regular expressions to find all links in the HTML content
        links = re.findall(r'href=[\'"]?([^\'" >]+)', response.text)
        
        # Extract the absolute URLs from the found links
        extracted_links = [urljoin(url, link) for link in links]
        
        return extracted_links
    else:
        print("Failed to fetch page. Status code:", response.status_code)
        return []

def download_file(url, directory="."):
    # Extract filename from URL
    filename = url.split("/")[-1]
    
    # Download the file
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(os.path.join(directory, filename), 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def delete_files_with_word(directory, word):
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if word in filename:
                filepath = os.path.join(root, filename)
                try:
                       os.remove(filepath)
                       print("Deleted", filepath)
                except Exception as e:
                       print(f"Error deleting {filepath}: {e}")



def delete_gz_files(directory):
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".gz"):
                filepath = os.path.join(root, filename)
                try:
                    os.remove(filepath)
                    print("Deleted", filepath)
                except Exception as e:
                    print(f"Error deleting {filepath}: {e}")

# Timing the script
start_time = time.time()

# Example usage:
url = "https://sdrbench.github.io/"
keywords = ["SDRBENCH-CESM-ATM-26x1800x3600.tar",
            "SDRBENCH-Hurricane-ISABEL-100x500x500.tar",
            "SDRBENCH-EXASKY-NYX-512x512x512.tar",
            "SDRBENCH-QMCPack.tar",
            "SDRBENCH-SCALE-98x1200x1200.tar",
            "SDRBENCH-exaalt-copper.tar",
            "SDRBENCH-exaalt-helium.tar",
            "EXASKY-HACC-data-medium-size.tar",
            "SDRBENCH-EXAALT-2869440.tar"]

links = get_links_from_page(url)
print("Links found on the page:")
for link in links:
    if link.endswith('.gz'):
        for keyword in keywords:
            if keyword in link:
                print("Downloading", link)
                download_file(link)
                print("Downloaded", link)
                break  # Break the inner loop to avoid downloading the same file multiple times if it matches multiple keywords

# Create a folder named "single_inputs" and move all downloaded files into it
if not os.path.exists("single_inputs"):
    os.makedirs("single_inputs")
for filename in os.listdir("."):
    if filename.endswith(".gz"):
        shutil.move(filename, os.path.join("single_inputs", filename))

# Unzip all .tar.gz files in the "single_inputs" folder
unzip_files("single_inputs")

delete_gz_files("single_inputs")

# Delete files from "single_inputs" folder that contain the word "log" and have the .txt extension
delete_files_with_word("single_inputs", "log")
delete_files_with_word("single_inputs", ".txt")

# Move the dataset files so the next script can see them
os.system("mv single_inputs/dataset/*/* single_inputs/dataset/")

# Calculate execution time
execution_time = time.time() - start_time
print("Script execution time:", execution_time, "seconds")

    
