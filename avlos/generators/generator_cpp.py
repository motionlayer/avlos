import os
import sys
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from avlos.formatting import format_c_code, is_clang_format_available
from avlos.generators.filters import avlos_bitmask_eps, avlos_enum_eps, capitalize_first, file_from_path
from avlos.validation import ValidationError, validate_all

env = Environment(loader=PackageLoader("avlos"), autoescape=select_autoescape())


def process(instance, config):
    # Validate config has required paths
    required_paths = ["output_helpers", "output_header", "output_impl"]
    if "paths" not in config:
        raise ValidationError(
            "Config validation failed: Missing 'paths' section in avlos config.\n"
            "Please add a 'paths' section with: output_helpers, output_header, output_impl"
        )

    missing_paths = [p for p in required_paths if p not in config["paths"]]
    if missing_paths:
        raise ValidationError(
            f"Config validation failed: Missing required paths in avlos config: {', '.join(missing_paths)}\n"
            f"Please add these paths to the 'paths' section of your avlos config file."
        )

    # Validate before generation
    validation_errors = validate_all(instance)
    if validation_errors:
        error_msg = "Validation failed:\n" + "\n".join(f"  - {err}" for err in validation_errors)
        raise ValidationError(error_msg)

    env.filters["enum_eps"] = avlos_enum_eps
    env.filters["bitmask_eps"] = avlos_bitmask_eps
    env.filters["file_from_path"] = file_from_path
    env.filters["capitalize_first"] = capitalize_first
    process_helpers(instance, config)
    process_header(instance, config)
    process_impl(instance, config)


def process_helpers(instance, config):
    template = env.get_template("tm_helpers.hpp.jinja")
    file_path = config["paths"]["output_helpers"]
    os.makedirs(os.path.dirname(config["paths"]["output_helpers"]), exist_ok=True)
    with open(file_path, "w") as output_file:
        print(
            template.render(instance=instance),
            file=output_file,
        )
    # Format the generated file
    format_c_code(file_path, config.get("format_style", "LLVM"))


def process_header(instance, config):
    template = env.get_template("device.hpp.jinja")
    file_path = config["paths"]["output_header"]
    helper_file = config["paths"]["output_helpers"]
    try:
        includes = config["header_includes"]
    except KeyError:
        includes = []
    os.makedirs(os.path.dirname(config["paths"]["output_header"]), exist_ok=True)
    with open(file_path, "w") as output_file:
        print(
            template.render(
                instance=instance,
                includes=includes,
                helper_file=helper_file,
                device_name=Path(config["paths"]["output_header"]).stem,
            ),
            file=output_file,
        )
    # Format the generated file
    format_c_code(file_path, config.get("format_style", "LLVM"))

    for attr in instance.remote_attributes.values():
        if hasattr(attr, "remote_attributes"):
            recurse_header(attr, config)


def recurse_header(remote_object, config):
    template = env.get_template("remote_object.hpp.jinja")
    file_path = os.path.join(
        os.path.dirname(config["paths"]["output_header"]),
        remote_object.name + ".hpp",
    )
    helper_file = config["paths"]["output_helpers"]
    os.makedirs(os.path.dirname(config["paths"]["output_header"]), exist_ok=True)
    with open(file_path, "w") as output_file:
        print(
            template.render(instance=remote_object, helper_file=helper_file),
            file=output_file,
        )
    # Format the generated file
    format_c_code(file_path, config.get("format_style", "LLVM"))

    for attr in remote_object.remote_attributes.values():
        if hasattr(attr, "remote_attributes"):
            recurse_header(attr, config)


def process_impl(instance, config):
    template = env.get_template("device.cpp.jinja")
    file_path = config["paths"]["output_impl"]
    try:
        includes = config["impl_includes"]
    except KeyError:
        includes = []
    includes.append(Path(config["paths"]["output_header"]).name)
    os.makedirs(os.path.dirname(config["paths"]["output_impl"]), exist_ok=True)
    with open(file_path, "w") as output_file:
        print(
            template.render(
                instance=instance,
                includes=includes,
                device_name=Path(config["paths"]["output_header"]).stem,
            ),
            file=output_file,
        )
    # Format the generated file
    format_c_code(file_path, config.get("format_style", "LLVM"))

    for attr in instance.remote_attributes.values():
        if hasattr(attr, "remote_attributes"):
            recurse_impl(attr, config)


def recurse_impl(remote_object, config):
    template = env.get_template("remote_object.cpp.jinja")
    file_path = os.path.join(
        os.path.dirname(config["paths"]["output_impl"]),
        remote_object.name + ".cpp",
    )
    os.makedirs(os.path.dirname(config["paths"]["output_impl"]), exist_ok=True)
    with open(file_path, "w") as output_file:
        print(template.render(instance=remote_object), file=output_file)
    # Format the generated file
    format_c_code(file_path, config.get("format_style", "LLVM"))

    for attr in remote_object.remote_attributes.values():
        if hasattr(attr, "remote_attributes"):
            recurse_impl(attr, config)
