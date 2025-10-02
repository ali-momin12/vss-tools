# Copyright (c) 2022 Contributors to COVESA
#
# This program and the accompanying materials are made available under the
# terms of the Mozilla Public License 2.0 which is available at
# https://www.mozilla.org/en-US/MPL/2.0/
#
# SPDX-License-Identifier: MPL-2.0

import filecmp
import pathlib
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TEST_UNITS = HERE / "test_units.yaml"
TEST_QUANT = HERE / "test_quantities.yaml"
DEFAULT_TEST_FILE = "test.vspec"


def default_directories() -> list:
    directories = []
    for path in HERE.iterdir():
        if path.is_dir():
            if list(path.rglob(DEFAULT_TEST_FILE)):
                # Exclude directories with custom made python file
                if not list(path.rglob("*.py")):
                    directories.append(path)
    return directories


# Use directory name as test name
def idfn(directory: pathlib.PosixPath):
    return directory.name


def _compare_dirs(left: Path, right: Path, check_structure: bool = True):
    """
    Compare directory contents. For ros2interface the original test only checked diff_files.
    """
    dcmp = filecmp.dircmp(left, right)
    if check_structure:
        assert not (dcmp.diff_files or dcmp.left_only or dcmp.right_only), (
            f"Directory mismatch:\n"
            f"  Differing files: {dcmp.diff_files}\n"
            f"  Only in output: {dcmp.left_only}\n"
            f"  Only in expected: {dcmp.right_only}\n"
            f"  Output: {left}\n  Expected: {right}"
        )
    else:
        assert not dcmp.diff_files, f"Differing files: {dcmp.diff_files}\n" f"Output: {left}\nExpected: {right}"


def run_exporter(directory: Path, exporter: str, tmp_path: Path, *, mode: str | None = None):
    vspec = directory / DEFAULT_TEST_FILE
    types = directory / "types.vspec"
    if exporter == "ros2interface":
        assert mode in {"leaf", "aggregate"}, "mode must be 'leaf' or 'aggregate' for ros2interface"
        output = tmp_path / f"out.{exporter}.{mode}"
        expected_dir = directory / f"expected.{exporter}.{mode}"
    else:
        output = tmp_path / f"out.{exporter}"
        expected_dir = directory / f"expected.{exporter}"

    topics_file = directory / "topics.txt"
    if exporter == "ros2interface":
        topics_file.write_text("# includes only branch A\nA.*", encoding="utf-8")

    # Build the command as a list (robust against spaces)
    cmd: list[str] = [
        "vspec",
        "export",
        exporter,
        "-u",
        str(TEST_UNITS),
        "-q",
        str(TEST_QUANT),
        "--vspec",
        str(vspec),
    ]
    if types.exists():
        cmd += ["--types", str(types)]

    if exporter == "apigear":
        cmd += ["--output-dir", str(output)]
    elif exporter == "samm":
        cmd += ["--target-folder", str(output)]
    elif exporter == "ros2interface":
        cmd += [
            "--output",
            str(output),
            "--topics-file",
            str(topics_file),
            "--topics",
            "A.*",
            "--topics-case-insensitive",
            "--mode",
            str(mode),
            "--srv",
            "both",
            "--expand",
            "--srv-use-msg",
            "--exclude-topics",
            "Z.*",
        ]
    else:
        cmd += ["--output", str(output)]

    subprocess.run(cmd.split(), check=True)

    if not expected_dir.exists():
        # If you want find directory/exporter combinations not yet covered enable the assert
        # assert False, f"Folder {expected} not found"
        return

    if exporter in {"apigear", "samm"}:
        _compare_dirs(output, expected_dir, check_structure=True)
    elif exporter == "ros2interface":
        # Preserve original semantics: only check differing files
        _compare_dirs(output, expected_dir, check_structure=False)
    else:
        # File outputs
        assert expected_dir.is_file(), f"Expected file not found: {expected_dir}"
        assert output.is_file(), f"Output file not found: {output}"
        assert filecmp.cmp(output, expected_dir), f"Output differs from expected:\n{output}\n{expected_dir}"


@pytest.mark.parametrize("directory", default_directories(), ids=idfn)
def test_exporters(directory, tmp_path):
    # Run all "supported" exporters, i.e. not those in contrib
    # Exception is "binary", as it is assumed output may vary depending on target
    # For ros2interface, running both 'leaf' and 'aggregate' modes,
    # to improve coverage of mutually exclusive code paths.
    exporters = [
        "ros2interface",
        "apigear",
        "json",
        "jsonschema",
        "ddsidl",
        "plantuml",
        "csv",
        "yaml",
        "franca",
        "graphql",
        "go",
        "samm",
    ]

    for exporter in exporters:
        if exporter == "ros2interface":
            # Run both modes to cover both branches
            for mode in ("leaf", "aggregate"):
                run_exporter(directory, exporter, tmp_path, mode=mode)
        else:
            run_exporter(directory, exporter, tmp_path)
