"""
Universal Pydantic to PyArrow Schema Converter for LanceDB.

This module provides a robust conversion utility that properly handles nested Pydantic
models within lists, which is a workaround for a bug in LanceDB 0.26.0.

The LanceDB library's `_pydantic_to_arrow_type` function incorrectly calls
`_py_type_to_arrow_type` for list child elements, which doesn't handle nested
Pydantic BaseModel types. This module fixes that by properly recursing into
Pydantic models at all nesting levels.

Key Features:
- Handles nested Pydantic models within lists
- Resolves forward references (string annotations like "ClassName")
- Supports both `list[T]` and `typing.List[T]` syntax
- Compatible with BAML-generated Pydantic models
- Handles Optional, Union, Dict, and other generic types

Usage:
    from pydantic_to_lance_db_schema import pydantic_to_arrow_schema
    from pydantic import BaseModel
    from lancedb.pydantic import LanceModel

    class NestedModel(BaseModel):
        value: str

    class MainModel(LanceModel):
        items: list[NestedModel]
        name: str

    # Get the correct PyArrow schema
    schema = pydantic_to_arrow_schema(MainModel)

    # Use with LanceDB
    db.create_table("my_table", schema=schema)

BAML Compatibility:
    # Works with BAML-generated types that use typing.List and forward refs
    from baml_client.types import BookConditionData
    schema = pydantic_to_arrow_schema(BookConditionData)
    db.create_table("books", schema=schema)
"""

from __future__ import annotations

import inspect
import sys
import types
from datetime import date, datetime
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    ForwardRef,
    GenericAlias,  # pyright: ignore[reportAttributeAccessIssue]
    List,
    Optional,
    Type,
    Union,
    _GenericAlias,  # type: ignore
    get_args,
    get_origin,
    get_type_hints,
)

import pyarrow as pa
from pydantic import BaseModel

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo


def _get_field_tz(field: FieldInfo) -> Optional[str]:
    """
    Extract timezone information from a Pydantic FieldInfo's json_schema_extra.

    Args:
        field: The Pydantic FieldInfo to inspect.

    Returns:
        The timezone string if specified, otherwise None.
    """
    if hasattr(field, "json_schema_extra") and field.json_schema_extra:
        if isinstance(field.json_schema_extra, dict):
            tz_value = field.json_schema_extra.get("tz")
            if isinstance(tz_value, str):
                return tz_value
    return None


def _python_type_to_arrow_type(
    py_type: Type[Any], field: Optional[FieldInfo] = None
) -> pa.DataType:
    """
    Convert a native Python type to a PyArrow DataType.

    This function handles primitive types and recursively processes generic types
    like list[T] and Optional[T]. Unlike the LanceDB implementation, this properly
    handles nested Pydantic models within lists.

    Args:
        py_type: The Python type to convert.
        field: Optional Pydantic FieldInfo for extracting additional metadata (e.g., timezone).

    Returns:
        The corresponding PyArrow DataType.

    Raises:
        TypeError: If the type cannot be converted to a PyArrow type.

    Examples:
        >>> _python_type_to_arrow_type(int)
        Int64Type(int64)
        >>> _python_type_to_arrow_type(str)
        StringType(string)
        >>> _python_type_to_arrow_type(list[str])
        ListType(list<item: string>)
    """
    # Handle None type
    if py_type is type(None):
        return pa.null()

    # Handle primitive types
    if py_type is int:
        return pa.int64()
    elif py_type is float:
        return pa.float64()
    elif py_type is str:
        return pa.utf8()
    elif py_type is bool:
        return pa.bool_()
    elif py_type is bytes:
        return pa.binary()
    elif py_type is date:
        return pa.date32()
    elif py_type is datetime:
        tz = _get_field_tz(field) if field else None
        return pa.timestamp("us", tz=tz)

    # Handle generic types (list, tuple, Optional, Union)
    origin = get_origin(py_type)
    args = get_args(py_type)

    if origin in (list, List):
        if args:
            child_type = args[0]
            # KEY FIX: Use pydantic_type_to_arrow_type for the child
            # This properly handles nested Pydantic models
            child_arrow_type = pydantic_type_to_arrow_type(child_type, field)
            return pa.list_(child_arrow_type)
        else:
            # Untyped list, default to string
            return pa.list_(pa.utf8())

    if origin in (tuple,):
        if args:
            child_type = args[0]
            child_arrow_type = pydantic_type_to_arrow_type(child_type, field)
            return pa.list_(child_arrow_type)
        else:
            return pa.list_(pa.utf8())

    if origin is Union:
        # Handle Optional[T] (which is Union[T, None])
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return pydantic_type_to_arrow_type(non_none_args[0], field)
        # For Union with multiple types, try to pick the first non-None type
        if non_none_args:
            return pydantic_type_to_arrow_type(non_none_args[0], field)

    # Handle Python 3.10+ union syntax (X | Y)
    if sys.version_info >= (3, 10) and isinstance(py_type, types.UnionType):
        args = py_type.__args__
        non_none_args = [arg for arg in args if arg is not type(None)]
        if non_none_args:
            return pydantic_type_to_arrow_type(non_none_args[0], field)

    # Handle Dict type
    if origin in (dict, Dict):
        if args and len(args) == 2:
            key_type = pydantic_type_to_arrow_type(args[0], field)
            value_type = pydantic_type_to_arrow_type(args[1], field)
            return pa.map_(key_type, value_type)
        else:
            return pa.map_(pa.utf8(), pa.utf8())

    raise TypeError(
        f"Cannot convert Python type to Arrow type: unsupported type {py_type}. "
        f"Supported types: int, float, str, bool, bytes, date, datetime, "
        f"list[T], tuple[T], Optional[T], Dict[K, V], and Pydantic BaseModel."
    )


