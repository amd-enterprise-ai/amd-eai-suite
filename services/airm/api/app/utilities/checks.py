# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from ..clusters.schemas import ClusterResponse, ClusterStatus
from ..projects.models import Project
from .exceptions import NotReadyException, UnhealthyException


# TODO This check is a bit strange and perhaps out of place?
def ensure_cluster_healthy(project: Project) -> None:
    if ClusterResponse.model_validate(project.cluster).status is not ClusterStatus.HEALTHY:
        raise UnhealthyException("Unable to submit workload to an unhealthy cluster.")


def ensure_base_url_configured(project: Project) -> None:
    if not project.cluster.base_url:
        raise NotReadyException("Cluster does not have a base URL configured. Please contact your administrator.")
