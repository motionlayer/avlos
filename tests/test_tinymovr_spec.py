"""
Tests for Tinymovr specification parsing and code generation.
"""

import importlib.resources
import os
import unittest

import yaml

from avlos.datatypes import DataType
from avlos.definitions.remote_attribute import RemoteAttribute
from avlos.definitions.remote_bitmask import RemoteBitmask
from avlos.definitions.remote_enum import RemoteEnum
from avlos.definitions.remote_function import RemoteFunction
from avlos.deserializer import deserialize
from avlos.generators import generator_c, generator_cpp


class TestTinymovr_Parsing(unittest.TestCase):
    """Test parsing of Tinymovr specification."""

    @classmethod
    def setUpClass(cls):
        """Load the Tinymovr specification once for all tests."""
        def_path_str = str(importlib.resources.files("tests").joinpath("definition/tinymovr_2_3_x.yaml"))

        with open(def_path_str) as device_desc_stream:
            cls.device = deserialize(yaml.safe_load(device_desc_stream))

    def test_device_loaded(self):
        """Test that device specification loads successfully."""
        self.assertIsNotNone(self.device)
        self.assertEqual(self.device.name, "tm")

    def test_root_level_attributes(self):
        """Test that root-level attributes are parsed correctly."""
        attr_names = [attr.name for attr in self.device.remote_attributes.values()]

        # Test for specific root attributes
        self.assertIn("protocol_hash", attr_names)
        self.assertIn("uid", attr_names)
        self.assertIn("fw_version", attr_names)
        self.assertIn("Vbus", attr_names)
        self.assertIn("temp", attr_names)
        self.assertIn("calibrated", attr_names)

    def test_nested_attributes(self):
        """Test that nested remote_attributes are parsed correctly."""
        # Find scheduler attribute
        scheduler = next((attr for attr in self.device.remote_attributes.values() if attr.name == "scheduler"), None)
        self.assertIsNotNone(scheduler)

        # Check it has nested attributes
        self.assertTrue(hasattr(scheduler, "remote_attributes"))
        self.assertGreater(len(scheduler.remote_attributes), 0)

        # Check nested attribute names
        nested_names = [attr.name for attr in scheduler.remote_attributes.values()]
        self.assertIn("load", nested_names)
        self.assertIn("warnings", nested_names)

    def test_deeply_nested_attributes(self):
        """Test that deeply nested attributes (3+ levels) are parsed correctly."""
        # Find controller.position.setpoint (3 levels deep)
        controller = next((attr for attr in self.device.remote_attributes.values() if attr.name == "controller"), None)
        self.assertIsNotNone(controller)

        position = next((attr for attr in controller.remote_attributes.values() if attr.name == "position"), None)
        self.assertIsNotNone(position)

        nested_names = [attr.name for attr in position.remote_attributes.values()]
        self.assertIn("setpoint", nested_names)
        self.assertIn("p_gain", nested_names)

    def test_data_types(self):
        """Test that various data types are parsed correctly."""
        # uint32
        uid_attr = next((attr for attr in self.device.remote_attributes.values() if attr.name == "uid"), None)
        self.assertEqual(uid_attr.dtype, DataType.UINT32)

        # float
        vbus_attr = next((attr for attr in self.device.remote_attributes.values() if attr.name == "Vbus"), None)
        self.assertEqual(vbus_attr.dtype, DataType.FLOAT)

        # bool
        calibrated_attr = next((attr for attr in self.device.remote_attributes.values() if attr.name == "calibrated"), None)
        self.assertEqual(calibrated_attr.dtype, DataType.BOOL)

        # string
        fw_version_attr = next((attr for attr in self.device.remote_attributes.values() if attr.name == "fw_version"), None)
        self.assertEqual(fw_version_attr.dtype, DataType.STR)

    def test_getter_setter_names(self):
        """Test that getter and setter names are parsed correctly."""
        # Attribute with only getter
        uid_attr = next((attr for attr in self.device.remote_attributes.values() if attr.name == "uid"), None)
        self.assertEqual(uid_attr.getter_name, "system_get_uid")
        self.assertIsNone(uid_attr.setter_name)

        # Attribute with both getter and setter (need to find one in controller)
        controller = next((attr for attr in self.device.remote_attributes.values() if attr.name == "controller"), None)
        state_attr = next((attr for attr in controller.remote_attributes.values() if attr.name == "state"), None)
        self.assertEqual(state_attr.getter_name, "controller_get_state")
        self.assertEqual(state_attr.setter_name, "controller_set_state")

    def test_enum_attributes(self):
        """Test that attributes with options (enums) are parsed correctly."""
        controller = next((attr for attr in self.device.remote_attributes.values() if attr.name == "controller"), None)

        # Test controller.state enum
        state_attr = next((attr for attr in controller.remote_attributes.values() if attr.name == "state"), None)
        self.assertIsInstance(state_attr, RemoteEnum)
        member_names = [m.name for m in state_attr.options]
        self.assertIn("IDLE", member_names)
        self.assertIn("CALIBRATE", member_names)
        self.assertIn("CL_CONTROL", member_names)

        # Test controller.mode enum
        mode_attr = next((attr for attr in controller.remote_attributes.values() if attr.name == "mode"), None)
        self.assertIsInstance(mode_attr, RemoteEnum)
        member_names = [m.name for m in mode_attr.options]
        self.assertIn("CURRENT", member_names)
        self.assertIn("VELOCITY", member_names)
        self.assertIn("POSITION", member_names)
        self.assertIn("TRAJECTORY", member_names)
        self.assertIn("HOMING", member_names)

    def test_bitmask_attributes(self):
        """Test that attributes with flags (bitmasks) are parsed correctly."""
        # Test root-level errors bitmask
        errors_attr = next((attr for attr in self.device.remote_attributes.values() if attr.name == "errors"), None)
        self.assertIsInstance(errors_attr, RemoteBitmask)
        self.assertIn("UNDERVOLTAGE", errors_attr.bitmask.__members__)

        # Test warnings bitmask
        warnings_attr = next((attr for attr in self.device.remote_attributes.values() if attr.name == "warnings"), None)
        self.assertIsInstance(warnings_attr, RemoteBitmask)
        self.assertIn("DRIVER_FAULT", warnings_attr.bitmask.__members__)
        self.assertIn("CHARGE_PUMP_FAULT_STAT", warnings_attr.bitmask.__members__)

    def test_function_attributes(self):
        """Test that function attributes are parsed correctly."""
        # Test void function without arguments
        reset_func = next((attr for attr in self.device.remote_attributes.values() if attr.name == "reset"), None)
        self.assertIsInstance(reset_func, RemoteFunction)
        self.assertEqual(reset_func.dtype, DataType.VOID)
        self.assertEqual(reset_func.caller_name, "system_reset")
        self.assertEqual(len(reset_func.arguments), 0)

    def test_function_with_return_value(self):
        """Test that functions with return values are parsed correctly."""
        controller = next((attr for attr in self.device.remote_attributes.values() if attr.name == "controller"), None)

        # Test set_pos_vel_setpoints function (returns float)
        func = next((attr for attr in controller.remote_attributes.values() if attr.name == "set_pos_vel_setpoints"), None)
        self.assertIsInstance(func, RemoteFunction)
        self.assertEqual(func.dtype, DataType.FLOAT)
        self.assertEqual(func.caller_name, "controller_set_pos_vel_setpoints_user_frame")

    def test_function_with_arguments(self):
        """Test that functions with arguments are parsed correctly."""
        traj_planner = next((attr for attr in self.device.remote_attributes.values() if attr.name == "traj_planner"), None)

        # Test move_to function (has 1 argument)
        move_to_func = next((attr for attr in traj_planner.remote_attributes.values() if attr.name == "move_to"), None)
        self.assertIsInstance(move_to_func, RemoteFunction)
        self.assertEqual(len(move_to_func.arguments), 1)
        self.assertEqual(move_to_func.arguments[0].name, "pos_setpoint")
        self.assertEqual(move_to_func.arguments[0].dtype, DataType.FLOAT)

        # Test set_pos_vel_setpoints function (has 2 arguments)
        controller = next((attr for attr in self.device.remote_attributes.values() if attr.name == "controller"), None)
        func = next((attr for attr in controller.remote_attributes.values() if attr.name == "set_pos_vel_setpoints"), None)
        self.assertEqual(len(func.arguments), 2)
        self.assertEqual(func.arguments[0].name, "pos_setpoint")
        self.assertEqual(func.arguments[1].name, "vel_setpoint")

    def test_units(self):
        """Test that units are parsed correctly."""
        # Test volt unit
        vbus_attr = next((attr for attr in self.device.remote_attributes.values() if attr.name == "Vbus"), None)
        self.assertEqual(str(vbus_attr.unit), "volt")

        # Test ampere unit
        ibus_attr = next((attr for attr in self.device.remote_attributes.values() if attr.name == "Ibus"), None)
        self.assertEqual(str(ibus_attr.unit), "ampere")

        # Test degC unit
        temp_attr = next((attr for attr in self.device.remote_attributes.values() if attr.name == "temp"), None)
        self.assertEqual(str(temp_attr.unit), "degree_Celsius")

    def test_metadata(self):
        """Test that metadata is parsed correctly."""
        # Test dynamic flag
        vbus_attr = next((attr for attr in self.device.remote_attributes.values() if attr.name == "Vbus"), None)
        self.assertIsNotNone(vbus_attr.meta)
        self.assertTrue(vbus_attr.meta.get("dynamic", False))

        # Test export flag
        controller = next((attr for attr in self.device.remote_attributes.values() if attr.name == "controller"), None)
        position = next((attr for attr in controller.remote_attributes.values() if attr.name == "position"), None)
        p_gain_attr = next((attr for attr in position.remote_attributes.values() if attr.name == "p_gain"), None)
        self.assertTrue(p_gain_attr.meta.get("export", False))

        # Test reload_data flag
        reset_func = next((attr for attr in self.device.remote_attributes.values() if attr.name == "reset"), None)
        self.assertTrue(reset_func.meta.get("reload_data", False))

        # Test jog_step metadata
        setpoint_attr = next((attr for attr in position.remote_attributes.values() if attr.name == "setpoint"), None)
        self.assertEqual(setpoint_attr.meta.get("jog_step"), 100)

    def test_attribute_count(self):
        """Test that we have the expected number of attributes at various levels."""
        # Root level should have a significant number of attributes
        self.assertGreater(len(self.device.remote_attributes), 10)

        # Controller should have many nested attributes
        controller = next((attr for attr in self.device.remote_attributes.values() if attr.name == "controller"), None)
        self.assertGreater(len(controller.remote_attributes), 10)

        # Sensors should have complex nesting
        sensors = next((attr for attr in self.device.remote_attributes.values() if attr.name == "sensors"), None)
        self.assertIsNotNone(sensors)
        self.assertGreater(len(sensors.remote_attributes), 2)

    def test_full_name_generation(self):
        """Test that full names are generated correctly for nested attributes."""
        controller = next((attr for attr in self.device.remote_attributes.values() if attr.name == "controller"), None)
        position = next((attr for attr in controller.remote_attributes.values() if attr.name == "position"), None)
        setpoint_attr = next((attr for attr in position.remote_attributes.values() if attr.name == "setpoint"), None)

        # Full name should be dot-separated
        self.assertEqual(setpoint_attr.full_name, "controller.position.setpoint")

    def test_endpoint_function_name_generation(self):
        """Test that endpoint function names are generated correctly."""
        controller = next((attr for attr in self.device.remote_attributes.values() if attr.name == "controller"), None)
        position = next((attr for attr in controller.remote_attributes.values() if attr.name == "position"), None)
        setpoint_attr = next((attr for attr in position.remote_attributes.values() if attr.name == "setpoint"), None)

        # Endpoint function name should be avlos_ + full_name with underscores
        self.assertEqual(setpoint_attr.endpoint_function_name, "avlos_controller_position_setpoint")


