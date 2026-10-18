"""Pytest fixtures for CopperPilot Drone Enclosure verification test suite."""

import os
import sys

import pytest
import trimesh

# Add case root to sys.path
CASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(CASE_DIR, ".."))
sys.path.insert(0, CASE_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "pcb", "tests"))

from collision import CollisionVerifier
from generator import (
    KEY_COMPONENTS,
    EnclosureConfig,
    create_bottom_base,
    create_top_canopy,
)


@pytest.fixture(scope="session")
def enclosure_config():
    """Provides standard manufacturing configuration for enclosure tests."""
    return EnclosureConfig(
        wall_thickness=1.4,
        pcb_clearance=0.3,
        component_clearance=0.6,
        snap_engagement=0.5,
        nozzle_diameter=0.4,
        material="petg",
    )


@pytest.fixture(scope="session")
def enclosure_meshes(enclosure_config):
    """Generates and returns watertight trimesh models of top canopy and bottom chassis."""
    top = create_top_canopy(enclosure_config)
    bottom = create_bottom_base(enclosure_config)
    assembly = trimesh.util.concatenate([top, bottom])
    return {
        "top": top,
        "bottom": bottom,
        "assembly": assembly,
        "config": enclosure_config,
    }


@pytest.fixture(scope="session")
def key_components():
    """Returns nominal 3D spatial boundaries and positions of key components."""
    return KEY_COMPONENTS


@pytest.fixture(scope="session")
def pcb_assembly_stl():
    """Returns path to high-fidelity exported PCB STL, exporting if not present."""
    stl_path = os.path.join(CASE_DIR, "build", "pcb_assembly.stl")
    pcb_path = os.path.join(ROOT_DIR, "pcb", "CopperPilotDrone.kicad_pcb")
    if not os.path.exists(stl_path):
        CollisionVerifier.export_pcb_stl(pcb_path, stl_path)
    return stl_path
