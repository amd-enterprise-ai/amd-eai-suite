// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

// Extracts data from an HTML form element and converts it to an object
// If there are multiple elements with the same key (multi-select dropdown for example),
// it converts that entry into an array
export const parseFormData = (target: HTMLFormElement) => {
  return Array.from(new FormData(target).entries()).reduce(
    (acc, [k, v]) => {
      if (!acc[k]) {
        acc[k] = v;
      } else if (Array.isArray(acc[k])) {
        acc[k].push(v);
      } else {
        acc[k] = [acc[k], v];
      }
      return acc;
    },
    {} as Record<PropertyKey, any>,
  );
};
