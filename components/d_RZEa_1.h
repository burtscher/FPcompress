#include "include/d_zero_elimination.h"
#include "include/d_repetition_elimination.h"


static __device__ inline bool d_RZE_1(int& csize, byte in [CS], byte out [CS], byte temp [CS])
{
  using type = byte;
  const int tid = threadIdx.x;
  const int size = csize / sizeof(type);  // words in chunk (rounded down)
  const int extra = csize % sizeof(type);
  const int avail = CS - 2 - extra;
  const int bits = 8 * sizeof(type);
  assert(CS == 16384);

  // zero out bitmap
  int* const temp_w = (int*)temp;
  byte* const bitmap = (byte*)&temp_w[WS + 1];
  if (csize < CS) {
    for (int i = csize / bits + tid; i < CS / bits; i += TPB) {
      bitmap[i] = 0;
    }
    __syncthreads();
  }

  // copy non-zero values and generate bitmap
  int wpos = 0;
  if (size > 0) d_ZEencode((type*)in, size, (type*)out, wpos, (type*)bitmap, temp_w);
  wpos *= sizeof(type);
  if (wpos >= avail) return false;
  __syncthreads();

  // check if not all zeros
  if (wpos != 0) {
    // iteratively compress bitmaps
    int base = 0 / sizeof(type);
    int range = 2048 / sizeof(type);
    int cnt = avail - wpos;
    if (!d_REencode<byte, 2048 / sizeof(type), true>(&bitmap[base], range, &out[wpos], cnt, &bitmap[base + range], temp_w)) return false;
    wpos += cnt;
    __syncthreads();

    base = 2048 / sizeof(type);
    range = 256 / sizeof(type);
    cnt = avail - wpos;
    if (!d_REencode<byte, 256 / sizeof(type), true>(&bitmap[base], range, &out[wpos], cnt, &bitmap[base + range], temp_w)) return false;
    wpos += cnt;
    __syncthreads();

    base = (2048 + 256) / sizeof(type);
    range = 32 / sizeof(type);
    if constexpr (sizeof(type) < 8) {
      cnt = avail - wpos;
      if (!d_REencode<byte, 32 / sizeof(type), true>(&bitmap[base], range, &out[wpos], cnt, &bitmap[base + range], temp_w)) return false;
      wpos += cnt;

      base = (2048 + 256 + 32) / sizeof(type);
      range = 4 / sizeof(type);
    }

    // output last level of bitmap
    if (wpos >= avail - range) return false;
    if (tid < range) {  // 4 / sizeof(type)
      out[wpos + tid] = bitmap[base + tid];
    }
    wpos += range;
  }

  // copy leftover bytes
  if constexpr (sizeof(type) > 1) {
    if (tid < extra) out[wpos + tid] = in[csize - extra + tid];
  }

  // output old csize and update csize
  const int new_size = wpos + 2 + extra;
  if (tid == 0) {
    out[new_size - 2] = csize;  // bottom byte
    out[new_size - 1] = csize >> 8;  // second byte
  }
  csize = new_size;
  return true;
}


static __device__ inline void d_iRZE_1(int& csize, byte in [CS], byte out [CS], byte temp [CS])
{
  using type = byte;
  const int tid = threadIdx.x;
  int rpos = csize;
  csize = (int)in[--rpos] << 8;  // second byte
  csize |= in[--rpos];  // bottom byte
  const int size = csize / sizeof(type);  // words in chunk (rounded down)
  assert(CS == 16384);
  assert(TPB >= 256);

  // copy leftover byte
  if constexpr (sizeof(type) > 1) {
    const int extra = csize % sizeof(type);
    if (tid < extra) out[csize - extra + tid] = in[rpos - extra + tid];
    rpos -= extra;
  }

  if (rpos == 0) {
    // all zeros
    type* const out_t = (type*)out;
    for (int i = tid; i < size; i += TPB) {
      out_t[i] = 0;
    }
  } else {
    int* const temp_w = (int*)temp;
    byte* const bitmap = (byte*)&temp_w[WS];

    // iteratively decompress bitmaps
    int base, range;
    if constexpr (sizeof(type) == 8) {
      base = (2048 + 256) / sizeof(type);
      range = 32 / sizeof(type);
      // read in last level of bitmap
      rpos -= range;
      if (tid < range) bitmap[base + tid] = in[rpos + tid];
    } else {
      base = (2048 + 256 + 32) / sizeof(type);
      range = 4 / sizeof(type);
      // read in last level of bitmap
      rpos -= range;
      if (tid < range) bitmap[base + tid] = in[rpos + tid];

      rpos -= __syncthreads_count((tid < range * 8) && ((in[rpos + tid / 8] >> (tid % 8)) & 1));
      base = (2048 + 256) / sizeof(type);
      range = 32 / sizeof(type);
      d_REdecode<byte, 32 / sizeof(type)>(range, &in[rpos], &bitmap[base + range], &bitmap[base], temp_w);
    }
    __syncthreads();

    rpos -= __syncthreads_count((tid < range * 8) && ((bitmap[base + tid / 8] >> (tid % 8)) & 1));
    base = 2048 / sizeof(type);
    range = 256 / sizeof(type);
    d_REdecode<byte, 256 / sizeof(type)>(range, &in[rpos], &bitmap[base + range], &bitmap[base], temp_w);
    __syncthreads();

    if constexpr (sizeof(type) >= 4) {
      rpos -= __syncthreads_count((tid < range * 8) && ((bitmap[base + tid / 8] >> (tid % 8)) & 1));
    }
    if constexpr (sizeof(type) == 2) {
      int sum = __syncthreads_count((tid < range * 8) && ((bitmap[base + tid / 8] >> (tid % 8)) & 1));
      sum += __syncthreads_count((tid + TPB < range * 8) && ((bitmap[base + (tid + TPB) / 8] >> (tid % 8)) & 1));
      rpos -= sum;
    }
    if constexpr (sizeof(type) == 1) {
      int sum = 0;
      for (int i = 0; i < TPB * 4; i += TPB) {
        sum += __syncthreads_count((tid + i < range * 8) && ((bitmap[base + (tid + i) / 8] >> (tid % 8)) & 1));
      }
      rpos -= sum;
    }
    base = 0 / sizeof(type);
    range = 2048 / sizeof(type);
    d_REdecode<byte, 2048 / sizeof(type)>(range, &in[rpos], &bitmap[base + range], &bitmap[base], temp_w);
    __syncthreads();

    // copy non-zero values based on bitmap
    if (size > 0) d_ZEdecode(size, (type*)in, (type*)bitmap, (type*)out, temp_w);
  }
}
