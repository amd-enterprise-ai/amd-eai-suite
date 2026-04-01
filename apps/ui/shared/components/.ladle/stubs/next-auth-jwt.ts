// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

// Stub for next-auth/jwt in Ladle environment.

export type JWT = Record<string, unknown>;
export const getToken = () => Promise.resolve(null);
