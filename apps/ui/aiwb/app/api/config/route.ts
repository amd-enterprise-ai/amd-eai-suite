// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextResponse } from 'next/server';

export async function GET() {
  const config = {
    isStandaloneMode:
      (process.env.STANDALONE_MODE ?? '').trim().toLowerCase() === 'true',
    // Make sure there are no extra spaces in the environment variables
    defaultNamespace: process.env.DEFAULT_NAMESPACE?.trim() ?? null,
  };

  return NextResponse.json({ config });
}
