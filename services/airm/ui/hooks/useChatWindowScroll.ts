// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { RefObject, useState } from 'react';

import { throttle } from '../utils/data/throttle';

/*
Custom hook which encapsulates scroll functionality for chat windows.
 */
export function useChatWindowScroll(
  messagesEndRefs: RefObject<HTMLDivElement | null>[],
  chatContainerRefs: RefObject<HTMLDivElement | null>[],
) {
  const [autoScrollEnabled, setAutoScrollEnabled] = useState<boolean>(true);
  const [showScrollDownButton, setShowScrollDownButton] =
    useState<boolean>(false);
  const [scrollEnabled, setScrollEnabled] = useState<boolean>(false);

  const handleScrollDown = () => {
    chatContainerRefs.forEach((ref) => {
      ref.current?.scrollTo({
        top: ref.current.scrollHeight,
        behavior: 'smooth',
      });
    });
  };

  const handleScroll = () => {
    setScrollEnabled(false);

    chatContainerRefs.forEach((ref) => {
      if (ref.current) {
        const { scrollTop, scrollHeight, clientHeight } = ref.current;
        const bottomTolerance = 30;

        if (scrollTop + clientHeight < scrollHeight - bottomTolerance) {
          setScrollEnabled(true);
        }
      }
    });

    if (scrollEnabled) {
      setAutoScrollEnabled(false);
      setShowScrollDownButton(true);
    } else {
      setShowScrollDownButton(false);
      setAutoScrollEnabled(true);
    }
  };

  const scrollDown = () => {
    messagesEndRefs.forEach((ref) => {
      if (autoScrollEnabled && !scrollEnabled) {
        ref.current?.scrollIntoView();
      }
    });
  };
  const throttledScrollDown = throttle(scrollDown, 250);

  return {
    showScrollDownButton,
    handleScroll,
    handleScrollDown,
    throttledScrollDown,
  };
}
