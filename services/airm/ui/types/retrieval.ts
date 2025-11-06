// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export interface RetrievalContext {
  collectionId: string;
  certainty?: number;
  top_k?: number; // needs to be snake_case to match the API
  alpha?: number;
}
