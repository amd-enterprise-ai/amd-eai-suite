# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from enum import StrEnum

from ..charts.config import COMFYUI_CHART_NAME, JUPYTERLAB_CHART_NAME, MLFLOW_CHART_NAME, VSCODE_CHART_NAME


class WorkspaceType(StrEnum):
    VSCODE = "vscode"
    JUPYTERLAB = "jupyterlab"
    COMFYUI = "comfyui"
    MLFLOW = "mlflow"


workspace_type_chart_name_mapping = {
    WorkspaceType.VSCODE: VSCODE_CHART_NAME,
    WorkspaceType.JUPYTERLAB: JUPYTERLAB_CHART_NAME,
    WorkspaceType.COMFYUI: COMFYUI_CHART_NAME,
    WorkspaceType.MLFLOW: MLFLOW_CHART_NAME,
}


class WorkspaceUsageScope(StrEnum):
    USER = "user"
    NAMESPACE = "namespace"


WORKSPACE_USAGE_SCOPE_MAPPING = {
    WorkspaceType.VSCODE: WorkspaceUsageScope.USER,
    WorkspaceType.JUPYTERLAB: WorkspaceUsageScope.USER,
    WorkspaceType.COMFYUI: WorkspaceUsageScope.USER,
    WorkspaceType.MLFLOW: WorkspaceUsageScope.NAMESPACE,
}

WORKSPACE_URL_SUFFIX_MAPPING = {
    VSCODE_CHART_NAME: "/?folder=/workload",
    JUPYTERLAB_CHART_NAME: "/lab",
    COMFYUI_CHART_NAME: "/",
    MLFLOW_CHART_NAME: "/",
}
