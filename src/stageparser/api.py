"""High-level programming API for querying stage data."""

from __future__ import annotations

from pathlib import Path

from stageparser.models import (
    BeamInfo,
    ChannelInfo,
    FixtureInfo,
    PhysicalInfo,
    StageData,
)
from stageparser.parser import parse_mvr


class Stage:
    """High-level API for querying parsed MVR stage data.

    Usage::

        stage = Stage("/path/to/venue.mvr")
        for u in stage.list_universes():
            for fixture in stage.list_fixtures(u):
                print(fixture.name, fixture.channel_count)
    """

    def __init__(self, mvr_path: str | Path) -> None:
        self._data: StageData = parse_mvr(mvr_path)

    @property
    def data(self) -> StageData:
        """Access the raw StageData."""
        return self._data

    @property
    def fixtures(self) -> list[FixtureInfo]:
        """All fixtures in the stage."""
        return self._data.fixtures

    # ── Universe queries ──────────────────────────────────────────

    def list_universes(self) -> list[int]:
        """Return sorted list of universe numbers that contain fixtures."""
        return sorted(self._data.fixtures_by_universe().keys())

    def list_fixtures(self, universe: int | None = None) -> list[FixtureInfo]:
        """List fixtures, optionally filtered by universe.

        Args:
            universe: If given, only return fixtures in that universe.
                      If None, return all fixtures.
        """
        if universe is None:
            return list(self._data.fixtures)
        by_u = self._data.fixtures_by_universe()
        return by_u.get(universe, [])

    def get_fixture(self, universe: int, address: int) -> FixtureInfo | None:
        """Get a fixture by its universe and start address.

        Args:
            universe: DMX universe number.
            address: DMX start address (1-based).

        Returns:
            FixtureInfo if found, None otherwise.
        """
        for f in self.list_fixtures(universe):
            if f.address == address:
                return f
        return None

    def get_fixture_by_uuid(self, uuid: str) -> FixtureInfo | None:
        """Get a fixture by its UUID."""
        for f in self._data.fixtures:
            if f.uuid == uuid:
                return f
        return None

    def get_fixture_by_name(self, name: str) -> list[FixtureInfo]:
        """Get all fixtures matching a name (case-insensitive)."""
        name_lower = name.lower()
        return [f for f in self._data.fixtures if name_lower in f.name.lower()]

    # ── Channel queries ───────────────────────────────────────────

    def get_channels(self, universe: int, address: int) -> list[ChannelInfo]:
        """Get channel list for a fixture at the given universe/address."""
        fixture = self.get_fixture(universe, address)
        if fixture is None:
            return []
        return fixture.channels

    def get_channel_map(self, universe: int, address: int) -> dict[int, str]:
        """Get {offset: attribute} map for a fixture."""
        fixture = self.get_fixture(universe, address)
        if fixture is None:
            return {}
        return fixture.channel_map()

    def get_channels_by_geometry(
        self, universe: int, address: int
    ) -> dict[str, list[ChannelInfo]]:
        """Get channels grouped by geometry for a fixture."""
        fixture = self.get_fixture(universe, address)
        if fixture is None:
            return {}
        return fixture.channels_by_geometry()

    # ── Physical queries ──────────────────────────────────────────

    def get_physical(self, universe: int, address: int) -> PhysicalInfo | None:
        """Get physical info for a fixture."""
        fixture = self.get_fixture(universe, address)
        if fixture is None:
            return None
        return fixture.physical

    def get_beams(self, universe: int, address: int) -> list[BeamInfo]:
        """Get beam info for a fixture."""
        fixture = self.get_fixture(universe, address)
        if fixture is None:
            return []
        return fixture.physical.beams

    def get_weight(self, universe: int, address: int) -> float:
        """Get weight in kg for a fixture (0.0 if unknown)."""
        fixture = self.get_fixture(universe, address)
        if fixture is None:
            return 0.0
        return fixture.physical.weight_kg

    def get_lumens(self, universe: int, address: int) -> float:
        """Get total luminous flux in lumens across all beams."""
        beams = self.get_beams(universe, address)
        return sum(b.luminous_flux for b in beams)

    # ── Summary ───────────────────────────────────────────────────

    def summary(self) -> dict:
        """Return a summary dict of the stage."""
        return {
            "mvr_file": self._data.mvr_file,
            "mvr_version": self._data.mvr_version,
            "provider": self._data.provider,
            "fixture_count": len(self._data.fixtures),
            "universes": self.list_universes(),
            "fixtures": [
                {
                    "name": f.name,
                    "manufacturer": f.manufacturer,
                    "model": f.model,
                    "universe": f.universe,
                    "address": f.address,
                    "channel_count": f.channel_count,
                }
                for f in self._data.fixtures
            ],
        }

    def to_dict(self) -> dict:
        """Full export as dict (structured by universe)."""
        return self._data.to_dict()