class TestTinymovr_CodeGeneration(unittest.TestCase):
    """Test code generation from Tinymovr specification."""

    @classmethod
    def setUpClass(cls):
        """Load the Tinymovr specification once for all tests."""
        def_path_str = str(importlib.resources.files("tests").joinpath("definition/tinymovr_2_3_x.yaml"))

        with open(def_path_str) as device_desc_stream:
            cls.device = deserialize(yaml.safe_load(device_desc_stream))

    def test_c_generation_succeeds(self):
        """Test that C code generation completes without errors."""
        output_impl = str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test.c"))

        config = {
            "hash_string": "0xTINYMOVR",
            "paths": {
                "output_enums": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_enum.h")),
                "output_header": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_header.h")),
                "output_impl": output_impl,
            },
        }

        # Should not raise any exceptions
        generator_c.process(self.device, config)

        # Verify files were created
        self.assertTrue(os.path.exists(output_impl))
        self.assertTrue(os.path.exists(config["paths"]["output_enums"]))
        self.assertTrue(os.path.exists(config["paths"]["output_header"]))

    def test_generated_c_contains_endpoint_functions(self):
        """Test that generated C code contains endpoint functions."""
        output_impl = str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test.c"))

        config = {
            "hash_string": "0xTINYMOVR",
            "paths": {
                "output_enums": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_enum.h")),
                "output_header": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_header.h")),
                "output_impl": output_impl,
            },
        }

        generator_c.process(self.device, config)

        with open(output_impl) as f:
            content = f.read()

        # Check for root-level endpoint functions
        self.assertIn("avlos_protocol_hash", content)
        self.assertIn("avlos_uid", content)
        self.assertIn("avlos_fw_version", content)

        # Check for nested endpoint functions
        self.assertIn("avlos_controller_state", content)
        self.assertIn("avlos_controller_position_setpoint", content)

        # Check for function endpoints
        self.assertIn("avlos_reset", content)
        self.assertIn("avlos_controller_calibrate", content)

    def test_generated_c_contains_enums(self):
        """Test that generated C code contains enum definitions."""
        output_enum = str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_enum.h"))

        config = {
            "hash_string": "0xTINYMOVR",
            "paths": {
                "output_enums": output_enum,
                "output_header": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_header.h")),
                "output_impl": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test.c")),
            },
        }

        generator_c.process(self.device, config)

        with open(output_enum) as f:
            content = f.read()

        # Check for enum type definitions
        self.assertIn("typedef enum", content)

        # Check for specific enum values
        self.assertIn("CONTROLLER_STATE_IDLE", content)
        self.assertIn("CONTROLLER_STATE_CALIBRATE", content)
        self.assertIn("CONTROLLER_MODE_CURRENT", content)
        self.assertIn("CONTROLLER_MODE_VELOCITY", content)

    def test_generated_c_contains_bitmasks(self):
        """Test that generated C code contains bitmask definitions."""
        output_enum = str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_enum.h"))

        config = {
            "hash_string": "0xTINYMOVR",
            "paths": {
                "output_enums": output_enum,
                "output_header": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_header.h")),
                "output_impl": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test.c")),
            },
        }

        generator_c.process(self.device, config)

        with open(output_enum) as f:
            content = f.read()

        # Check for bitmask definitions
        self.assertIn("ERRORS_UNDERVOLTAGE", content)
        self.assertIn("WARNINGS_DRIVER_FAULT", content)

    def test_generated_c_contains_string_helpers(self):
        """Test that generated C code contains string helper functions."""
        output_impl = str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test.c"))

        config = {
            "hash_string": "0xTINYMOVR",
            "paths": {
                "output_enums": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_enum.h")),
                "output_header": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_header.h")),
                "output_impl": output_impl,
            },
        }

        generator_c.process(self.device, config)

        with open(output_impl) as f:
            content = f.read()

        # Should contain string helper functions (since fw_version is string type)
        self.assertIn("_avlos_getter_string", content)

    def test_generated_c_endpoint_array(self):
        """Test that generated C code contains the endpoint array."""
        output_impl = str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test.c"))

        config = {
            "hash_string": "0xTINYMOVR",
            "paths": {
                "output_enums": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_enum.h")),
                "output_header": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_header.h")),
                "output_impl": output_impl,
            },
        }

        generator_c.process(self.device, config)

        with open(output_impl) as f:
            content = f.read()

        # Should have endpoint array
        self.assertIn("avlos_endpoints[", content)

        # Should have proto hash function
        self.assertIn("_avlos_get_proto_hash", content)

    def test_cpp_generation_succeeds(self):
        """Test that C++ code generation completes without errors."""
        config = {
            "hash_string": "0xTINYMOVR",
            "paths": {
                "output_helpers": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_helpers.hpp")),
                "output_header": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test.hpp")),
                "output_impl": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test.cpp")),
            },
        }

        # Should not raise any exceptions
        generator_cpp.process(self.device, config)

        # Verify files were created
        self.assertTrue(os.path.exists(config["paths"]["output_helpers"]))
        self.assertTrue(os.path.exists(config["paths"]["output_header"]))
        self.assertTrue(os.path.exists(config["paths"]["output_impl"]))

    def test_generated_cpp_contains_classes(self):
        """Test that generated C++ code contains class definitions."""
        output_header = str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test.hpp"))

        config = {
            "hash_string": "0xTINYMOVR",
            "paths": {
                "output_helpers": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test_helpers.hpp")),
                "output_header": output_header,
                "output_impl": str(importlib.resources.files("tests").joinpath("outputs/tinymovr_test.cpp")),
            },
        }

        generator_cpp.process(self.device, config)

        with open(output_header) as f:
            content = f.read()

        # Should contain class definitions
        self.assertIn("class", content)

    def test_attribute_index_generation(self):
        """Test that attribute indices are generated correctly."""

        # Get all attributes as a flat list (including nested groups)
        def get_all_attrs(obj, attrs_list=None):
            if attrs_list is None:
                attrs_list = []
            for attr in obj.remote_attributes.values():
                # Add this attribute to the list
                attrs_list.append(attr)
                # If it has nested attributes, recursively get those too
                if hasattr(attr, "remote_attributes"):
                    get_all_attrs(attr, attrs_list)
            return attrs_list

        all_attrs = get_all_attrs(self.device)

        # Each attribute should have an ep_id
        ep_ids = [attr.ep_id for attr in all_attrs if hasattr(attr, "ep_id") and attr.ep_id >= 0]

        # Should have many endpoints (Tinymovr has over 70 endpoints)
        self.assertGreater(len(ep_ids), 70)

        # All ep_ids should be unique
        self.assertEqual(len(ep_ids), len(set(ep_ids)))

        # ep_ids should start from 0
        self.assertEqual(min(ep_ids), 0)

        # ep_ids should be consecutive
        self.assertEqual(max(ep_ids), len(ep_ids) - 1)


if __name__ == "__main__":
    unittest.main()
