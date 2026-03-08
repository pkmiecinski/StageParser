"""Data models for parsed stage/fixture data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Transform:
    """Position and rotation extracted from a 4x4 matrix."""

    # Position in millimeters (MVR convention)
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    # Rotation matrix (3x3 upper-left of the 4x4)
    rotation: list[list[float]] = field(default_factory=lambda: [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ])

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_mm": {"x": self.x, "y": self.y, "z": self.z},
            "rotation": self.rotation,
        }


@dataclass
class DmxAddress:
    """DMX address info for a fixture."""

    universe: int
    address: int  # 1-based channel within universe
    dmx_break: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "universe": self.universe,
            "address": self.address,
            "dmx_break": self.dmx_break,
        }


@dataclass
class ChannelInfo:
    """Single DMX channel description."""

    offset: list[int]  # byte offsets (e.g. [1,2] for 16-bit)
    attribute: str  # e.g. "Tilt", "Dimmer", "ColorAdd_R"
    geometry: str  # geometry this channel controls, e.g. "Head", "Pixel 1"
    default: int = 0
    dmx_break: int = 1
    bit_depth: int = 8  # 8 or 16

    def to_dict(self) -> dict[str, Any]:
        return {
            "offset": self.offset,
            "attribute": self.attribute,
            "geometry": self.geometry,
            "default": self.default,
            "dmx_break": self.dmx_break,
            "bit_depth": 8 * len(self.offset),
        }


@dataclass
class BeamInfo:
    """Light beam physical properties."""

    luminous_flux: float = 0.0  # lumens
    beam_angle: float = 0.0  # degrees
    field_angle: float = 0.0  # degrees
    color_temperature: float = 0.0  # Kelvin
    power_consumption: float = 0.0  # watts
    lamp_type: str = ""
    beam_type: str = ""
    color_rendering_index: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.luminous_flux:
            d["luminous_flux_lm"] = self.luminous_flux
        if self.beam_angle:
            d["beam_angle_deg"] = self.beam_angle
        if self.field_angle:
            d["field_angle_deg"] = self.field_angle
        if self.color_temperature:
            d["color_temperature_k"] = self.color_temperature
        if self.power_consumption:
            d["power_consumption_w"] = self.power_consumption
        if self.lamp_type:
            d["lamp_type"] = self.lamp_type
        if self.beam_type:
            d["beam_type"] = self.beam_type
        if self.color_rendering_index:
            d["color_rendering_index"] = self.color_rendering_index
        return d


@dataclass
class ModelDimensions:
    """3D model dimensions."""

    name: str = ""
    length: float = 0.0  # meters
    width: float = 0.0  # meters
    height: float = 0.0  # meters

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "length_m": self.length,
            "width_m": self.width,
            "height_m": self.height,
        }


@dataclass
class PhysicalInfo:
    """Physical properties of a fixture."""

    weight_kg: float = 0.0
    beams: list[BeamInfo] = field(default_factory=list)
    models: list[ModelDimensions] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.weight_kg:
            d["weight_kg"] = self.weight_kg
        if self.beams:
            d["beams"] = [b.to_dict() for b in self.beams]
        if self.models:
            d["models"] = [m.to_dict() for m in self.models]
        return d


@dataclass
class FixtureInfo:
    """Complete info for a single lighting fixture."""

    # Identity
    name: str = ""
    uuid: str = ""
    manufacturer: str = ""
    model: str = ""
    short_name: str = ""
    description: str = ""
    fixture_id: str = ""
    fixture_id_numeric: int = 0

    # GDTF
    gdtf_file: str = ""
    gdtf_mode: str = ""

    # DMX
    addresses: list[DmxAddress] = field(default_factory=list)
    channel_count: int = 0
    channels: list[ChannelInfo] = field(default_factory=list)

    # Transform
    transform: Transform = field(default_factory=Transform)

    # Physical
    physical: PhysicalInfo = field(default_factory=PhysicalInfo)

    @property
    def universe(self) -> int | None:
        """Primary universe number, or None if no address."""
        if self.addresses:
            return self.addresses[0].universe
        return None

    @property
    def address(self) -> int | None:
        """Primary DMX address (1-based), or None if no address."""
        if self.addresses:
            return self.addresses[0].address
        return None

    def channel_map(self) -> dict[int, str]:
        """Return {offset: attribute} mapping for quick lookup."""
        result: dict[int, str] = {}
        for ch in self.channels:
            for off in ch.offset:
                result[off] = ch.attribute
        return result

    def channels_by_geometry(self) -> dict[str, list[ChannelInfo]]:
        """Group channels by their geometry name."""
        groups: dict[str, list[ChannelInfo]] = {}
        for ch in self.channels:
            groups.setdefault(ch.geometry, []).append(ch)
        return groups

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "uuid": self.uuid,
            "manufacturer": self.manufacturer,
            "model": self.model,
        }
        if self.short_name:
            d["short_name"] = self.short_name
        if self.description:
            d["description"] = self.description
        if self.fixture_id:
            d["fixture_id"] = self.fixture_id
        if self.fixture_id_numeric:
            d["fixture_id_numeric"] = self.fixture_id_numeric

        d["gdtf_file"] = self.gdtf_file
        d["gdtf_mode"] = self.gdtf_mode
        d["addresses"] = [a.to_dict() for a in self.addresses]
        d["channel_count"] = self.channel_count
        d["channels"] = [c.to_dict() for c in self.channels]
        d["channel_map"] = self.channel_map()
        d["transform"] = self.transform.to_dict()

        phys = self.physical.to_dict()
        if phys:
            d["physical"] = phys

        return d


@dataclass
class StageData:
    """Top-level container for all parsed stage data."""

    mvr_file: str = ""
    mvr_version: str = ""
    provider: str = ""
    fixtures: list[FixtureInfo] = field(default_factory=list)

    def fixtures_by_universe(self) -> dict[int, list[FixtureInfo]]:
        """Group fixtures by their primary universe."""
        universes: dict[int, list[FixtureInfo]] = {}
        for f in self.fixtures:
            u = f.universe
            if u is not None:
                universes.setdefault(u, []).append(f)
        return universes

    def to_dict(self) -> dict[str, Any]:
        by_universe = self.fixtures_by_universe()
        return {
            "mvr_file": self.mvr_file,
            "mvr_version": self.mvr_version,
            "provider": self.provider,
            "universes": {
                str(u): [f.to_dict() for f in fixtures]
                for u, fixtures in sorted(by_universe.items())
            },
            "fixture_count": len(self.fixtures),
        }
