"""Tests for bounding box transforming."""

from contextlib import nullcontext as does_not_raise
from typing import Any

import pytest
import typer
from parametrization import Parametrization as P

from pixel_map.__main__ import BboxGeometryParser


@P.parameters("value", "expectation")  # type: ignore
@P.case(
    "BBox with spaces",
    "7.41648, 43.73108, 7.42193, 43.73370",
    does_not_raise(),
)  # type: ignore
@P.case(
    "BBox without spaces",
    "7.41648,43.73108,7.42193,43.73370",
    does_not_raise(),
)  # type: ignore
@P.case(
    "Wrong BBox - str",
    "bounding_box",
    pytest.raises(typer.BadParameter),
)  # type: ignore
@P.case(
    "Wrong BBox - 3 floats",
    "7.41648,43.73108,7.42193",
    pytest.raises(typer.BadParameter),
)  # type: ignore
@P.case(
    "Wrong BBox - 3 floats, loose comma",
    "7.41648,43.73108,7.42193,",
    pytest.raises(typer.BadParameter),
)  # type: ignore
@P.case(
    "Wrong BBox - 5 floats",
    "7.41648,43.73108,7.42193,43.73370,7.41648",
    pytest.raises(typer.BadParameter),
)  # type: ignore
def test_bbox_loading(value: str, expectation: Any) -> None:
    """Test if extracts finding by name works."""
    with expectation:
        bbox = BboxGeometryParser().convert(value)  # type: ignore[no-untyped-call]
        assert len(bbox) == 4
        assert all(isinstance(v, float) for v in bbox)
