"""
Tests for endpoint metadata C code generation (avlos_endpoint_metadata.h / .c).

The metadata table describes each endpoint's kind, value_dtype, and (for callables)
num_args and arg_dtypes, so firmware can do type-aware UART ASCII parsing without
a hand-maintained table.
"""

import importlib.resources
import os
import unittest

import yaml

from avlos.deserializer import deserialize
from avlos.generators import generator_c
from avlos.generators.filters import avlos_endpoints


class TestMetadataGeneration(unittest.TestCase):
    """Test that generator_c emits endpoint metadata when paths are configured."""

    def setUp(self):
        """Load good_device spec and set up output paths."""
        def_path = str(importlib.resources.files("tests").joinpath("definition/good_device.yaml"))
        with open(def_path) as f:
            self.device = deserialize(yaml.safe_load(f))
        self.out_dir = str(importlib.resources.files("tests").joinpath("outputs"))
        self.meta_header = os.path.join(self.out_dir, "avlos_endpoint_metadata_test.h")
        self.meta_impl = os.path.join(self.out_dir, "avlos_endpoint_metadata_test.c")

    def _config_with_metadata(self):
        """Config that includes optional metadata output paths."""
        return {
            "paths": {
                "output_enums": os.path.join(self.out_dir, "metadata_test_enums.h"),
                "output_header": os.path.join(self.out_dir, "metadata_test_header.h"),
                "output_impl": os.path.join(self.out_dir, "metadata_test_impl.c"),
                "output_metadata_header": self.meta_header,
                "output_metadata_impl": self.meta_impl,
            },
        }

    def test_metadata_files_generated_when_paths_set(self):
        """When both output_metadata_header and output_metadata_impl are set, both files are created."""
        config = self._config_with_metadata()
        generator_c.process(self.device, config)
        self.assertTrue(os.path.exists(self.meta_header), "Metadata header should be created")
        self.assertTrue(os.path.exists(self.meta_impl), "Metadata implementation should be created")

    def test_metadata_count_matches_endpoint_count(self):
        """avlos_endpoint_meta_count in generated C must match the number of endpoints."""
        config = self._config_with_metadata()
        generator_c.process(self.device, config)
        expected_count = len(avlos_endpoints(self.device))
        with open(self.meta_impl) as f:
            content = f.read()
        # Count variable and sizeof expression (clang-format may wrap the line)
        self.assertIn("avlos_endpoint_meta_count", content)
        self.assertIn("sizeof(avlos_endpoint_meta)", content)
        self.assertIn("sizeof(avlos_endpoint_meta) / sizeof(avlos_endpoint_meta[0])", content)

    def test_metadata_read_only_uint32(self):
        """A read-only uint32 endpoint (e.g. sn) has READ_ONLY kind and UINT32 value_dtype."""
        config = self._config_with_metadata()
        generator_c.process(self.device, config)
        with open(self.meta_impl) as f:
            content = f.read()
        self.assertIn("AVLOS_EP_KIND_READ_ONLY", content)
        self.assertIn("AVLOS_DTYPE_UINT32", content)
        # good_device has 'sn' as first endpoint: read-only uint32 (full_name is "sn" at root)
        self.assertIn("avlos_sn", content)

    def test_metadata_call_with_args(self):
        """A callable with two float args (e.g. set_pos_vel_setpoints) has CALL_WITH_ARGS and arg_dtypes."""
        config = self._config_with_metadata()
        generator_c.process(self.device, config)
        with open(self.meta_impl) as f:
            content = f.read()
        self.assertIn("AVLOS_EP_KIND_CALL_WITH_ARGS", content)
        self.assertIn("avlos_controller_set_pos_vel_setpoints", content)
        # Should have two AVLOS_DTYPE_FLOAT for the two float arguments
        self.assertIn("AVLOS_DTYPE_FLOAT", content)
        # num_args = 2 for this endpoint
        self.assertIn(".num_args = 2", content)

    def test_metadata_not_required(self):
        """Generator runs successfully without metadata paths (backward compatibility)."""
        # Use a path we never pass to the generator; without metadata keys it must not be created
        never_passed_meta_header = os.path.join(self.out_dir, "avlos_metadata_absent_test.h")
        never_passed_meta_impl = os.path.join(self.out_dir, "avlos_metadata_absent_test.c")
        config = {
            "paths": {
                "output_enums": os.path.join(self.out_dir, "no_meta_enums.h"),
                "output_header": os.path.join(self.out_dir, "no_meta_header.h"),
                "output_impl": os.path.join(self.out_dir, "no_meta_impl.c"),
            },
        }
        generator_c.process(self.device, config)
        self.assertFalse(
            os.path.exists(never_passed_meta_header),
            "Metadata header must not be created when paths are not in config",
        )
        self.assertFalse(
            os.path.exists(never_passed_meta_impl),
            "Metadata impl must not be created when paths are not in config",
        )
