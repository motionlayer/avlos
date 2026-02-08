import os
import sys

from jinja2 import Environment, PackageLoader, select_autoescape

from avlos.formatting import format_c_code, is_clang_format_available
from avlos.generators.filters import (
    as_include,
    avlos_bitmask_eps,
    avlos_endpoints,
    avlos_enum_eps,
    avlos_ep_kind,
    avlos_metadata_dtype,
)
from avlos.validation import ValidationError, validate_all

env = Environment(loader=PackageLoader("avlos"), autoescape=select_autoescape())


def _generate_metadata_if_requested(instance, config):
    """Generate endpoint metadata .h/.c when both paths are in config. Returns extra paths or []."""
    paths = config["paths"]
    if "output_metadata_header" not in paths or "output_metadata_impl" not in paths:
        return []
    meta_header_path = paths["output_metadata_header"]
    meta_impl_path = paths["output_metadata_impl"]
    metadata_header_basename = os.path.basename(meta_header_path)
    os.makedirs(os.path.dirname(meta_header_path), exist_ok=True)
    template_meta_h = env.get_template("avlos_endpoint_metadata.h.jinja")
    with open(meta_header_path, "w") as f:
        print(template_meta_h.render(), file=f)
    os.makedirs(os.path.dirname(meta_impl_path), exist_ok=True)
    template_meta_c = env.get_template("avlos_endpoint_metadata.c.jinja")
    with open(meta_impl_path, "w") as f:
        print(
            template_meta_c.render(
                instance=instance,
                metadata_header_basename=metadata_header_basename,
            ),
            file=f,
        )
    return [meta_header_path, meta_impl_path]


def process(instance, config):
    # Validate config has required paths
    required_paths = ["output_enums", "output_header", "output_impl"]
    if "paths" not in config:
        raise ValidationError(
            "Config validation failed: Missing 'paths' section in avlos config.\n"
            "Please add a 'paths' section with: output_enums, output_header, output_impl"
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

    env.filters["endpoints"] = avlos_endpoints
    env.filters["enum_eps"] = avlos_enum_eps
    env.filters["bitmask_eps"] = avlos_bitmask_eps
    env.filters["as_include"] = as_include
    env.filters["avlos_ep_kind"] = avlos_ep_kind
    env.filters["avlos_metadata_dtype"] = avlos_metadata_dtype

    template = env.get_template("tm_enums.h.jinja")
    os.makedirs(os.path.dirname(config["paths"]["output_enums"]), exist_ok=True)
    with open(config["paths"]["output_enums"], "w") as output_file:
        print(
            template.render(instance=instance),
            file=output_file,
        )

    template = env.get_template("fw_endpoints.h.jinja")
    try:
        includes = config["header_includes"]
    except KeyError:
        includes = []
    os.makedirs(os.path.dirname(config["paths"]["output_header"]), exist_ok=True)
    with open(config["paths"]["output_header"], "w") as output_file:
        print(
            template.render(instance=instance, includes=includes),
            file=output_file,
        )

    template = env.get_template("fw_endpoints.c.jinja")
    try:
        includes = config["impl_includes"]
    except KeyError:
        includes = []
    os.makedirs(os.path.dirname(config["paths"]["output_impl"]), exist_ok=True)
    with open(config["paths"]["output_impl"], "w") as output_file:
        print(
            template.render(instance=instance, includes=includes),
            file=output_file,
        )

    base_files = [
        config["paths"]["output_enums"],
        config["paths"]["output_header"],
        config["paths"]["output_impl"],
    ]
    generated_files = base_files + _generate_metadata_if_requested(instance, config)

    # Post-process with clang-format if available
    format_style = config.get("format_style", "LLVM")
    for file_path in generated_files:
        success = format_c_code(file_path, format_style)
        if not success and is_clang_format_available():
            print(f"Warning: clang-format failed for {file_path}", file=sys.stderr)
