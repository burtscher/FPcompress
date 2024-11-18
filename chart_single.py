#!/usr/bin/python3 -u

import os
import re
import matplotlib.pyplot as plt

def combine_text_files(directory):
    # Specify the directory containing the text files
    input_directory = os.path.join(os.getcwd(), directory)

    # Check if the directory exists
    if not os.path.exists(input_directory):
        print(f"Directory '{directory}' does not exist.")
        return

    # Initialize an empty string to store the combined content
    combined_content = ""

    # Iterate over all files in the directory
    for filename in os.listdir(input_directory):
        # Check if the file is a text file
        if filename.endswith(".txt"):
            filepath = os.path.join(input_directory, filename)
            # Open and read the content of the text file
            with open(filepath, "r") as file:
                file_content = file.read()
                # Append the content to the combined content string
                combined_content += file_content + "\n"  # Add a newline between each file's content

    # Write the combined content to a new file
    output_file = os.path.join("combined-single.txt")
    with open(output_file, "w") as combined_file:
        combined_file.write(combined_content)

    print(f"Combined content has been saved to '{output_file}'.")


# Read the text file
combine_text_files("single_inputs")

with open('combined-single.txt', 'r') as file:
    code_block = file.read()

# Regular expression to match multiple occurrences of the pattern
pattern = r"Geometric mean of median throughputs for ([\w\-\.]+):.*?Overall geometric mean:\s*([\d\.]+)"
ratio = r"Geometric mean of median ratios for ([\w\-\.]+):.*?Overall geometric mean:\s*([\d\.]+)"

# Find all matches in the code block
matches = re.findall(pattern, code_block, re.DOTALL)
ratio_matches = re.findall(ratio, code_block, re.DOTALL)

# Store the results in a list of pairs (filename, overall mean)
throughputs = [(file_name, float(overall_mean)) for file_name, overall_mean in matches]
ratios = [(file_name, float(overall_mean)) for file_name, overall_mean in ratio_matches]

decompression_ratios = [(entry[0].replace("compress", "decompress"), entry[1]) for entry in ratios]

# Combine both lists
ratios += decompression_ratios
#print(new_ratios)
dict1 = dict(ratios)
dict2 = dict(throughputs)

# Create a new list with matched entries
combined_list = [(name, (dict2[name], dict1[name])) for name in dict1 if name in dict2]
combined_dict = dict(combined_list)
#print(combined_list)
# Organize data for each chart category
chart_data = {
    'CPU Compress': {'SPratio': combined_dict['ratio-cpu-compress.exe'], 'SPspeed': combined_dict['speed-cpu-compress.exe']},
    'CPU Decompress': {'SPratio': combined_dict['ratio-cpu-decompress.exe'], 'SPspeed': combined_dict['speed-cpu-decompress.exe']},
    'GPU Compress': {'SPratio': combined_dict['ratio-gpu-compress.exe'], 'SPspeed': combined_dict['speed-gpu-compress.exe']},
    'GPU Decompress': {'SPratio': combined_dict['ratio-gpu-decompress.exe'], 'SPspeed': combined_dict['speed-gpu-decompress.exe']}
}

# Plotting each chart
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle("Compression and Decompression Throughput and Ratios")

# Mapping of chart titles to subplot positions
titles = ['CPU Compress', 'CPU Decompress', 'GPU Compress', 'GPU Decompress']
for i, ax in enumerate(axes.flat):
    title = titles[i]
    data = chart_data[title]
    
    # Plot points
    for label, (x, y) in data.items():
        ax.scatter(float(x), float(y), label=label, s=100)
    
    # Chart aesthetics
    ax.set_title(title)
    ax.set_xlabel("Throughput (GB/s)")
    ax.set_ylabel("Compression Ratio")
    ax.legend()
    ax.grid(True)

# Save the plot as a PNG file
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig("single_charts.png")
plt.show()
print("Chart saved to 'single_charts.png'")
