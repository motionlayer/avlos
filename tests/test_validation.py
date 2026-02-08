"""
Tests for validation module.
"""

import unittest

import yaml

from avlos.deserializer import deserialize
from avlos.validation import (
    C_RESERVED_WORDS,
    ValidationError,
    validate_all,
    validate_c_identifier,
    validate_endpoint_ids,
    validate_function_names,
    validate_names,
)


class TestValidation(unittest.TestCase):
    """Test validation functions."""

    def test_valid_c_identifier(self):
        """Test that valid C identifiers pass validation."""
        # These should not raise
        validate_c_identifier("valid_name")
        validate_c_identifier("_private")
        validate_c_identifier("name123")
        validate_c_identifier("CamelCase")
        validate_c_identifier("snake_case_123")

    def test_invalid_c_identifier_special_chars(self):
        """Test that identifiers with special characters are rejected."""
        with self.assertRaises(ValidationError) as cm:
            validate_c_identifier("invalid-name")
        self.assertIn("invalid-name", str(cm.exception))
        self.assertIn("Invalid C identifier", str(cm.exception))

        with self.assertRaises(ValidationError):
            validate_c_identifier("name with spaces")

        with self.assertRaises(ValidationError):
            validate_c_identifier("name.with.dots")

        with self.assertRaises(ValidationError):
            validate_c_identifier("name$special")

    def test_invalid_c_identifier_starts_with_digit(self):
        """Test that identifiers starting with digits are rejected."""
        with self.assertRaises(ValidationError) as cm:
            validate_c_identifier("123invalid")
        self.assertIn("123invalid", str(cm.exception))
        self.assertIn("Invalid C identifier", str(cm.exception))

    def test_c_reserved_words(self):
        """Test that C reserved words are rejected."""
        reserved_samples = [
            "int",
            "void",
            "return",
            "if",
            "else",
            "while",
            "for",
            "struct",
            "union",
            "enum",
            "static",
            "const",
            "_Bool",
        ]

        for word in reserved_samples:
            self.assertIn(word, C_RESERVED_WORDS)
            with self.assertRaises(ValidationError) as cm:
                validate_c_identifier(word)
            self.assertIn(word, str(cm.exception))
            self.assertIn("reserved word", str(cm.exception))

    def test_long_identifier_warning(self):
        """Test that very long identifiers generate warnings."""
        # 64+ character identifier (C99 requires at least 63 significant chars)
        long_name = "a" * 70
        # Should not raise; warning is logged (captured here so it does not print)
        with self.assertLogs("avlos", level="WARNING") as cm:
            validate_c_identifier(long_name)
        self.assertIn("very long", cm.output[0])
        self.assertIn("63 characters", cm.output[0])

    def test_valid_device_passes_all_validation(self):
        """Test that good_device.yaml passes all validations."""
        import importlib.resources

        def_path_str = str(importlib.resources.files("tests").joinpath("definition/good_device.yaml"))

        with open(def_path_str) as device_desc_stream:
            obj = deserialize(yaml.safe_load(device_desc_stream))
            errors = validate_all(obj)
            self.assertEqual(errors, [], f"good_device.yaml should pass validation but got: {errors}")

    def test_validate_endpoint_ids_no_conflicts(self):
        """Test endpoint ID validation with no conflicts."""
        import importlib.resources

        def_path_str = str(importlib.resources.files("tests").joinpath("definition/good_device.yaml"))

        with open(def_path_str) as device_desc_stream:
            obj = deserialize(yaml.safe_load(device_desc_stream))
            errors = validate_endpoint_ids(obj)
            self.assertEqual(errors, [], "Should have no endpoint ID conflicts")

    def test_validate_function_names_no_conflicts(self):
        """Test function name validation with no conflicts."""
        import importlib.resources

        def_path_str = str(importlib.resources.files("tests").joinpath("definition/good_device.yaml"))

        with open(def_path_str) as device_desc_stream:
            obj = deserialize(yaml.safe_load(device_desc_stream))
            errors = validate_function_names(obj)
            self.assertEqual(errors, [], "Should have no function name conflicts")

    def test_validate_names_valid(self):
        """Test name validation for valid device tree."""
        import importlib.resources

        def_path_str = str(importlib.resources.files("tests").joinpath("definition/good_device.yaml"))

        with open(def_path_str) as device_desc_stream:
            obj = deserialize(yaml.safe_load(device_desc_stream))
            errors = validate_names(obj)
            self.assertEqual(errors, [], "All names should be valid C identifiers")

    def test_invalid_getter_name_caught(self):
        """Test that invalid getter names are caught."""
        yaml_content = """
        name: test_device
        remote_attributes:
          - name: value
            summary: Test value
            dtype: uint32
            getter_name: invalid-getter-name
        """

        obj = deserialize(yaml.safe_load(yaml_content))
        errors = validate_function_names(obj)

        self.assertTrue(len(errors) > 0, "Should detect invalid getter name")
        self.assertTrue(any("invalid-getter-name" in err for err in errors))

    def test_invalid_setter_name_caught(self):
        """Test that invalid setter names are caught."""
        yaml_content = """
        name: test_device
        remote_attributes:
          - name: value
            summary: Test value
            dtype: uint32
            setter_name: invalid-setter
            getter_name: valid_getter
        """

        # Note: setter name "invalid-setter" has a dash which is invalid
        obj = deserialize(yaml.safe_load(yaml_content))
        errors = validate_function_names(obj)

        self.assertTrue(len(errors) > 0, "Should detect invalid setter name")

    def test_reserved_word_as_getter_name(self):
        """Test that C reserved words as getter names are caught."""
        yaml_content = """
        name: test_device
        remote_attributes:
          - name: value
            summary: Test value
            dtype: uint32
            getter_name: return
        """

        obj = deserialize(yaml.safe_load(yaml_content))
        errors = validate_function_names(obj)

        self.assertTrue(len(errors) > 0, "Should detect reserved word as getter name")
        self.assertTrue(any("reserved word" in err for err in errors))

    def test_invalid_node_name_caught(self):
        """Test that invalid node names are caught."""
        yaml_content = """
        name: invalid-device-name
        remote_attributes:
          - name: value
            summary: Test value
            dtype: uint32
            getter_name: get_value
        """

        obj = deserialize(yaml.safe_load(yaml_content))
        errors = validate_names(obj)

        self.assertTrue(len(errors) > 0, "Should detect invalid node name")
        self.assertTrue(any("invalid-device-name" in err for err in errors))

    def test_nested_invalid_node_name(self):
        """Test that invalid names in nested nodes are caught."""
        yaml_content = """
        name: device
        remote_attributes:
          - name: motor
            summary: Motor controller
            remote_attributes:
              - name: invalid-nested-name
                summary: Invalid nested attribute
                dtype: float
                getter_name: get_value
        """

        obj = deserialize(yaml.safe_load(yaml_content))
        errors = validate_names(obj)

        self.assertTrue(len(errors) > 0, "Should detect invalid nested node name")
        self.assertTrue(any("invalid-nested-name" in err for err in errors))

    def test_validation_error_with_context(self):
        """Test that validation errors include helpful context."""
        with self.assertRaises(ValidationError) as cm:
            validate_c_identifier("123bad", "test context")

        error_msg = str(cm.exception)
        self.assertIn("123bad", error_msg)
        self.assertIn("test context", error_msg)

    def test_validate_all_collects_multiple_errors(self):
        """Test that validate_all collects all errors, not just the first one."""
        yaml_content = """
        name: test-device
        remote_attributes:
          - name: attr-one
            summary: Test attribute
            dtype: uint32
            getter_name: invalid-getter
          - name: attr-two
            summary: Another test
            dtype: float
            setter_name: return
        """

        obj = deserialize(yaml.safe_load(yaml_content))
        errors = validate_all(obj)

        # Should have multiple errors:
        # - invalid device name (test-device)
        # - invalid attribute names (attr-one, attr-two)
        # - invalid getter name (invalid-getter)
        # - reserved word setter name (return)
        self.assertTrue(len(errors) >= 4, f"Should collect multiple errors, got {len(errors)}: {errors}")


if __name__ == "__main__":
    unittest.main()
