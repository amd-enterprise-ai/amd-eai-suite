// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextResponse } from 'next/server';

import { isHttpUrl } from '@amdenterpriseai/utils/app';

export async function GET() {
  const isStandaloneMode =
    (process.env.STANDALONE_MODE ?? '').trim().toLowerCase() === 'true';
  const rawAirmAppUrl = process.env.AIRM_APP_URL?.trim();
  const airmAppUrl =
    rawAirmAppUrl && isHttpUrl(rawAirmAppUrl) ? rawAirmAppUrl : undefined;
  const clusterAuthEnabled =
    (process.env.CLUSTER_AUTH_ENABLED ?? 'true').trim().toLowerCase() !==
    'false';
  const config: {
    isStandaloneMode: boolean;
    defaultNamespace: string | null;
    clusterAuthEnabled: boolean;
    airmAppUrl?: string;
  } = {
    isStandaloneMode,
    defaultNamespace: process.env.DEFAULT_NAMESPACE?.trim() ?? null,
    clusterAuthEnabled,
  };
  if (!isStandaloneMode && airmAppUrl) {
    config.airmAppUrl = airmAppUrl;
  }
  return NextResponse.json({ config });
}
