"""Core MVR/GDTF parser that extracts fixture data from MVR files."""

from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote

import pygdtf
import pymvr

from stageparser.models import (
    BeamInfo,
    ChannelInfo,
    DmxAddress,
    FixtureInfo,
    ModelDimensions,
    PhysicalInfo,
    StageData,
    Transform,
)


def _extract_transform(matrix: pymvr.value.Matrix) -> Transform:
    """Extract position and rotation from a pymvr 4x4 Matrix."""
    rows = matrix.matrix  # list[list[float]], 4x4
    return Transform(
        x=rows[3][0],
        y=rows[3][1],
        z=rows[3][2],
        rotation=[row[:3] for row in rows[:3]],
    )


def _parse_channels(gdtf: pygdtf.FixtureType, mode_name: str) -> tuple[int, list[ChannelInfo]]:
    """Parse DMX channels for a given mode from GDTF fixture type.

    Returns (channel_count, list_of_channels).
    """
    mode = None
    for m in gdtf.dmx_modes:
        if m.name == mode_name:
            mode = m
            break
    if mode is None:
        return 0, []

    channel_count = mode.dmx_channels_count
    channels: list[ChannelInfo] = []

    for ch in mode.dmx_channels:
        offset = ch.offset if ch.offset else []
        # Get attribute name - may be NodeLink or string, always coerce to str
        attribute = str(ch.attribute) if ch.attribute else ""
        if not attribute and ch.logical_channels:
            attribute = str(ch.logical_channels[0].attribute) if ch.logical_channels[0].attribute else ""

        default_val = 0
        if ch.default:
            try:
                default_val = int(ch.default.value)
            except (AttributeError, TypeError, ValueError):
                pass

        geometry = str(ch.geometry) if ch.geometry else ""

        channels.append(ChannelInfo(
            offset=offset,
            attribute=attribute,
            geometry=geometry,
            default=default_val,
            dmx_break=ch.dmx_break or 1,
            bit_depth=8 * len(offset),
        ))

    return channel_count, channels


def _parse_beams(gdtf: pygdtf.FixtureType) -> list[BeamInfo]:
    """Extract beam geometry data from GDTF fixture."""
    beams: list[BeamInfo] = []

    def _walk(geoms: list) -> None:
        for g in geoms:
            if isinstance(g, pygdtf.GeometryBeam):
                beams.append(BeamInfo(
                    luminous_flux=float(getattr(g, "luminous_flux", 0.0) or 0.0),
                    beam_angle=float(getattr(g, "beam_angle", 0.0) or 0.0),
                    field_angle=float(getattr(g, "field_angle", 0.0) or 0.0),
                    color_temperature=float(getattr(g, "color_temperature", 0.0) or 0.0),
                    power_consumption=float(getattr(g, "power_consumption", 0.0) or 0.0),
                    lamp_type=_safe_str(getattr(g, "lamp_type", "")),
                    beam_type=_safe_str(getattr(g, "beam_type", "")),
                    color_rendering_index=float(getattr(g, "color_rendering_index", 0.0) or 0.0),
                ))
            if hasattr(g, "geometries") and g.geometries:
                _walk(g.geometries)

    _walk(list(gdtf.geometries))
    return beams


def _safe_str(val: object) -> str:
    """Convert a value to string, handling enums and NodeLink objects."""
    if val is None:
        return ""
    if hasattr(val, "value") and hasattr(val, "name"):
        # Enum type
        return str(val.value) if val.value else str(val.name)
    return str(val)


def _parse_models(gdtf: pygdtf.FixtureType) -> list[ModelDimensions]:
    """Extract model dimensions from GDTF fixture."""
    models: list[ModelDimensions] = []
    for model in gdtf.models:
        if model.length or model.width or model.height:
            models.append(ModelDimensions(
                name=model.name or "",
                length=model.length or 0.0,
                width=model.width or 0.0,
                height=model.height or 0.0,
            ))
    return models