def pydantic_type_to_arrow_type(
    tp: Any, field: Optional[FieldInfo] = None
) -> pa.DataType:
    """
    Convert a Pydantic type annotation to a PyArrow DataType.

    This function handles:
    - Primitive Python types (int, str, float, bool, bytes, date, datetime)
    - Generic types (list[T], tuple[T], Optional[T], Dict[K, V])
    - Nested Pydantic BaseModel classes (converted to PyArrow structs)
    - LanceDB Vector types (if available)
    - Forward references (string annotations like "MyModel")

    Args:
        tp: The type annotation to convert.
        field: Optional Pydantic FieldInfo for extracting additional metadata.

    Returns:
        The corresponding PyArrow DataType.

    Examples:
        >>> from pydantic import BaseModel
        >>> class Item(BaseModel):
        ...     name: str
        ...     value: int
        >>> pydantic_type_to_arrow_type(Item)
        StructType(struct<name: string, value: int64>)
        >>> pydantic_type_to_arrow_type(list[Item])
        ListType(list<item: struct<name: string, value: int64>>)
    """
    # Handle ForwardRef (string annotations like "MyClass")
    if isinstance(tp, (ForwardRef, str)):
        # Cannot resolve forward references without more context
        # This should not happen if we use get_type_hints properly
        raise TypeError(
            f"Unresolved forward reference: {tp}. "
            "Forward references should be resolved using get_type_hints() "
            "before calling this function."
        )

    # Check if it's a class
    if inspect.isclass(tp):
        # Handle Enum subclasses (convert to string in Arrow)
        if issubclass(tp, Enum):
            return pa.utf8()

        # Handle Pydantic BaseModel subclasses
        if issubclass(tp, BaseModel):
            # Convert to a PyArrow struct
            fields = _pydantic_model_to_arrow_fields(tp)
            return pa.struct(fields)

        # Handle LanceDB's FixedSizeListMixin (Vector types)
        try:
            from lancedb.pydantic import FixedSizeListMixin

            if issubclass(tp, FixedSizeListMixin):
                if getattr(tp, "is_multi_vector", lambda: False)():
                    return pa.list_(pa.list_(tp.value_arrow_type(), tp.dim()))
                return pa.list_(tp.value_arrow_type(), tp.dim())
        except ImportError:
            pass

    # Handle generic aliases (list[T], Optional[T], etc.)
    if isinstance(tp, (_GenericAlias, GenericAlias)):
        origin = getattr(tp, "__origin__", None)
        args = getattr(tp, "__args__", ())

        if origin is list:
            if args:
                child = args[0]
                # KEY FIX: Recursively handle nested types including Pydantic models
                # Check if child is a ForwardRef and warn
                if isinstance(child, (ForwardRef, str)):
                    raise TypeError(
                        f"Unresolved forward reference in list: {child}. "
                        "Ensure get_type_hints() is used to resolve forward references."
                    )
                child_arrow_type = pydantic_type_to_arrow_type(child, field)
                return pa.list_(child_arrow_type)
            else:
                # Untyped list, default to string
                return pa.list_(pa.utf8())

        elif origin is Union:
            # Handle Optional[T] (Union[T, None])
            non_none_args = [arg for arg in args if arg is not type(None)]
            if non_none_args:
                return pydantic_type_to_arrow_type(non_none_args[0], field)

        elif origin is dict:
            if len(args) == 2:
                key_type = pydantic_type_to_arrow_type(args[0], field)
                value_type = pydantic_type_to_arrow_type(args[1], field)
                return pa.map_(key_type, value_type)

    # Handle Python 3.10+ union syntax (X | Y)
    if sys.version_info >= (3, 10) and isinstance(tp, types.UnionType):
        args = tp.__args__
        non_none_args = [arg for arg in args if arg is not type(None)]
        if non_none_args:
            return pydantic_type_to_arrow_type(non_none_args[0], field)

    # Fall back to primitive type conversion
    # Cast to Type[Any] to handle edge cases
    return _python_type_to_arrow_type(tp, field)  # type: ignore[arg-type]


