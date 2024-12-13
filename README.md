# Artifact Appendix
### Abstract
This artifact contains the code and script to generate compression-ratio and throughput results for the 4 algorithms the paper introduces. The results should be similar to the numbers shown in Figures 8 through 19 for SPratio, SPspeed, DPratio, and DPspeed, that is, the compression ratios should match exactly but the compression and decompression throughputs are system dependent.

### Artifact check-list (meta-information)
  - Algorithm: SPratio, SPspeed, DPratio, and DPspeed
  - Compilation: g++ and nvcc
  - Data set: SDRBench
  - Hardware: CPU and GPU
  - Execution: Parallel
  - Metrics: Compression ratio and throughput
  - Output: Compression ratio vs. throughput scatter plots
  - How much disk space required (approximately)?: 100 GB
  - How much time is needed to prepare workflow (approximately)?: 180 minutes to download inputs
  - How much time is needed to complete experiments (approximately)?: 100 minutes for the GPU and 200 minutes for the CPU
  - Publicly available?: Yes
  - Code licenses (if publicly available)?: BSD 3-Clause License
  - Workflow automation framework used?: Python scripts
  - Archived (provide DOI)?: https://doi.org/10.5281/zenodo.14061031


### Description
###### How to access
The artifact can be found at https://github.com/burtscher/FPcompress.

###### Hardware dependencies
The hardware required for this artifact is an x86 multi-core CPU and a CUDA-capable GPU. We used a 32-core Intel Xeon Gold 6226R CPU @ 2.9 GHz with hyperthreading enabled to run the CPU codes. To run the GPU codes, we used an NVIDIA RTX 4090. Using similar hardware should result in throughputs similar to those reported in the paper.

###### Software dependencies
The required software includes:
- The computational artifact from https://github.com/burtscher/FPcompress
- GCC 7.5.0 or higher
- OpenMP 3.1 or higher
- CUDA 11.0 or higher
- Python v3.4 or higher
- Matplotlib v3.6 or higher


###### Data sets
The data sets used in the artifact are downloaded as part of the installation process and can be found at https://sdrbench.github.io.

###### Installation
To install the artifact
- Clone the repository from https://github.com/burtscher/FPcompress
- Run './compile.py' to compile SPratio, SPspeed, DPratio, and DPspeed

> **Note:**  
> If you encounter an error related to missing dependencies, add the flag  `-lttb` at the very end of the compilation instructions in  `compile.py`

###### Experiment workflow
1. Clone the repository from https://github.com/burtscher/FPcompress
2. Run './get\_inputs\_double.py' and './get\_inputs\_single.py' to download and set up the inputs used by the artifact
3. Run './compile.py' to compile SPratio, SPspeed, DPratio, and DPspeed
4. Run './run\_experiments\_double.py' and './run\_experiments\_single.py' to produce the intermediate experimental results
5. Run './chart\_double.py' and './chart\_single.py' to generate compression and decompression charts that look like Figures 8 through 19 but without the results for the third-party codes.
6. View the charts, which can be found in the current directory under 'double_charts.png' and 'single_charts.png'

###### Evaluation and expected results

The evaluation of the results is accomplished by comparing the figures generated using this artifact to the SPratio, SPspeed, DPratio, and DPspeed results listed in Figures 8 through 19. The absolute values of the throughputs and the relative positions may be different based on the CPU and GPU used, but the compression ratios should be the same.

###### Methodology

Submission, reviewing and badging methodology:
- https://www.acm.org/publications/policies/artifact-review-and-badging-current
- https://cTuning.org/ae
