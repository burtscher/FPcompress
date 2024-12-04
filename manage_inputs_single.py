#!/usr/bin/python3 -u

import os
import shutil

# Define the base directory
base_dir = "single_inputs"

# Move all files from specified folders into the new 'exaalt' folder
folders_to_move = [
    "SDRBENCH-exaalt-copper",
    "SDRBENCH-exaalt-helium",
    "2869440"
]
exaalt_folder = os.path.join(base_dir, "exaalt")
os.makedirs(exaalt_folder, exist_ok=True)

for folder in folders_to_move:
    folder_path = os.path.join(base_dir, folder)
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                shutil.move(os.path.join(root, file), os.path.join(exaalt_folder, file))

# Delete the three folders
for folder in folders_to_move:
    folder_path = os.path.join(base_dir, folder)
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        shutil.rmtree(folder_path)

