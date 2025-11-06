# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

from threading import Lock


class AppConfig:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.org_name = None
            self.cluster_name = None

    def set_config(self, org_name: str, cluster_name: str):
        self.org_name = org_name
        self.cluster_name = cluster_name

    def get_org_name(self) -> str:
        if not self.org_name:
            raise ValueError("Organization name is not set.")
        return self.org_name

    def get_cluster_name(self) -> str:
        if not self.cluster_name:
            raise ValueError("Cluster name is not set.")
        return self.cluster_name

    def destroy_instance(cls):
        with cls._lock:
            cls._instance = None
