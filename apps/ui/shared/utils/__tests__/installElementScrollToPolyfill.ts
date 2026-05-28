// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * JSDOM exposes scrollTop/scrollLeft on Element but not scrollTo; @react-aria/utils
 * calls scrollView.scrollTo. Install a minimal polyfill only when the prototype has
 * no scrollTo so future JSDOM (non-configurable built-in) does not throw.
 */
export function installElementScrollToPolyfill(): void {
  if (typeof Element === 'undefined' || 'scrollTo' in Element.prototype) {
    return;
  }

  Object.defineProperty(Element.prototype, 'scrollTo', {
    value(
      this: Element,
      optionsOrX?: ScrollToOptions | number,
      y?: number,
    ): void {
      const el = this as HTMLElement;
      if (typeof optionsOrX === 'object' && optionsOrX !== null) {
        if (optionsOrX.top != null) el.scrollTop = optionsOrX.top;
        if (optionsOrX.left != null) el.scrollLeft = optionsOrX.left;
      } else if (typeof optionsOrX === 'number') {
        el.scrollLeft = optionsOrX;
        if (typeof y === 'number') el.scrollTop = y;
      }
    },
    writable: true,
    configurable: true,
  });
}
