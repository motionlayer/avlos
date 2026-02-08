Avlos Configuration
*******************

Device Spec
-----------

A Device Spec is a YAML file that outlines the attributes and functionalities of a device, serving as a blueprint for code generation with Avlos. It is structured as a hierarchical tree, with each node representing a specific feature or function of the device.

Structure of a Device Spec
^^^^^^^^^^^^^^^^^^^^^^^^^^

The top level of the spec typically starts with the `name` of the device. This is followed by `remote_attributes`, a list of attributes that describe various aspects of the device. Each attribute in this list can itself be a complex entity, often consisting of several key-value pairs:

- `name`: The name of the attribute.
- `dtype`: The data type of the attribute (e.g., `uint32`, `float`, `string`, `bool`).
- `unit` (optional): The unit of measurement, applicable for numerical data types (e.g., `volt`, `ampere`, `meter/s`).
- `meta` (optional): Metadata for the attribute, which can include flags like `dynamic` or `export`.
- `getter_name` / `setter_name`: The names of the getter and setter functions associated with the attribute.
- `summary` (optional): A brief description of the attribute.
- `flags` (optional): A list of specific flags relevant to the attribute (e.g., error types). This is useful to define bit fields that can represent specific conditions in the system.
- `options` (optional): Alternative to flags, a list of exclusive options like an enum. This is useful to enums that represent different system states.


Sub-attributes and Nested Structures
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Attributes can have nested `remote_attributes`, creating a tree-like structure. This is particularly useful for grouping related functionalities or aspects of the device, such as `scheduler`, `controller`, `motor`, etc. Each of these groupings can have its own set of attributes, mirroring the structure described above.

Functions
^^^^^^^^^

Besides standard attributes that behave like getters/setters, the spec can define functions for the device, such as `save_config`, `erase_config`, `reset`, etc. Functions can have a list of arguments, and can return a value. Functions are typically defined with:

- `name`: The name of the function.
- `summary` (optional): A brief description of the function.
- `caller_name`: The function prototype to call for this function endpoint.
- `dtype`: The return data type, often `void` for function.
- `arguments` (optional): A list of arguments for functions, each with its own `name` and `dtype`.
- `unit` (optional): The unit of measurement, applicable for numerical data types (e.g., `volt`, `ampere`, `meter/s`).
- `meta`: Metadata for the function, similar to attributes.

Implementing Your Own Device Spec
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To implement your own device spec for use with Avlos:

1. Define the device name at the top of the YAML file.
2. Enumerate the attributes (`remote_attributes`) of your device, following the structure described above.
3. For each attribute, specify its `name`, `dtype`, `getter_name`, `setter_name` (if applicable), `summary`, and any other relevant details.
4. Group related attributes under nested `remote_attributes` to create a clear, hierarchical structure.
5. Add any special actions or commands your device supports, with appropriate details.

This structured approach allows Avlos to understand the capabilities and interface of your device, enabling efficient and accurate code generation.


Output Config
-------------

The output config defines the output modules that will be used and their options. Example, showing C code generation for embedded devices:

.. code-block::

    generators:
        generator_c:
            enabled: true
            paths:
                output_enums: outputs/tm_enums.h
                output_header: outputs/header.h
                output_impl: outputs/header.c
            header_includes:
            - outputs/tm_enums.h
            impl_includes:
            - outputs/header.h

There are three main generated files that are configured above: A header containing enums (`output_enums`), a header containing function declarations (`output_header`), and an implementation containing function definitions (`output_impl`).

Optional: Endpoint metadata (for type-aware UART/ASCII parsing)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want the C generator to emit an endpoint type metadata table (so firmware can parse and format ASCII without a hand-maintained table), add both of these optional paths under ``paths``:

- ``output_metadata_header``: Path for the generated metadata header (e.g. ``fw/avlos_endpoint_metadata.h``).
- ``output_metadata_impl``: Path for the generated metadata implementation (e.g. ``fw/avlos_endpoint_metadata.c``).

When both are present, Avlos generates ``Avlos_EndpointMeta avlos_endpoint_meta[]`` and ``avlos_endpoint_meta_count`` in the same order as ``avlos_endpoints[]``. Each entry describes the endpoint kind (read-only, read-write, call with/without args), value type, and for callables the argument types. If either path is omitted, no metadata files are generated (backward compatible).

Of note is that no #include statements for the generated files are generated automatically. This is something that we decided in order to maximize compatibility to edge cases, but may be revised in future Avlos versions.

CLI Usage
---------

Using a Local File
^^^^^^^^^^^^^^^^^^

Ensure the device spec and the output config exist in the current folder.

.. code-block:: console

    avlos from file device.yaml

This will generate the outputs according to the configuration in the output config file.


Using a URL
^^^^^^^^^^^

Ensure the output config exists in the current folder.

.. code-block:: console

    avlos from url https://your.url/spec.yaml

This will generate the outputs according to the configuration in the output config file.
