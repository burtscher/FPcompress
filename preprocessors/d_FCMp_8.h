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


#include <cub/cub.cuh>


static __device__ inline int d_hash12(const unsigned long long val)
{
  return (val >> 32) ^ val;
}


template <typename T>
__global__ void FCMp_8_kernel1(int size, const T* __restrict__ data_T, T* __restrict__ hash_pos)
{
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < size) {
    int idx = 0;
    if (i - 1 >= 0) idx ^= d_hash12(data_T[i - 1]);
    if (i - 2 >= 0) idx ^= d_hash12(data_T[i - 2]);
    if (i - 3 >= 0) idx ^= d_hash12(data_T[i - 3]);
    hash_pos[i] = ((T)idx << 32) | i;
  }
}


template <typename T>
__global__ void FCMp_8_kernel2(const int size, const T* __restrict__ data_T, const T* __restrict__ hash_pos, T* __restrict__ new_data)
{
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < size) {
    const T hp = hash_pos[i];
    const int pos = hp;
    const int hash = hp >> 32;
    T dist = 0;
    T val = data_T[pos];
    for (int j = 1; j <= 4; j++) {
      if (i - j >= 0) {
        const T hp = hash_pos[i - j];
        if (hash != (int)(hp >> 32)) break;
        const int prev_pos = hp;
        if (val == data_T[prev_pos]) {
          dist = pos - prev_pos;
          val = 0;
          break;
        }
      }
    }
    new_data[pos + size] = dist;
    new_data[pos] = val;
  }
}


template <typename T>
static __global__ void parallel_union_find(volatile T* __restrict__ data_T, const int s)
{
  const int i = blockIdx.x * TPB + threadIdx.x;
  if (i < s) {
    T dist = data_T[i + s];
    if (dist != 0) {
      int prev = i;
      int curr = i - dist;
      dist = data_T[curr + s];
      while (dist != 0) {
        const int next = curr - dist;
        dist = data_T[next + s];
        data_T[prev + s] = prev - next;
        prev = curr;
        curr = next;
      }
      data_T[i] = data_T[curr];
      __threadfence();  // ensure visibility of write before proceeding
      data_T[i + s] = 0;
    }
  }
}


template <typename T>
static void cubSortOnDevice(T* d_data, const int size)
{
  // Allocate temporary storage for sorting
  size_t temp_storage_bytes = 0;
  void* d_temp_storage = nullptr;
  cub::DeviceRadixSort::SortKeys(d_temp_storage, temp_storage_bytes, d_data, d_data, size);
  cudaMalloc(&d_temp_storage, temp_storage_bytes);

  // Perform sorting
  cub::DeviceRadixSort::SortKeys(d_temp_storage, temp_storage_bytes, d_data, d_data, size);

  // Free temporary storage
  cudaFree(d_temp_storage);
}


static inline void d_FCMp_8(long long& size, byte*& data, const int paramc, const double paramv [])
{
  using T = unsigned long long;

  if (size % sizeof(T) != 0) {fprintf(stderr, "d_FCMp_8: ERROR: size of input must be a multiple of %ld bytes\n", sizeof(T));  exit(-1);}

  const int s = size / sizeof(T);
  T* data_T;
  T* hash_pos;
  T* new_data;

  cudaMalloc((void**)&data_T, size);
  cudaMalloc((void**)&hash_pos, s * sizeof(T));
  cudaMalloc((void**)&new_data, 2 * s * sizeof(T));

  cudaMemcpy(data_T, data, size, cudaMemcpyHostToDevice);
  const int blocks = (s + TPB - 1) / TPB;

  FCMp_8_kernel1<<<blocks, TPB>>>(s, data_T, hash_pos);

  cubSortOnDevice(hash_pos, s);

  FCMp_8_kernel2<<<blocks, TPB>>>(s, data_T, hash_pos, new_data);

  data = (byte*)new_data;
  size *= 2;
}


static inline void d_iFCMp_8(long long& size, byte*& data, const int paramc, const double paramv [])
{
  using T = unsigned long long;

  if (size % (sizeof(T) * 2) != 0) {fprintf(stderr, "d_FCMp_8: ERROR: size of input must be a multiple of %ld bytes\n", sizeof(T) * 2); exit(-1);}

  const int s = size / (sizeof(T) * 2);
  T* const data_T = (T*)data;

  const int blocks = (s + TPB - 1) / TPB;
  parallel_union_find<<<blocks, TPB>>>(data_T, s);

  size /= 2;
}