def _parse_physical(gdtf: pygdtf.FixtureType) -> PhysicalInfo:
    """Extract all physical properties from GDTF fixture."""
    weight = 0.0
    if gdtf.properties:
        weight = getattr(gdtf.properties, "weight", 0.0) or 0.0

    return PhysicalInfo(
        weight_kg=weight,
        beams=_parse_beams(gdtf),
        models=_parse_models(gdtf),
    )


def _collect_fixtures(child_list: pymvr.ChildList) -> list[pymvr.Fixture]:
    """Recursively collect all fixtures from an MVR child list."""
    fixtures: list[pymvr.Fixture] = []
    if hasattr(child_list, "fixtures"):
        fixtures.extend(child_list.fixtures)
    # Recurse into group objects
    if hasattr(child_list, "group_objects"):
        for group in child_list.group_objects:
            if hasattr(group, "child_list"):
                fixtures.extend(_collect_fixtures(group.child_list))
    # Recurse into trusses
    if hasattr(child_list, "trusses"):
        for truss in child_list.trusses:
            if hasattr(truss, "child_list"):
                fixtures.extend(_collect_fixtures(truss.child_list))
    return fixtures


def parse_mvr(mvr_path: str | Path) -> StageData:
    """Parse an MVR file and return structured stage data.

    Args:
        mvr_path: Path to the .mvr file.

    Returns:
        StageData with all fixtures, channels, and physical data.
    """
    mvr_path = Path(mvr_path)
    mvr = pymvr.GeneralSceneDescription(str(mvr_path))

    stage = StageData(
        mvr_file=mvr_path.name,
        mvr_version=f"{mvr.version_major}.{mvr.version_minor}",
        provider=mvr.provider or "",
    )

    # Cache GDTF parsing to avoid re-parsing the same fixture type
    gdtf_cache: dict[str, pygdtf.FixtureType | None] = {}

    # Collect all fixtures across all layers (recursive)
    all_mvr_fixtures: list[pymvr.Fixture] = []
    for layer in mvr.scene.layers:
        all_mvr_fixtures.extend(_collect_fixtures(layer.child_list))

    for fx in all_mvr_fixtures:
        info = FixtureInfo(
            name=fx.name or "",
            uuid=str(fx.uuid) if fx.uuid else "",
            fixture_id=fx.fixture_id or "",
            fixture_id_numeric=fx.fixture_id_numeric or 0,
            gdtf_file=unquote(fx.gdtf_spec) if fx.gdtf_spec else "",
            gdtf_mode=fx.gdtf_mode or "",
        )

        # DMX addresses
        if fx.addresses and fx.addresses.addresses:
            for addr in fx.addresses.addresses:
                info.addresses.append(DmxAddress(
                    universe=addr.universe or 0,
                    address=addr.address or 0,
                    dmx_break=addr.dmx_break or 0,
                ))

        # Transform
        if fx.matrix:
            info.transform = _extract_transform(fx.matrix)

        # Parse GDTF for detailed fixture data
        gdtf_spec = fx.gdtf_spec or ""
        if gdtf_spec and gdtf_spec not in gdtf_cache:
            try:
                with zipfile.ZipFile(str(mvr_path)) as z:
                    gdtf_data = z.read(gdtf_spec)
                # pygdtf needs a file path, write to temp
                with tempfile.NamedTemporaryFile(suffix=".gdtf", delete=False) as tmp:
                    tmp.write(gdtf_data)
                    tmp_path = tmp.name
                gdtf_cache[gdtf_spec] = pygdtf.FixtureType(tmp_path)
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                gdtf_cache[gdtf_spec] = None

        gdtf_ft = gdtf_cache.get(gdtf_spec)
        if gdtf_ft:
            info.manufacturer = gdtf_ft.manufacturer or ""
            info.model = gdtf_ft.long_name or gdtf_ft.name or ""
            info.short_name = gdtf_ft.short_name or ""
            info.description = gdtf_ft.description or ""

            # Channels for the specified mode
            info.channel_count, info.channels = _parse_channels(gdtf_ft, info.gdtf_mode)

            # Physical data
            info.physical = _parse_physical(gdtf_ft)

        stage.fixtures.append(info)

    return stage
