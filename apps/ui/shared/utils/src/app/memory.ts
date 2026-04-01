// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

const KBMultiplier = 1024;
const GBMultiplier = 1024 ** 3;

export const bytesToGigabytes = (bytes: number) => {
  return bytes / GBMultiplier;
};

export const megabytesToGigabytes = (mbs: number) => {
  return mbs / 1024;
};

export const gigabytesToBytes = (bytes: number) => {
  return bytes * GBMultiplier;
};

export const displayBytesInGigabytes = (bytes: number) => {
  return `${+bytesToGigabytes(bytes).toFixed(2)} GB`;
};

export const displayMegabytesInGigabytes = (mbs: number) => {
  return `${+megabytesToGigabytes(mbs).toFixed(2)} GB`;
};

export const displayBytesInOptimalUnit = (bytes: number): string => {
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = 0;
  let i = 0;

  if (bytes > 0) {
    i = Math.min(
      Math.floor(Math.log(bytes) / Math.log(KBMultiplier)),
      sizes.length - 1,
    );
    value = parseFloat((bytes / KBMultiplier ** i).toFixed(2));
  }
  return `${value} ${sizes[i]}`;
};
