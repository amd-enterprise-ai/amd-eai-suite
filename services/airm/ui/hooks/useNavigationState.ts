// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback, useState } from 'react';
import { useRouter } from 'next/router';

import { airmMenuItems, aiWorkbenchMenuItems } from '@/utils/app/navigation';

interface UseNavigationStateResult {
  expandedSections: string[];
  currentSection: string | null;
  toggleSection: (sectionId: string) => void;
}

/**
 * Custom hook for managing navigation state.
 * Keeps track of which collapsible section is currently expanded and
 * determines which page is currently active and which section it belongs to.
 * The expanded section can be manually controlled or automatically set based on the current page.
 */
export const useNavigationState = (): UseNavigationStateResult => {
  const router = useRouter();
  const [manualExpandedSections, setManualExpandedSections] = useState<
    string[]
  >([]);
  const [hasUserInteracted, setHasUserInteracted] = useState(false);

  /**
   * Determines which section a given page belongs to based on the menu structure
   */
  const getSectionForPage = useCallback((pathname: string): string | null => {
    // Check if page belongs to resource management section
    const isResourceManagementPage = airmMenuItems.some((item) => {
      if (item.href === '/') {
        return pathname === '/';
      }
      return pathname === item.href || pathname.startsWith(item.href + '/');
    });

    if (isResourceManagementPage) {
      return 'resource-management';
    }

    // Check if page belongs to AI Workbench section
    const isAIWorkbenchPage = aiWorkbenchMenuItems.some((item) => {
      return pathname === item.href || pathname.startsWith(item.href + '/');
    });

    if (isAIWorkbenchPage) {
      return 'ai-workbench';
    }

    return null;
  }, []);

  // Get current page and section
  const currentPage = router.pathname;
  const currentSection = getSectionForPage(currentPage);

  const expandedSections = hasUserInteracted
    ? manualExpandedSections
    : currentSection
      ? [currentSection]
      : [];

  const toggleSection = useCallback(
    (sectionId: string) => {
      setHasUserInteracted(true);
      setManualExpandedSections((prev) => {
        const baseState = hasUserInteracted
          ? prev
          : currentSection
            ? [currentSection]
            : [];

        if (baseState.includes(sectionId))
          return baseState.filter((id) => id !== sectionId);

        return [...baseState, sectionId];
      });
    },
    [hasUserInteracted, currentSection],
  );

  return {
    expandedSections,
    currentSection,
    toggleSection,
  };
};
