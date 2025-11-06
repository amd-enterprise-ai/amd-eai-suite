# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT
from uuid import UUID


def get_attr_or_key(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def extract_label_id(item: dict, label_key: str) -> UUID | None:
    metadata = get_attr_or_key(item, "metadata", {})
    labels = get_attr_or_key(metadata, "labels", {})
    label_value = get_attr_or_key(labels, label_key, None)
    try:
        return UUID(label_value) if label_value else None
    except (ValueError, TypeError):
        return None
