/*
This file is part of the LC framework for synthesizing high-speed parallel lossless and error-bounded lossy data compression and decompression algorithms for CPUs and GPUs.

BSD 3-Clause License

Copyright (c) 2021-2024, Noushin Azami, Alex Fallin, Brandon Burtchell, Andrew Rodriguez, Benila Jerald, Yiqian Liu, and Martin Burtscher
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

URL: The latest version of this code is available at https://github.com/burtscher/LC-framework.

Sponsor: This code is based upon work supported by the U.S. Department of Energy, Office of Science, Office of Advanced Scientific Research (ASCR), under contract DE-SC0022223.
*/

#define NDEBUG

using byte = unsigned char;
static const int CS = 1024 * 16;  // chunk size (in bytes) [must be multiple of 8]
static const int TPB = 512;  // threads per block [must be power of 2 and at least 128]
#define WS 32

#include <string>
#include <cmath>
#include <cassert>
#include <cuda.h>
#include "../include/sum_reduction.h"
#include "../include/max_scan.h"
#include "../include/prefix_sum.h"
#include "../components/d_DIFFMS_8.h"
#include "../components/d_HCLOG_8.h"


// copy (len) bytes from shared memory (source) to global memory (destination)
// source must we word aligned
static inline __device__ void s2g(void* const __restrict__ destination, const void* const __restrict__ source, const int len)
{
  const int tid = threadIdx.x;
  const byte* const __restrict__ input = (byte*)source;
  byte* const __restrict__ output = (byte*)destination;
  if (len < 128) {
    if (tid < len) output[tid] = input[tid];
  } else {
    const int nonaligned = (int)(size_t)output;
    const int wordaligned = (nonaligned + 3) & ~3;
    const int linealigned = (nonaligned + 127) & ~127;
    const int bcnt = wordaligned - nonaligned;
    const int wcnt = (linealigned - wordaligned) / 4;
    const int* const __restrict__ in_w = (int*)input;
    if (bcnt == 0) {
      int* const __restrict__ out_w = (int*)output;
      if (tid < wcnt) out_w[tid] = in_w[tid];
      for (int i = tid + wcnt; i < len / 4; i += TPB) {
        out_w[i] = in_w[i];
      }
      if (tid < (len & 3)) {
        const int i = len - 1 - tid;
        output[i] = input[i];
      }
    } else {
      const int shift = bcnt * 8;
      const int rlen = len - bcnt;
      int* const __restrict__ out_w = (int*)&output[bcnt];
      if (tid < bcnt) output[tid] = input[tid];
      if (tid < wcnt) out_w[tid] = __funnelshift_r(in_w[tid], in_w[tid + 1], shift);
      for (int i = tid + wcnt; i < rlen / 4; i += TPB) {
        out_w[i] = __funnelshift_r(in_w[i], in_w[i + 1], shift);
      }
      if (tid < (rlen & 3)) {
        const int i = len - 1 - tid;
        output[i] = input[i];
      }
    }
  }
}


static __device__ int g_chunk_counter;


static __global__ void d_reset()
{
  g_chunk_counter = 0;
}


static inline __device__ void propagate_carry(const int value, const int chunkID, volatile int* const __restrict__ fullcarry, int* const __restrict__ s_fullc)
{
  if (chunkID == 0) {
    if (threadIdx.x == WS) {
      fullcarry[0] = value;
    }
  } else {
    if (threadIdx.x == WS) {
      fullcarry[chunkID] = -value;
    }

    if (threadIdx.x + WS >= TPB) {  // last warp
      const int lane = threadIdx.x % WS;
      const int cidm1ml = chunkID - 1 - lane;
      int val = -1;
      __syncwarp();  // optional
      do {
        if (cidm1ml >= 0) {
          val = fullcarry[cidm1ml];
        }
      } while ((__any_sync(~0, val == 0)) || (__all_sync(~0, val <= 0)));
      const int mask = __ballot_sync(~0, val > 0);
      const int pos = __ffs(mask) - 1;
      int partc = (lane < pos) ? -val : 0;
      partc = __reduce_add_sync(~0, partc);
/*
      partc += __shfl_xor_sync(~0, partc, 1);  // MB: use reduction on 8.6 devices
      partc += __shfl_xor_sync(~0, partc, 2);
      partc += __shfl_xor_sync(~0, partc, 4);
      partc += __shfl_xor_sync(~0, partc, 8);
      partc += __shfl_xor_sync(~0, partc, 16);
*/
      if (lane == pos) {
        const int fullc = partc + val;
        fullcarry[chunkID] = fullc + value;
        *s_fullc = fullc;
      }
    }
  }
}


