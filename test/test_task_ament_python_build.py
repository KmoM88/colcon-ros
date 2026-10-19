# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

"""Tests for AmentPythonBuildTask supporting modern PEP 621 packages."""

import asyncio
from types import SimpleNamespace

from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.task import TaskContext

from colcon_ros.task.ament_python.build import AmentPythonBuildTask

import pytest


def test_ament_python_build_pep621(tmp_path):
    """Test AmentPythonBuildTask with a pyproject.toml package."""
    pytest.importorskip('flit_core')

    pkg_dir = tmp_path / 'src' / 'my_ros_pkg'
    pkg_dir.mkdir(parents=True)

    # ROS package.xml
    (pkg_dir / 'package.xml').write_text("""<?xml version="1.0"?>
<package format="3">
  <name>my_ros_pkg</name>
  <version>0.1.0</version>
  <description>Sample ament_python package with pyproject.toml</description>
  <maintainer email="user@example.com">User</maintainer>
  <license>Apache-2.0</license>
  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
""")

    # Modern pyproject.toml (no setup.py!)
    (pkg_dir / 'pyproject.toml').write_text("""
[build-system]
requires = ["flit_core >=3.2,<4"]
build-backend = "flit_core.buildapi"

[project]
name = "my_ros_pkg"
version = "0.1.0"
description = "Sample ament_python package with pyproject.toml"
readme = "README.md"
dependencies = []
""")
    (pkg_dir / 'README.md').write_text('# my_ros_pkg\n')
    mod_dir = pkg_dir / 'my_ros_pkg'
    mod_dir.mkdir()
    (mod_dir / '__init__.py').write_text('__version__ = "0.1.0"\n')

    desc = PackageDescriptor(pkg_dir)
    desc.name = 'my_ros_pkg'
    desc.type = 'ros.ament_python'

    build_base = tmp_path / 'build'
    install_base = tmp_path / 'install'
    build_base.mkdir(parents=True)
    install_base.mkdir(parents=True)

    task = AmentPythonBuildTask()
    context = TaskContext(
        pkg=desc,
        args=SimpleNamespace(
            path=str(pkg_dir),
            build_base=str(build_base),
            install_base=str(install_base),
            symlink_install=False,
        ),
        dependencies={},
    )
    task.set_context(context=context)

    res = asyncio.run(task.build())
    assert res is None, f'Task build failed with: {res}'

    # Verify ament_index marker
    marker = (
        install_base / 'share' / 'ament_index' / 'resource_index' /
        'packages' / 'my_ros_pkg'
    )
    assert marker.is_file(), f'Missing ament_index marker at {marker}'

    # Verify package.xml in share
    pkg_xml = install_base / 'share' / 'my_ros_pkg' / 'package.xml'
    assert pkg_xml.is_file(), f'Missing package.xml at {pkg_xml}'

    # Verify Python module installed
    dist_info = list(install_base.glob('**/my_ros_pkg-0.1.0.dist-info'))
    assert len(dist_info) == 1
    lib_dir = dist_info[0].parent
    assert (lib_dir / 'my_ros_pkg' / '__init__.py').is_file()

    # Verify ament_prefix_path environment hook created
    hook = (
        install_base / 'share' / 'my_ros_pkg' / 'hook' /
        'ament_prefix_path.dsv'
    )
    assert hook.is_file(), f'Missing ament_prefix_path hook at {hook}'
