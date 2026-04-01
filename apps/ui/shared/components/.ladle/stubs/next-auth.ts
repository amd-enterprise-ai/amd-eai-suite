// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

// Stub for next-auth in Ladle environment.
// Barrel imports from shared packages pull in modules that depend on next-auth,
// even though chart/UI components never use auth directly.

export default {};
export type Session = Record<string, unknown>;
export type JWT = Record<string, unknown>;