static __global__ __launch_bounds__(TPB, 4)
void d_encode(const byte* const __restrict__ input, const int insize, byte* const __restrict__ output, int* const __restrict__ outsize, int* const __restrict__ fullcarry)
{
  // allocate shared memory buffer
  __shared__ long long chunk [2 * (CS / sizeof(long long)) + 4 + 17];
  const int last = 2 * (CS / sizeof(long long)) + WS;

  // create the 3 shared memory buffers
  byte* const in = (byte*)&chunk[0 * (CS / sizeof(long long))];
  byte* const out = (byte*)&chunk[1 * (CS / sizeof(long long))];
  byte* const temp = (byte*)&chunk[2 * (CS / sizeof(long long))];
  long long* const out_l = (long long*)out;

  // initialize
  const int chunks = (insize + CS - 1) / CS;  // round up
  int* const head_out = (int*)output;
  unsigned short* const size_out = (unsigned short*)&head_out[1];
  byte* const data_out = (byte*)&size_out[chunks];

  // loop over chunks
  const int tid = threadIdx.x;
  do {
    // assign work dynamically
    if (tid == WS) chunk[last] = atomicAdd(&g_chunk_counter, 1);
    __syncthreads();  // chunk[last] produced, chunk consumed

    // terminate if done
    const int chunkID = chunk[last];
    const int base = chunkID * CS;
    if (base >= insize) break;

    // load chunk
    const int osize = min(CS, insize - base);
    long long* const input_l = (long long*)&input[base];
    for (int i = tid; i < osize / 8; i += TPB) {
      out_l[i] = input_l[i];
    }
    const int extra = osize % 8;
    if (tid < extra) out[osize - extra + tid] = input[base + osize - extra + tid];
    __syncthreads();  // chunk produced, chunk[last] consumed

    // encode chunk
    int csize = osize;
    d_DIFFMS_8(csize, out, in, temp);
    __syncthreads();
    const bool good = d_HCLOG_8(csize, in, out, temp);

    // handle carry
    if (!good || (csize > osize)) csize = osize;
    propagate_carry(csize, chunkID, fullcarry, (int*)temp);

    // store chunk
    if (tid == 2 * WS) size_out[chunkID] = csize;
    if (csize == osize) {
      __syncthreads();

      // store original data
      for (int i = tid; i < osize / 8; i += TPB) {
        out_l[i] = input_l[i];
      }
      const int extra = osize % 8;
      if (tid < extra) out[osize - extra + tid] = input[base + osize - extra + tid];
    }
    __syncthreads();  // temp (and fullcarry) written

    const int offs = (chunkID == 0) ? 0 : *((int*)temp);
    s2g(&data_out[offs], out, csize);

    // finalize if last chunk
    if ((tid == 0) && (base + CS >= insize)) {
      // output header
      head_out[0] = insize;
      // compute compressed size
      *outsize = &data_out[fullcarry[chunks - 1]] - output;
    }
  } while (true);
}


struct GPUTimer
{
  cudaEvent_t beg, end;
  GPUTimer() {cudaEventCreate(&beg);  cudaEventCreate(&end);}
  ~GPUTimer() {cudaEventDestroy(beg);  cudaEventDestroy(end);}
  void start() {cudaEventRecord(beg, 0);}
  double stop() {cudaEventRecord(end, 0);  cudaEventSynchronize(end);  float ms;  cudaEventElapsedTime(&ms, beg, end);  return 0.001 * ms;}
};


static void CheckCuda(const int line)
{
  cudaError_t e;
  cudaDeviceSynchronize();
  if (cudaSuccess != (e = cudaGetLastError())) {
    fprintf(stderr, "CUDA error %d on line %d: %s\n", e, line, cudaGetErrorString(e));
    exit(-1);
  }
}


