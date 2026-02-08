"""
Pre-generation validation for Avlos code generation.
Validates C identifiers, detects conflicts, and ensures consistency.
"""

import logging
import re
from typing import List

_logger = logging.getLogger("avlos")

# C reserved words (C11 standard)
C_RESERVED_WORDS = {
    "auto",
    "break",
    "case",
    "char",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extern",
    "float",
    "for",
    "goto",
    "if",
    "int",
    "long",
    "register",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "struct",
    "switch",
    "typedef",
    "union",
    "unsigned",
    "void",
    "volatile",
    "while",
    "_Alignas",
    "_Alignof",
    "_Atomic",
    "_Bool",
    "_Complex",
    "_Generic",
    "_Imaginary",
    "_Noreturn",
    "_Static_assert",
    "_Thread_local",
}

C_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_c_identifier(name: str, context: str = "") -> None:
    """
    Validate that a name is a valid C identifier.

    Args:
        name: Identifier to validate
        context: Context string for error messages (e.g., "getter_name for motor.R")

    Raises:
        ValidationError: If identifier is invalid
    """
    if not C_IDENTIFIER_PATTERN.match(name):
        ctx = f" ({context})" if context else ""
        raise ValidationError(
            f"Invalid C identifier '{name}'{ctx}. "
            f"Must start with letter or underscore, contain only alphanumeric and underscore."
        )

    if name in C_RESERVED_WORDS:
        ctx = f" ({context})" if context else ""
        raise ValidationError(f"Invalid C identifier '{name}'{ctx}. '{name}' is a C reserved word.")

    if len(name) > 63:
        # C99 requires at least 63 significant characters for identifiers
        ctx = f" ({context})" if context else ""
        _logger.warning(
            "Identifier '%s'%s is very long (%d chars). " "Some compilers may truncate after 63 characters.",
            name,
            ctx,
            len(name),
        )


def validate_endpoint_ids(instance) -> List[str]:
    """
    Check for endpoint ID conflicts.

    Args:
        instance: Root node to validate

    Returns:
        List of error messages (empty if no conflicts)
    """
    from avlos.generators.filters import avlos_endpoints

    errors = []
    ep_id_map = {}

    for ep in avlos_endpoints(instance):
        ep_id = ep.ep_id
        if ep_id in ep_id_map:
            errors.append(f"Duplicate endpoint ID {ep_id}: " f"'{ep.full_name}' and '{ep_id_map[ep_id].full_name}'")
        else:
            ep_id_map[ep_id] = ep

    return errors


def validate_function_names(instance) -> List[str]:
    """
    Check for function name conflicts in generated C code.

    Args:
        instance: Root node to validate

    Returns:
        List of error messages (empty if no conflicts)
    """
    from avlos.generators.filters import avlos_endpoints

    errors = []

    # Check getter/setter/caller names are valid C identifiers
    for ep in avlos_endpoints(instance):
        if hasattr(ep, "getter_name") and ep.getter_name:
            try:
                validate_c_identifier(ep.getter_name, f"getter for {ep.full_name}")
            except ValidationError as e:
                errors.append(str(e))

        if hasattr(ep, "setter_name") and ep.setter_name:
            try:
                validate_c_identifier(ep.setter_name, f"setter for {ep.full_name}")
            except ValidationError as e:
                errors.append(str(e))

        if hasattr(ep, "caller_name") and ep.caller_name:
            try:
                validate_c_identifier(ep.caller_name, f"caller for {ep.full_name}")
            except ValidationError as e:
                errors.append(str(e))

    # Check for endpoint function name collisions
    # (endpoint functions are named: avlos_{full_name with dots replaced by underscores})
    endpoint_names = {}
    for ep in avlos_endpoints(instance):
        ep_func_name = "avlos_" + ep.full_name.replace(".", "_")
        if ep_func_name in endpoint_names:
            errors.append(
                f"Endpoint function name collision: '{ep_func_name}' "
                f"generated from both '{ep.full_name}' and '{endpoint_names[ep_func_name]}'"
            )
        else:
            endpoint_names[ep_func_name] = ep.full_name

    return errors


def validate_names(instance) -> List[str]:
    """
    Validate all names in the device tree are valid C identifiers.

    Args:
        instance: Root node to validate

    Returns:
        List of error messages (empty if all valid)
    """
    errors = []

    def traverse_nodes(node, path=""):
        # Validate node name
        current_path = f"{path}.{node.name}" if path else node.name
        try:
            # Node names become part of full_name which becomes C function name
            # So they should be valid C identifier parts
            validate_c_identifier(node.name, f"node name at {current_path}")
        except ValidationError as e:
            errors.append(str(e))

        # Recursively check children
        if hasattr(node, "remote_attributes"):
            for child in node.remote_attributes.values():
                traverse_nodes(child, current_path)

    traverse_nodes(instance)
    return errors


def validate_all(instance) -> List[str]:
    """
    Run all validations and return list of errors.

    Args:
        instance: Root node to validate

    Returns:
        List of all error messages (empty if validation passes)
    """
    errors = []

    # Collect all validation errors
    errors.extend(validate_names(instance))
    errors.extend(validate_endpoint_ids(instance))
    errors.extend(validate_function_names(instance))

    return errors
