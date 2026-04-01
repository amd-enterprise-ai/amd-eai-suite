# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

"""Tests for dispatch configuration."""

import importlib
from unittest.mock import patch

import pytest

from app.dispatch import config


def test_use_local_kube_context_default():
    """Test USE_LOCAL_KUBE_CONTEXT defaults to False."""
    with patch.dict("os.environ", {}, clear=True):
        importlib.reload(config)
        assert config.USE_LOCAL_KUBE_CONTEXT is False


def test_use_local_kube_context_true():
    """Test USE_LOCAL_KUBE_CONTEXT can be set to True."""
    with patch.dict("os.environ", {"USE_LOCAL_KUBE_CONTEXT": "true"}):
        importlib.reload(config)
        assert config.USE_LOCAL_KUBE_CONTEXT is True


def test_use_local_kube_context_case_insensitive():
    """Test USE_LOCAL_KUBE_CONTEXT is case insensitive."""
    with patch.dict("os.environ", {"USE_LOCAL_KUBE_CONTEXT": "TRUE"}):
        importlib.reload(config)
        assert config.USE_LOCAL_KUBE_CONTEXT is True


def test_polling_interval_default():
    """Test POLLING_INTERVAL_SECONDS defaults to 5."""
    with patch.dict("os.environ", {}, clear=True):
        importlib.reload(config)
        assert config.POLLING_INTERVAL_SECONDS == 5


def test_polling_interval_custom():
    """Test POLLING_INTERVAL_SECONDS can be customized."""
    with patch.dict("os.environ", {"SYNCER_POLLING_INTERVAL_SECONDS": "10"}):
        importlib.reload(config)
        assert config.POLLING_INTERVAL_SECONDS == 10


@pytest.mark.asyncio
@patch("app.dispatch.config.k8s_config.load_kube_config", autospec=True)
async def test_load_k8s_config_local_context(mock_load_kube_config):
    """Test load_k8s_config uses kubeconfig for local development."""
    with patch.object(config, "USE_LOCAL_KUBE_CONTEXT", True):
        await config.load_k8s_config()

    mock_load_kube_config.assert_called_once()


@pytest.mark.asyncio
@patch("app.dispatch.config.k8s_config.load_incluster_config", autospec=True)
async def test_load_k8s_config_in_cluster(mock_load_incluster):
    """Test load_k8s_config uses in-cluster config for production."""
    with patch.object(config, "USE_LOCAL_KUBE_CONTEXT", False):
        await config.load_k8s_config()

    mock_load_incluster.assert_called_once()


# =============================================================================
# Error handling
# =============================================================================


@pytest.mark.asyncio
@patch("app.dispatch.config.k8s_config.load_kube_config", autospec=True)
async def test_load_k8s_config_error_handling(mock_load_kube_config):
    """Test load_k8s_config propagates errors from config loading."""
    mock_load_kube_config.side_effect = Exception("Failed to load kubeconfig")

    with patch.object(config, "USE_LOCAL_KUBE_CONTEXT", True):
        with pytest.raises(Exception, match="Failed to load kubeconfig"):
            await config.load_k8s_config()


@pytest.mark.asyncio
@patch("app.dispatch.config.k8s_config.load_incluster_config", autospec=True)
async def test_load_k8s_config_incluster_error_handling(mock_load_incluster):
    """Test load_k8s_config propagates errors from in-cluster config loading."""
    mock_load_incluster.side_effect = Exception("Not running in cluster")

    with patch.object(config, "USE_LOCAL_KUBE_CONTEXT", False):
        with pytest.raises(Exception, match="Not running in cluster"):
            await config.load_k8s_config()