int main(int argc, char* argv [])
{
  printf("GPU LC 1.1 Algorithm: DIFFMS_4 HCLOG_4\n");
  printf("Copyright 2024 Texas State University\n\n");

  // read input from file
  if (argc < 3) {printf("USAGE: %s input_file_name compressed_file_name [performance_analysis (y)]\n\n", argv[0]);  exit(-1);}
  FILE* const fin = fopen(argv[1], "rb");
  fseek(fin, 0, SEEK_END);
  const int fsize = ftell(fin);  assert(fsize > 0);
  byte* const input = new byte [fsize];
  fseek(fin, 0, SEEK_SET);
  const int insize = fread(input, 1, fsize, fin);  assert(insize == fsize);
  fclose(fin);
  printf("original size: %d bytes\n", insize);

  // Check if the third argument is "y" to enable performance analysis
  char* perf_str = argv[3];
  bool perf = false;
  if (perf_str != nullptr && strcmp(perf_str, "y") == 0) {
    perf = true;
  } else if (perf_str != nullptr && strcmp(perf_str, "y") != 0) {
    printf("Invalid performance analysis argument. Use 'y' or leave it empty.\n");
    exit(-1);
  }

  // get GPU info
  cudaSetDevice(0);
  cudaDeviceProp deviceProp;
  cudaGetDeviceProperties(&deviceProp, 0);
  if ((deviceProp.major == 9999) && (deviceProp.minor == 9999)) {fprintf(stderr, "ERROR: no CUDA capable device detected\n\n"); exit(-1);}
  const int SMs = deviceProp.multiProcessorCount;
  const int mTpSM = deviceProp.maxThreadsPerMultiProcessor;
  const int blocks = SMs * (mTpSM / TPB);
  const int chunks = (insize + CS - 1) / CS;  // round up
  CheckCuda(__LINE__);
  const int maxsize = sizeof(int) + chunks * sizeof(short) + chunks * CS;

  // allocate GPU memory
  byte* dencoded;
  cudaMallocHost((void **)&dencoded, maxsize);
  byte* d_input;
  cudaMalloc((void **)&d_input, insize);
  cudaMemcpy(d_input, input, insize, cudaMemcpyHostToDevice);
  byte* d_encoded;
  cudaMalloc((void **)&d_encoded, maxsize);
  int* d_encsize;
  cudaMalloc((void **)&d_encsize, sizeof(int));
  CheckCuda(__LINE__);

  byte* dpreencdata;
  cudaMalloc((void **)&dpreencdata, insize);
  cudaMemcpy(dpreencdata, d_input, insize, cudaMemcpyDeviceToDevice);
  int dpreencsize = insize;
/*
  if (perf) {
    // warm up
    int* d_fullcarry_dummy;
    cudaMalloc((void **)&d_fullcarry_dummy, chunks * sizeof(int));
    d_reset<<<1, 1>>>();
    cudaMemset(d_fullcarry_dummy, 0, chunks * sizeof(int));
    d_encode<<<blocks, TPB>>>(dpreencdata, dpreencsize, d_encoded, d_encsize, d_fullcarry_dummy);
    cudaFree(d_fullcarry_dummy);
  }
*/
  GPUTimer dtimer;
  dtimer.start();
  d_reset<<<1, 1>>>();
  int* d_fullcarry;
  cudaMalloc((void **)&d_fullcarry, chunks * sizeof(int));
  cudaMemset(d_fullcarry, 0, chunks * sizeof(int));
  d_encode<<<blocks, TPB>>>(dpreencdata, dpreencsize, d_encoded, d_encsize, d_fullcarry);
  cudaFree(d_fullcarry);
  double runtime = dtimer.stop();

  // get encoded GPU result
  int dencsize = 0;
  cudaMemcpy(&dencsize, d_encsize, sizeof(int), cudaMemcpyDeviceToHost);
  cudaMemcpy(dencoded, d_encoded, dencsize, cudaMemcpyDeviceToHost);
  printf("encoded size: %d bytes\n", dencsize);
  CheckCuda(__LINE__);

  const float CR = (100.0 * dencsize) / insize;
  printf("ratio: %6.2f%% %7.3fx\n", CR, 100.0 / CR);

  if (perf) {
    printf("encoding time: %.6f s\n", runtime);
    double throughput = insize * 0.000000001 / runtime;
    printf("encoding throughput: %8.3f Gbytes/s\n", throughput);
    CheckCuda(__LINE__);
  }

  // write to file
  FILE* const fout = fopen(argv[2], "wb");
  fwrite(dencoded, 1, dencsize, fout);
  fclose(fout);

  // clean up GPU memory
  cudaFree(d_input);
  cudaFree(d_encoded);
  cudaFree(d_encsize);
  cudaFree(dpreencdata);
  CheckCuda(__LINE__);

  // clean up
  delete [] input;
  cudaFreeHost(dencoded);
  return 0;
}
