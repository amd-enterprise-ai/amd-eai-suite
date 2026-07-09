// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import {
  getAimClusterProfilesByAimIds,
  getProjectAimProfilesByAimIds,
} from '@/lib/app/aims';
import type { AIMProfileSpec } from '@/types/aims';

/** Profile specs are effectively immutable for the session — they only
 *  change when the aim-engine / chart is reinstalled. `Infinity` keeps
 *  React Query from ever marking the data stale, so workload polling never
 *  re-fetches profiles. */
const PROFILE_CACHE_MS = Infinity;

/**
 * Returns a `profile name → spec` map by fetching both profile catalogs
 * (AIMClusterProfile + AIMProfile) for the given aimIds and indexing them
 * by profile name.
 *
 * Callers compute the aimId union at the call site — typically the
 * `status.aimId` of every cluster model from `useInferenceModelsByName` plus
 * every fine-tuned AIMModel CR — and must wait for those upstream fetches to
 * settle before passing the result, otherwise the partially-populated array
 * will trigger one profile fetch per per-name fan-out completion.
 *
 * Namespace profiles take precedence on name collision (when a non-overlay
 * project profile shadows its cluster equivalent).
 *
 * Coverage caveat: AIWB's `/projects/{p}/profiles` filters out
 * AIMService-owned overlay profiles (see `_is_service_owned_profile` in
 * `apps/api/aiwb/app/aims/gateway.py`), so deployments whose
 * `status.resolvedProfile.name` points at a service-owned overlay will not
 * be present in the returned map. Callers must treat a lookup miss as a
 * null profile (which `toProfileSummaryFields` already does).
 */
export const useProfileSpecsForServices = ({
  aimIds,
  project,
}: {
  aimIds: string[];
  project: string | null | undefined;
}): { specByName: Map<string, AIMProfileSpec>; isLoading: boolean } => {
  // Each query self-gates on `length > 0` — when the caller is still waiting
  // for upstream models to land it passes `[]` and no fetch fires.
  const { data: clusterProfiles = [], isLoading: isLoadingCluster } = useQuery({
    queryKey: ['aim-cluster-profiles', aimIds],
    queryFn: () => getAimClusterProfilesByAimIds(aimIds),
    enabled: aimIds.length > 0,
    staleTime: PROFILE_CACHE_MS,
  });

  const { data: namespaceProfiles = [], isLoading: isLoadingNamespace } =
    useQuery({
      queryKey: ['project', project, 'aim-profiles', aimIds],
      queryFn: () => getProjectAimProfilesByAimIds(project!, aimIds),
      enabled: !!project && aimIds.length > 0,
      staleTime: PROFILE_CACHE_MS,
    });

  const specByName = useMemo((): Map<string, AIMProfileSpec> => {
    const map = new Map<string, AIMProfileSpec>();
    for (const p of clusterProfiles) {
      if (p.metadata.name) map.set(p.metadata.name, p.spec);
    }
    for (const p of namespaceProfiles) {
      if (p.metadata.name) map.set(p.metadata.name, p.spec);
    }
    return map;
  }, [clusterProfiles, namespaceProfiles]);

  return { specByName, isLoading: isLoadingCluster || isLoadingNamespace };
};
