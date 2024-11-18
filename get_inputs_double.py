#!/usr/bin/env python3

import http.client
import ssl
import re
import shutil
import os
import subprocess
from urllib.parse import urlparse

# Replace 'url' with the URL you want to scrape
url = "https://userweb.cs.txstate.edu/~burtscher/research/datasets/FPdouble/"

# Parse the URL to extract the host and path
parsed_url = urlparse(url)
host = parsed_url.netloc
path = parsed_url.path if parsed_url.path else '/'

# Set up SSL context to skip certificate verification
context = ssl._create_unverified_context()

# Initialize a connection to the host with the custom context
connection = http.client.HTTPSConnection(host, context=context)
connection.request("GET", path)

# Get the response
response = connection.getresponse()

if response.status == 200:
    # Read the response content
    html_content = response.read().decode("utf-8")

    # Regular expression to find all href attributes in anchor tags
    links = re.findall(r'href=["\'](.*?)["\']', html_content)

    # Make sure we have enough links
    if len(links) >= 14:
        # Select the first 13 links, excluding the last one
        download_links = links[-14:-1]
        
        # Create the folder if it doesn't exist
        os.makedirs("double_inputs", exist_ok=True)
        
        print("Downloading the 13 links before the last one:")
        for link in download_links:
            # Convert relative links to absolute if necessary
            if link.startswith('/'):
                link = f"https://{host}{link}"
            elif not link.startswith('http'):
                link = f"https://{host}/{link}"

            # Use wget to download the file, ignoring SSL certificate errors
            print(f"Downloading {link}...")
            subprocess.run(["wget", "--no-check-certificate", "-P", "double_inputs", link])

        # Compile the C program using gcc
        print("Compiling fpc.c with gcc...")
        subprocess.run(["gcc", "-O3", "fpc.c", "-o", "fpc"])

        # Run the fpc program on the downloaded files inside the 'double_inputs' folder
        for file in os.listdir("double_inputs"):
            if file.endswith(".fpc"):
                input_file = os.path.join("double_inputs", file)
                output_file = os.path.splitext(file)[0] + ".dp"
                output_file_path = os.path.join("double_inputs", output_file)

                # Run ./fpc on the input file, redirect output to a .dp file
                #print(input_file, output_file_path)
                #print(f"Running ./fpc on {file}...")
                # Run ./fpc with redirection using shell=True
                command = f"./fpc < {input_file} > {output_file_path}"
                print(f"Running command: {command}")
                subprocess.run(command, shell=True)
                #subprocess.run(["./fpc", "<", input_file, ">", output_file_path], shell=True)

    else:
        print("Not enough links found to download 13 links before the last one.")
else:
    print(f"Failed to retrieve the page. Status code: {response.status}")

# Close the connection
connection.close()

# Delete all .fpc files in the 'double_inputs' folder
for file in os.listdir("double_inputs"):
    if file.endswith(".fpc"):
        os.remove(os.path.join("double_inputs", file))
        print(f"Deleted {file}")
# Define the paths for the new folders
obs_folder = "double_inputs/obs"
msg_folder = "double_inputs/msg"
num_folder = "double_inputs/num"

# Create the new folders if they don't exist
os.makedirs(obs_folder, exist_ok=True)
os.makedirs(msg_folder, exist_ok=True)
os.makedirs(num_folder, exist_ok=True)

# Define the files to move based on their names
obs_files = ["obs_info.trace.dp", "obs_error.trace.dp", "obs_spitzer.trace.dp", "obs_temp.trace.dp"]
msg_files = ["msg_sp.trace.dp", "msg_sppm.trace.dp", "msg_bt.trace.dp", "msg_sweep3d.trace.dp", "msg_lu.trace.dp"]
num_files = ["num_comet.trace.dp", "num_plasma.trace.dp", "num_brain.trace.dp", "num_control.trace.dp"]

# Move the files to the 'obs' folder
for file in os.listdir("double_inputs"):
    if file in obs_files:
        src = os.path.join("double_inputs", file)
        dst = os.path.join(obs_folder, file)
        shutil.move(src, dst)
        print(f"Moved {file} to {obs_folder}")

# Move the files to the 'msg' folder
for file in os.listdir("double_inputs"):
    if file in msg_files:
        src = os.path.join("double_inputs", file)
        dst = os.path.join(msg_folder, file)
        shutil.move(src, dst)
        print(f"Moved {file} to {msg_folder}")

# Move the files to the 'num' folder
for file in os.listdir("double_inputs"):
    if file in num_files:
        src = os.path.join("double_inputs", file)
        dst = os.path.join(num_folder, file)
        shutil.move(src, dst)
        print(f"Moved {file} to {num_folder}")


# Define the URL and the file path
url = "https://g-8d6b0.fd635.8443.data.globus.org/ds131.2/Data-Reduction-Repo/raw-data/Miranda/SDRBENCH-Miranda-256x384x384.tar.gz"
compressed_file_path = "SDRBENCH-Miranda-256x384x384.tar.gz"
extracted_folder_name = "SDRBENCH-Miranda-256x384x384"  # This is typically the folder extracted from the tar.gz file
destination_folder = "double_inputs"

# Download the file using wget
print("Downloading the compressed file using wget...")
subprocess.run(["wget", url, "-O", compressed_file_path], check=True)
print(f"Downloaded {compressed_file_path}")

# Uncompress the tar.gz file using the tar command
print("Uncompressing the file using tar...")
subprocess.run(["tar", "-xzvf", compressed_file_path], check=True)
print(f"Extracted {extracted_folder_name}")

# Move the extracted folder to double_inputs
print(f"Moving the extracted folder {extracted_folder_name} to {destination_folder}...")
shutil.move(extracted_folder_name, os.path.join(destination_folder, extracted_folder_name))

# Delete the compressed file
print(f"Deleting the compressed file {compressed_file_path}...")
os.remove(compressed_file_path)
print(f"Deleted {compressed_file_path}")


