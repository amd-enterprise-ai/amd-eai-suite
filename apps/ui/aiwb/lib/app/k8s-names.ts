// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/** Kubernetes DNS subdomain name pattern (RFC 1123), aligned with backend secret names. */
export const K8S_DNS_SUBDOMAIN_PATTERN = /^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$/;

export const K8S_DNS_SUBDOMAIN_MAX_LENGTH = 253;

export const isValidK8sDnsSubdomain = (value: string): boolean => {
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > K8S_DNS_SUBDOMAIN_MAX_LENGTH) {
    return false;
  }
  return K8S_DNS_SUBDOMAIN_PATTERN.test(trimmed);
};
