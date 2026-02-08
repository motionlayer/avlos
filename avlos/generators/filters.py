import os
from copy import copy
from typing import List

from avlos.datatypes import DataType

# Avlos_Dtype enum names for metadata (reduced set for UART/ASCII parsing)
_AVLOS_DTYPE_MAP = {
    DataType.VOID: "AVLOS_DTYPE_VOID",
    DataType.BOOL: "AVLOS_DTYPE_BOOL",
    DataType.UINT8: "AVLOS_DTYPE_UINT8",
    DataType.INT8: "AVLOS_DTYPE_UINT8",
    DataType.UINT16: "AVLOS_DTYPE_UINT32",
    DataType.INT16: "AVLOS_DTYPE_INT32",
    DataType.UINT32: "AVLOS_DTYPE_UINT32",
    DataType.INT32: "AVLOS_DTYPE_INT32",
    DataType.UINT64: "AVLOS_DTYPE_UINT32",
    DataType.INT64: "AVLOS_DTYPE_INT32",
    DataType.FLOAT: "AVLOS_DTYPE_FLOAT",
    DataType.DOUBLE: "AVLOS_DTYPE_FLOAT",
    DataType.STR: "AVLOS_DTYPE_STRING",
}


def avlos_endpoints(input) -> List:
    """
    Traverse remote dictionary and return list of remote endpoints.

    Recursively walks the tree of RemoteNode objects and collects all endpoint
    objects (those with getter_name, setter_name, or caller_name).

    Args:
        input: Root RemoteNode to traverse

    Returns:
        Flat list of all endpoint objects found in the tree
    """

    def traverse_endpoint_list(ep_list, ep_out_list: List) -> None:
        """Helper function to recursively traverse endpoint tree."""
        for ep in ep_list:
            if hasattr(ep, "getter_name") or hasattr(ep, "setter_name") or hasattr(ep, "caller_name"):
                ep_out_list.append(ep)
            elif hasattr(ep, "remote_attributes"):
                traverse_endpoint_list(ep.remote_attributes.values(), ep_out_list)

    ep_out_list: List = []
    if hasattr(input, "remote_attributes"):
        traverse_endpoint_list(input.remote_attributes.values(), ep_out_list)
    return ep_out_list


def avlos_enum_eps(input) -> List:
    """
    Traverse remote dictionary and return a list of enum type endpoints.

    Args:
        input: Root RemoteNode to traverse

    Returns:
        List of RemoteEnum objects
    """
    return [ep for ep in avlos_endpoints(input) if hasattr(ep, "options")]


def avlos_bitmask_eps(input) -> List:
    """
    Traverse remote dictionary and return a list of bitmask type endpoints.

    Args:
        input: Root RemoteNode to traverse

    Returns:
        List of RemoteBitmask objects
    """
    return [ep for ep in avlos_endpoints(input) if hasattr(ep, "bitmask")]


def as_include(input: str) -> str:
    """
    Render a string as a C include, with opening and closing braces or quotation marks.

    If the input already has proper include delimiters, returns unchanged.
    Otherwise, wraps in angle brackets.

    Args:
        input: Include path string

    Returns:
        Properly formatted include directive (e.g., "<stdio.h>" or '"myheader.h"')
    """
    if input.startswith('"') and input.endswith('"'):
        return input
    elif input.startswith("<") and input.endswith(">"):
        return input
    return "<" + input + ">"


def file_from_path(input: str) -> str:
    """
    Get the file string from a path string.

    Args:
        input: File path

    Returns:
        Base filename without directory path
    """
    return os.path.basename(input)


def capitalize_first(input: str) -> str:
    """
    Capitalize the first character of a string, leaving the rest unchanged.

    Args:
        input: String to capitalize

    Returns:
        String with first character capitalized
    """
    return input[0].upper() + input[1:]


def avlos_ep_kind(ep) -> str:
    """
    Return the Avlos_EndpointKind enum name for an endpoint (for metadata generation).

    Args:
        ep: Endpoint object (RemoteAttribute, RemoteFunction, RemoteEnum, or RemoteBitmask)

    Returns:
        String like AVLOS_EP_KIND_READ_ONLY, AVLOS_EP_KIND_CALL_WITH_ARGS, etc.
    """
    has_getter = getattr(ep, "getter_name", None) is not None
    has_setter = getattr(ep, "setter_name", None) is not None
    has_caller = getattr(ep, "caller_name", None) is not None
    if has_caller:
        num_args = len(getattr(ep, "arguments", None) or [])
        if num_args == 0:
            return "AVLOS_EP_KIND_CALL_NO_ARGS"
        return "AVLOS_EP_KIND_CALL_WITH_ARGS"
    if has_getter and has_setter:
        return "AVLOS_EP_KIND_READ_WRITE"
    if has_getter:
        return "AVLOS_EP_KIND_READ_ONLY"
    if has_setter:
        return "AVLOS_EP_KIND_WRITE_ONLY"
    return "AVLOS_EP_KIND_READ_ONLY"  # fallback


def avlos_metadata_dtype(value) -> str:
    """
    Map a DataType or an object with .dtype (endpoint or argument) to Avlos_Dtype enum name.

    Used for value_dtype and arg_dtypes in endpoint metadata. Narrowing (e.g. 64-bit to
    32-bit) is applied where the metadata enum set is smaller than DataType.

    Args:
        value: Either a DataType enum member or an object with a .dtype attribute (endpoint, argument)

    Returns:
        String like AVLOS_DTYPE_UINT32, AVLOS_DTYPE_FLOAT, etc.
    """
    dtype = getattr(value, "dtype", value)
    try:
        return _AVLOS_DTYPE_MAP[dtype]
    except KeyError:
        return "AVLOS_DTYPE_UINT32"  # safe fallback
