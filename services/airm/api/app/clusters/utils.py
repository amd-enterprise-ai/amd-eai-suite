# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from typing import Any

from airm.messaging.schemas import ClusterNode

from .models import ClusterNode as ClusterNodeModel


def flatten_for_db_comparison(node: ClusterNode) -> dict[str, Any]:
    """Flattens a ClusterNode object into a dictionary, so it is comparable with the ClusterNode database model."""
    node_dict = node.model_dump(exclude={"gpu_information"})
    gpu_info = node.gpu_information
    if gpu_info:
        gpu_data = {f"gpu_{k}": v for k, v in gpu_info.model_dump().items()}
        node_dict.update(gpu_data)
    return node_dict


def has_node_changed(node: ClusterNode, existing_node: ClusterNodeModel) -> bool:
    existing_node_fields = existing_node.__dict__
    return any(
        v != existing_node_fields.get(k)
        for k, v in flatten_for_db_comparison(node).items()
        if k in existing_node_fields
    )
