// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useState, useEffect, useRef, useCallback } from 'react';
import type { AutoscalingFieldValues } from '@/lib/app/aims';
import type { AIMService } from '@/types/aims';

export const CONVERGENCE_POLL_INTERVAL_MS = 5_000;
const CONVERGENCE_TIMEOUT_MS = 60_000;

interface UseScalingConvergenceParams {
  aimService: AIMService | undefined;
  isAimServiceError: boolean;
  /** Whether the parent is currently polling for data. */
  isPolling: boolean;
  /** Called when the runtime has converged with the saved settings, or on fetch error. */
  onConverged: () => void;
  /** Called when the convergence timeout expires before the runtime converges. */
  onTimeout: () => void;
}

interface UseScalingConvergenceReturn {
  startPolling: (savedValues: AutoscalingFieldValues) => void;
}

/**
 * Tracks whether runtime scaling status has converged with recently saved
 * autoscaling settings. Only replica counts are compared against
 * `status.runtime` (the actual cluster state); spec-level metric fields
 * update immediately on the server and are not meaningful convergence
 * indicators.
 *
 * The parent component owns the `isPolling` flag so the query's
 * `refetchInterval` can reference it without a circular dependency.
 */
export const useScalingConvergence = ({
  aimService,
  isAimServiceError,
  isPolling,
  onConverged,
  onTimeout,
}: UseScalingConvergenceParams): UseScalingConvergenceReturn => {
  const [lastSavedSettings, setLastSavedSettings] =
    useState<AutoscalingFieldValues | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onConvergedRef = useRef(onConverged);
  const onTimeoutRef = useRef(onTimeout);
  onConvergedRef.current = onConverged;
  onTimeoutRef.current = onTimeout;

  const clearConvergenceTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!isPolling || !lastSavedSettings) return;
    if (isAimServiceError) {
      setLastSavedSettings(null);
      clearConvergenceTimeout();
      onConvergedRef.current();
      return;
    }
    if (!aimService) return;
    const runtime = aimService.status?.runtime;
    const replicasConverged =
      runtime?.maxReplicas === lastSavedSettings.maxReplicas &&
      runtime?.minReplicas === lastSavedSettings.minReplicas;
    if (replicasConverged) {
      setLastSavedSettings(null);
      clearConvergenceTimeout();
      onConvergedRef.current();
    }
  }, [
    aimService,
    isPolling,
    lastSavedSettings,
    isAimServiceError,
    clearConvergenceTimeout,
  ]);

  useEffect(() => {
    return () => clearConvergenceTimeout();
  }, [clearConvergenceTimeout]);

  const startPolling = useCallback(
    (savedValues: AutoscalingFieldValues) => {
      setLastSavedSettings(savedValues);
      clearConvergenceTimeout();
      timeoutRef.current = setTimeout(() => {
        timeoutRef.current = null;
        setLastSavedSettings(null);
        onTimeoutRef.current();
      }, CONVERGENCE_TIMEOUT_MS);
    },
    [clearConvergenceTimeout],
  );

  return { startPolling };
};