def _is_nullable_field(field: FieldInfo, resolved_type: Optional[Type] = None) -> bool:
    """
    Determine if a Pydantic field is nullable.

    A field is nullable if:
    - It's annotated as Optional[T] (i.e., Union[T, None])
    - It uses Python 3.10+ union syntax with None (T | None)
    - It's a LanceDB Vector type with nullable=True
    - The field has a default value of None

    Args:
        field: The Pydantic FieldInfo to check.
        resolved_type: Optional pre-resolved type hint (from get_type_hints).
                      If provided, this takes precedence over field.annotation.

    Returns:
        True if the field is nullable, False otherwise.
    """
    # Use resolved_type if provided, otherwise fall back to field.annotation
    annotation = resolved_type if resolved_type is not None else field.annotation

    # Check if the field has a default value of None (indicates nullable)
    if field.default is None and field.is_required() is False:
        return True

    # Handle generic aliases (Union, Optional) - typing.Optional[T] = Union[T, None]
    if isinstance(annotation, (_GenericAlias, GenericAlias)):
        origin = getattr(annotation, "__origin__", None)
        args = getattr(annotation, "__args__", ())

        if origin is Union:
            # Check if None is in the union args
            return type(None) in args

    # Handle Python 3.10+ union syntax (X | Y | None)
    if sys.version_info >= (3, 10) and isinstance(annotation, types.UnionType):
        return type(None) in annotation.__args__

    # Handle LanceDB Vector types
    if inspect.isclass(annotation):
        try:
            from lancedb.pydantic import FixedSizeListMixin

            if issubclass(annotation, FixedSizeListMixin):
                # Use hasattr to check if nullable method exists
                if hasattr(annotation, "nullable") and callable(annotation.nullable):  # type: ignore[attr-defined]
                    return annotation.nullable()  # type: ignore[attr-defined]
        except ImportError:
            pass

    return False


def _pydantic_field_to_arrow_field(
    name: str, field: FieldInfo, resolved_type: Optional[Type] = None
) -> pa.Field:
    """
    Convert a Pydantic field to a PyArrow Field.

    Args:
        name: The field name.
        field: The Pydantic FieldInfo object.
        resolved_type: Optional pre-resolved type (from get_type_hints) to handle forward refs.

    Returns:
        A PyArrow Field with the correct type and nullability.
    """
    # Use resolved type if provided, otherwise use field annotation
    type_to_convert = resolved_type if resolved_type is not None else field.annotation
    arrow_type = pydantic_type_to_arrow_type(type_to_convert, field)
    # Pass resolved_type to _is_nullable_field for proper nullability detection
    nullable = _is_nullable_field(field, resolved_type)
    return pa.field(name, arrow_type, nullable=nullable)


