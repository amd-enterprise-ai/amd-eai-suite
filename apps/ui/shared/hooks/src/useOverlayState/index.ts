// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useDisclosure } from '@heroui/react';

/**
 * Manages open/close state for overlays (modals, drawers, popovers).
 * Adapter that re-exports useDisclosure today; will swap to v3's
 * useOverlayState at EAI-5712.
 */
export const useOverlayState = useDisclosure;
