// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button, Spinner } from '@amdenterpriseai/components';

type Props = {
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  showEmptyAcceleratorsWarning: boolean;
  emptyAcceleratorsMessage: string;
  loadingMessage: string;
  loadErrorMessage: string;
  retryLabel: string;
  onRetry: () => void;
};

export function RuntimeProfileCatalogStatus({
  isLoading,
  isError,
  errorMessage,
  showEmptyAcceleratorsWarning,
  emptyAcceleratorsMessage,
  loadingMessage,
  loadErrorMessage,
  retryLabel,
  onRetry,
}: Props) {
  if (isError) {
    return (
      <div
        className="flex flex-col gap-2 rounded-medium border border-danger/40 bg-danger-50/10 p-3 text-sm"
        data-testid="runtime-profile-catalog-error"
      >
        <p className="text-danger">{errorMessage ?? loadErrorMessage}</p>
        <Button size="sm" variant="flat" onPress={onRetry}>
          {retryLabel}
        </Button>
      </div>
    );
  }
  if (isLoading) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-default-500"
        data-testid="runtime-profile-catalog-loading"
      >
        <Spinner size="sm" />
        <span>{loadingMessage}</span>
      </div>
    );
  }
  if (showEmptyAcceleratorsWarning) {
    return (
      <p
        className="text-sm text-warning-600"
        data-testid="runtime-profile-empty-accelerators"
      >
        {emptyAcceleratorsMessage}
      </p>
    );
  }
  return null;
}