def _pydantic_model_to_arrow_fields(
    model: Type[BaseModel],
) -> List[pa.Field]:
    """
    Convert all fields of a Pydantic model to PyArrow Fields.

    This function properly resolves forward references using get_type_hints()
    before converting to Arrow types. This is essential for handling BAML-generated
    models that use typing.List["ClassName"] syntax.

    Args:
        model: The Pydantic BaseModel class to convert.

    Returns:
        A list of PyArrow Fields representing all model fields.
    """
    fields = []

    # Resolve all type hints to handle forward references
    # This converts typing.List[ForwardRef('PhysicalObservation')]
    # to typing.List[PhysicalObservation]
    try:
        resolved_hints = get_type_hints(model)
    except Exception as e:
        # If get_type_hints fails, fall back to raw annotations
        # This can happen if forward refs can't be resolved
        raise TypeError(
            f"Failed to resolve type hints for {model.__name__}: {e}. "
            "Make sure all referenced classes are defined and imported."
        ) from e

    for name, field_info in model.model_fields.items():
        # Use the resolved type hint if available
        resolved_type = resolved_hints.get(name)
        arrow_field = _pydantic_field_to_arrow_field(name, field_info, resolved_type)
        fields.append(arrow_field)

    return fields


def pydantic_to_arrow_schema(model: Type[BaseModel]) -> pa.Schema:
    """
    Convert a Pydantic BaseModel to a PyArrow Schema.

    This is the main entry point for converting Pydantic models to PyArrow schemas.
    It properly handles nested Pydantic models within lists, which is a fix for
    a bug in LanceDB 0.26.0.

    The function automatically resolves forward references using get_type_hints(),
    making it compatible with BAML-generated models that use typing.List["ClassName"]
    syntax.

    Args:
        model: The Pydantic BaseModel class to convert.

    Returns:
        A PyArrow Schema representing the Pydantic model.

    Raises:
        TypeError: If the model contains unresolvable forward references or
                   unsupported types.

    Examples:
        >>> from pydantic import BaseModel
        >>> from lancedb.pydantic import LanceModel
        >>>
        >>> class Item(BaseModel):
        ...     name: str
        ...     value: int
        ...
        >>> class Container(LanceModel):
        ...     items: list[Item]
        ...     description: str
        ...
        >>> schema = pydantic_to_arrow_schema(Container)
        >>> print(schema)
        items: list<item: struct<name: string, value: int64>>
        description: string

        # Works with BAML-generated types
        >>> from baml_client.types import BookConditionData
        >>> schema = pydantic_to_arrow_schema(BookConditionData)
        >>> # Successfully converts typing.List["PhysicalObservation"] fields

        # Works with typing.List syntax
        >>> from typing import List
        >>> class MyModel(BaseModel):
        ...     items: List[Item]  # typing.List works
        ...     tags: list[str]     # built-in list also works
        >>> schema = pydantic_to_arrow_schema(MyModel)
    """
    fields = _pydantic_model_to_arrow_fields(model)
    return pa.schema(fields)


class LanceModelSchemaOverride:
    """
    A mixin class that overrides the to_arrow_schema method for LanceModel classes.

    This class provides a proper implementation that handles nested Pydantic models
    within lists, fixing the bug in LanceDB 0.26.0.

    Usage:
        from lancedb.pydantic import LanceModel
        from pydantic_to_lance_db_schema import LanceModelSchemaOverride

        class MyModel(LanceModelSchemaOverride, LanceModel):
            items: list[NestedModel]
            name: str

        # Now create_table will work correctly
        db.create_table("my_table", schema=MyModel)
    """

    @classmethod
    def to_arrow_schema(cls) -> pa.Schema:
        """
        Convert the Pydantic model to an Arrow schema.

        This method uses the fixed pydantic_to_arrow_schema function
        that properly handles nested Pydantic models within lists.

        Returns:
            pa.Schema: The PyArrow schema for this model.
        """
        return pydantic_to_arrow_schema(cls)  # type: ignore[arg-type]


# Type mapping reference for documentation and debugging
PYTHON_TO_ARROW_TYPE_MAP: Dict[type, pa.DataType] = {
    int: pa.int64(),
    float: pa.float64(),
    str: pa.utf8(),
    bool: pa.bool_(),
    bytes: pa.binary(),
    date: pa.date32(),
    datetime: pa.timestamp("us"),
}


if __name__ == "__main__":
    import doctest

    doctest.testmod()
