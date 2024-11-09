#!/usr/bin/env python3

import os
import subprocess
import statistics
import math
import sys

# Check if the correct number of command-line arguments are provided
if len(sys.argv) != 4:
    print("Usage: python script.py <input_directory> <executable_directory> <executable_file>")
    sys.exit(1)

# Extract the command-line arguments
inputs_dir = sys.argv[1]
exe_dir = sys.argv[2]
exe_file = sys.argv[3]


# Create a list to store geometric mean of median throughputs and ratios for all subfolders
exe_median_throughputs = []

for input_folder in os.listdir(inputs_dir):
    input_folder_path = os.path.join(inputs_dir, input_folder)
    if not os.path.isdir(input_folder_path):
        continue

    median_throughputs = []
    compressed_folder_path = os.path.join(input_folder_path, "compressed")
    # Create the "decompressed" folder within the subfolder of "single_inputs"
    decompressed_folder_path = os.path.join(input_folder_path, "decompressed")
    os.makedirs(decompressed_folder_path, exist_ok=True)
    
    print(f"Running {exe_file} on files in folder: {input_folder}")
    
    input_files = [f for f in os.listdir(compressed_folder_path) if os.path.isfile(os.path.join(compressed_folder_path, f))]
    for input_file in input_files:
        input_file_path = os.path.join(compressed_folder_path, input_file)
        output_file_name = os.path.join(decompressed_folder_path, os.path.splitext(input_file)[0] + ".decomp")
        
        print(f"Processing {input_file}")
        
        # Run the exe file with the input file and output file name five times
        throughput_list = []
        for i in range(3):
            print(f"Processing file {input_file} run {i+1}")
            command = [os.path.join(exe_dir, exe_file), input_file_path, output_file_name, "y"]
            try:
                result = subprocess.run(command, capture_output=True, text=True, check=True)
                output = result.stdout
                lines = output.split('\n')
                for line in lines:
                    if "decoding throughput:" in line:
                        throughput = float(line.split()[2])
                        throughput_list.append(throughput)
            except subprocess.CalledProcessError as e:
                print(f"Error running {exe_file} for {input_file}: {e}")
                # Handle the error as required
        
        # Calculate median throughput and ratio for the current input file and exe combination
        median_throughput = statistics.median(throughput_list)
        
        median_throughputs.append(median_throughput)
        
        print(f"Median throughput for {exe_file} on {input_file}: {median_throughput}")
        # The Kleene star is a hack that I think works for this small set. Is probably not universalizable
        os.system("if diff " + compressed_folder_path + "/../" + input_file_path.split('/')[-1].replace(".comp", "*") + " " + output_file_name + " > /dev/null; then echo \"Lossless comparison passed\"; else echo \"Lossless comparison failed\"; fi")

    # Calculate geometric mean of median throughputs and median ratios for this subfolder
    geometric_mean_throughput = math.exp(statistics.mean(math.log(x) for x in median_throughputs))
    
    exe_median_throughputs.append(geometric_mean_throughput)

# Calculate overall geometric mean of median throughputs and ratios for all subfolders
overall_geometric_mean_throughput = math.exp(statistics.mean(math.log(x) for x in exe_median_throughputs))

# Write overall geometric mean of median throughputs and ratios to a text file
output_file_path = os.path.join(inputs_dir, f"{exe_file}_metrics.txt")
with open(output_file_path, "w") as f:
    f.write(f"Geometric mean of median throughputs for {exe_file}:\n")
    for i, median_throughput in enumerate(exe_median_throughputs):
        f.write(f"  Subfolder {i+1}: {median_throughput}\n")
    f.write(f"Overall geometric mean: {overall_geometric_mean_throughput}\n")

