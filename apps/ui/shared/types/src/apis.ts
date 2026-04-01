// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export type APIErrorContent = {
  message: string;
};

export type APIError = {
  error: string | APIErrorContent;
};
