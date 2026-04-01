// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import NextAuth from 'next-auth';

import { authOptions } from '@amdenterpriseai/utils/server';

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
