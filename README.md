# StageParser

Parse **MVR** (My Virtual Rig) stage files and extract DMX fixture data, organized by universe. Built for automating venue configuration in TouchDesigner and Unreal Engine.

Uses [python-mvr](https://github.com/open-stage/python-mvr) for MVR parsing and [pygdtf](https://pypi.org/project/pygdtf/) for GDTF fixture data.

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone and install
git clone <repo-url>
cd StageParser
uv sync
```

## CLI Usage

```bash
# Full JSON output (organized by universe)
stageparser venue.mvr

# Summary view
stageparser venue.mvr --summary

# YAML output
stageparser venue.mvr -f yaml

# Filter by universe
stageparser venue.mvr -u 1

# Save to file
stageparser venue.mvr -o output.json
```

### Example Summary Output

```json
{
  "mvr_file": "SimpleStage.mvr",
  "mvr_version": "1.6",
  "provider": "pymvr",
  "fixture_count": 1,
  "universes": [1],
  "fixtures": [
    {
      "name": "TB 1230 QW",
      "manufacturer": "ACME",
      "model": "ACME DOTLINE360 (TB-1230 QW)",
      "universe": 1,
      "address": 1,
      "channel_count": 57
    }
  ]
}
```

## Programming API

```python
from stageparser import Stage

stage = Stage("venue.mvr")

# List universes
stage.list_universes()          # [1, 2, 3]

# List fixtures (all or by universe)
stage.list_fixtures()           # all fixtures
stage.list_fixtures(universe=1) # fixtures in universe 1

# Get specific fixture
fixture = stage.get_fixture(universe=1, address=1)
fixture.name            # "TB 1230 QW"
fixture.manufacturer    # "ACME"
fixture.model           # "ACME DOTLINE360 (TB-1230 QW)"
fixture.channel_count   # 57
fixture.gdtf_mode       # "Mode 1 57 DMX"

# Find fixtures by name
stage.get_fixture_by_name("dotline")  # case-insensitive search
stage.get_fixture_by_uuid("30b410fb-...")

# Channel data
fixture.channels                # list of ChannelInfo
fixture.channel_map()           # {1: "Tilt", 2: "Tilt", 3: "PT Speed", ...}
fixture.channels_by_geometry()  # {"Head": [...], "Pixel 1": [...], ...}

# Shorthand channel queries
stage.get_channels(1, 1)              # channels for universe 1, address 1
stage.get_channel_map(1, 1)           # {offset: attribute} dict
stage.get_channels_by_geometry(1, 1)  # channels grouped by geometry

# Position & rotation
fixture.transform.x   # mm (MVR convention)
fixture.transform.y
fixture.transform.z
fixture.transform.rotation  # 3x3 rotation matrix

# Physical data
fixture.physical.weight_kg
fixture.physical.beams        # list of BeamInfo
fixture.physical.models       # list of ModelDimensions

# Beam properties
for beam in fixture.physical.beams:
    beam.luminous_flux       # lumens
    beam.beam_angle          # degrees
    beam.color_temperature   # Kelvin
    beam.power_consumption   # watts
    beam.lamp_type
    beam.beam_type

# Shorthand physical queries
stage.get_lumens(1, 1)     # total lumens across all beams
stage.get_weight(1, 1)     # weight in kg
stage.get_physical(1, 1)   # full PhysicalInfo
stage.get_beams(1, 1)      # list of BeamInfo

# Full export
stage.to_dict()   # complete data organized by universe
stage.summary()   # brief overview
```

## Data Models

| Model | Description |
|---|---|
| `StageData` | Top-level container with all fixtures |
| `FixtureInfo` | Complete fixture: identity, DMX, channels, transform, physical |
| `ChannelInfo` | Single DMX channel: offset, attribute, geometry, bit depth |
| `DmxAddress` | Universe + address + break |
| `Transform` | Position (mm) + 3x3 rotation matrix |
| `PhysicalInfo` | Weight, beams, model dimensions |
| `BeamInfo` | Lumens, beam angle, color temp, power, lamp/beam type |
| `ModelDimensions` | Name, length, width, height (meters) |

## Channel Map

For the ACME DOTLINE360 in Mode 1 (57 DMX channels):

| Offset | Attribute | Geometry | Bit Depth |
|---|---|---|---|
| 1-2 | Tilt | Head | 16-bit |
| 3 | PT Speed | Head | 8-bit |
| 4 | Zoom | Array 1 | 8-bit |
| 5 | Zoom | Array 2 | 8-bit |
| 6-7 | Dimmer | Head | 16-bit |
| 8 | Shutter1 | Head | 8-bit |
| 9-32 | RGBW x 6 | Pixel 1-6 | 8-bit each |
| 33-56 | RGBW x 6 | Pixel 7-12 | 8-bit each |
| 57 | Function | Head | 8-bit |

## License

MIT
