# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

import importlib
import pkgutil
import sys
from pathlib import Path


def verify_submodule_imports(package, root_package_name):
    if hasattr(package, "__path__"):
        for _, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_module_name = f"{root_package_name}.{name}"
            try:
                submodule = importlib.import_module(full_module_name)
                print(f"Successfully imported {full_module_name}")
                if is_pkg:  # Recursive call for packages
                    verify_submodule_imports(submodule, full_module_name)
            except Exception as e:
                print(f"Error importing {full_module_name}: {e}")
                sys.exit(1)


def verify_package_location(package_name, editable):
    module = importlib.import_module(package_name)
    if module.__file__ is None:
        print(f"Package {package_name} seems to lack an __init__.py file.")
        sys.exit(1)
    package_path = Path(module.__file__).resolve().parent
    if editable:
        # For editable installs, the package should NOT be in site-packages
        # It should be in the source directory (could be /src/, packages/, or any other structure)
        if "/site-packages/" in str(package_path):
            print(f"Package {package_name} seems not installed in editable mode as expected.")
            sys.exit(1)
    else:
        if "/site-packages/" not in str(package_path):
            print(f"Package {package_name} seems installed in editable mode, not standard as expected.")
            sys.exit(1)
    print(f"Package {package_name} installation mode (editable={editable}) verified successfully.")


def main(package_name, editable=False):
    try:
        package = importlib.import_module(package_name)
        print(f"Successfully imported {package_name}")
        verify_submodule_imports(package, package_name)
        verify_package_location(package_name, editable)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python test_packages_installation.py <package_name> [editable]")
        sys.exit(1)
    package_name = sys.argv[1]
    editable = len(sys.argv) == 3 and sys.argv[2] == "editable"
    main(package_name, editable)
