#!/usr/bin/python3 -u

import os
import shutil

# Define the base directory
base_directory = "double_inputs"

# Define the source directory containing the files
source_directory = os.path.join(base_directory, "SDRBENCH-Miranda-256x384x384")

# Define the new folder path in the base directory
new_folder = os.path.join(base_directory, "vel")

# Create the new folder if it doesn't exist
os.makedirs(new_folder, exist_ok=True)

# List of files to move
files_to_move = ["velocityx.d64", "velocityy.d64", "velocityz.d64", "viscocity.d64"]

# Move each file to the new folder
for file_name in files_to_move:
  source_path = os.path.join(source_directory, file_name)
  destination_path = os.path.join(new_folder, file_name)
  if os.path.exists(source_path):
    shutil.move(source_path, destination_path)

