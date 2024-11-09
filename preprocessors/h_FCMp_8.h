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


#include <vector>
#include <algorithm>
#include <execution>


template <typename T>
static inline int hash12(T val)
{
  return (val >> 32) ^ val;
}


static inline void h_FCMp_8(long long& size, byte*& data, const int paramc, const double paramv [])
{
  using T = unsigned long long;
  if (size % sizeof(T) != 0) {fprintf(stderr, "h_FCMp_8: ERROR: size of input must be a multiple of %ld bytes\n", sizeof(T)); throw std::runtime_error("LC error");}

  const int s = size / sizeof(T);
  T* const data_T = (T*)data;

  T* const hash_pos = new T [s];
  T* const new_data = new T [2 * s];

  // embarrassingly parallel
  #pragma omp parallel for default(none) shared(s, data_T, hash_pos)
  for (int i = 0; i < s; i++) {
    int idx = 0;
    if (i - 1 >= 0) idx ^= hash12(data_T[i - 1]);
    if (i - 2 >= 0) idx ^= hash12(data_T[i - 2]);
    if (i - 3 >= 0) idx ^= hash12(data_T[i - 3]);
    hash_pos[i] = ((T)idx << 32) | i;
  }

  // parallel sort
  std::sort(std::execution::par_unseq, hash_pos, hash_pos + s);

  // embarrassingly parallel
  #pragma omp parallel for default(none) shared(s, data_T, hash_pos, new_data)
  for (int i = 0; i < s; i++) {
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
    new_data[pos + s] = dist;
    new_data[pos] = val;
  }

//  delete [] hash_pos;
//  delete [] data;
  data = (byte*)new_data;
  size *= 2;
}


static inline void h_iFCMp_8(long long& size, byte*& data, const int paramc, const double paramv [])
{
  using T = unsigned long long;
  if (size % (sizeof(T) * 2) != 0) {fprintf(stderr, "h_FCMp_8: ERROR: size of input must be a multiple of %ld bytes\n", sizeof(T) * 2); throw std::runtime_error("LC error");}

  const int s = size / (sizeof(T) * 2);
  T* const data_T = (T*)data;

  // parallel "union-find"
  #pragma omp parallel for default(none) shared(s, data_T) //schedule(static, 1)
  for (int i = 0; i < s; i++) {
    T dist, val;
    #pragma omp atomic read
    dist = data_T[i + s];
    if (dist != 0) {
      int prev = i;
      int curr = i - dist;
      #pragma omp atomic read
      dist = data_T[curr + s];
      while (dist != 0) {
        int next = curr - dist;
        #pragma omp atomic read
        dist = data_T[next + s];
        #pragma omp atomic write
        data_T[prev + s] = prev - next;
        prev = curr;
        curr = next;
      }
      #pragma omp atomic read
      val = data_T[curr];
      #pragma omp atomic write
      data_T[i] = val;
      #pragma omp flush
      #pragma omp atomic write
      data_T[i + s] = 0;
    }
  }

  size /= 2;
}
