// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export interface DragSelectionConfig {
  selectedKeys: Set<string>;
  onSelectionChange: (keys: string[]) => void;
  hasUserInteracted: boolean;
  onUserInteraction: () => void;
}

export interface DragSelectionResult {
  isDragging: boolean;
  dragStartItem: string | null;
  handleMouseDown: (itemKey: string, event: React.MouseEvent) => void;
  handleMouseEnter: (itemKey: string) => void;
  handleMouseUp: () => void;
}
