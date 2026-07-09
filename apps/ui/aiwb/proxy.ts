// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export { proxy } from '@amdenterpriseai/utils/server/proxy';

// Keep config local: sharing/re-exporting it from a barrel can be flaky in Next dev,
// which may run proxy for /_next/* assets and trigger sign-in redirect loops.
export const config = {
  matcher: ['/', '/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
