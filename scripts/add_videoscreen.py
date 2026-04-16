#!/usr/bin/env python3
"""Inject a VideoScreen element into an MVR file.

Usage:
    python3 scripts/add_videoscreen.py /path/to/SimpleStage.mvr

Creates a backup (.mvr.bak) and writes the patched MVR in place.
"""

import shutil
import sys
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: add_videoscreen.py <mvr_file>")
        sys.exit(1)

    mvr_path = Path(sys.argv[1])
    if not mvr_path.exists():
        print(f"Error: {mvr_path} not found")
        sys.exit(1)

    # Backup
    backup = mvr_path.with_suffix(".mvr.bak")
    shutil.copy2(mvr_path, backup)
    print(f"Backup: {backup}")

    # Read MVR ZIP contents
    members: dict[str, bytes] = {}
    with zipfile.ZipFile(mvr_path, "r") as z:
        for name in z.namelist():
            members[name] = z.read(name)

    xml_name = "GeneralSceneDescription.xml"
    if xml_name not in members:
        print(f"Error: {xml_name} not found in MVR")
        sys.exit(1)

    # Parse XML
    tree = ET.ElementTree(ET.fromstring(members[xml_name]))
    root = tree.getroot()

    # Find the DMX layer's ChildList
    dmx_child_list = None
    for layer in root.iter("Layer"):
        if layer.get("name") == "DMX":
            dmx_child_list = layer.find("ChildList")
            break

    if dmx_child_list is None:
        print("Error: DMX layer not found")
        sys.exit(1)

    # --- VideoScreen parameters ---
    # Back wall at Y=6500
    # Fixtures span X: -6740 to 1200, Z: 650 to 1650
    # Center the screen between the dotlines
    center_x = (-6740 + 1200) / 2  # -2770
    center_y = 6500.0              # on the wall
    center_z = (650 + 1650) / 2    # 1150

    # Identity rotation (screen faces the camera, which looks at the back wall)
    matrix_str = (
        f"{{1,0,0}}"
        f"{{0,1,0}}"
        f"{{0,0,1}}"
        f"{{{center_x},{center_y},{center_z}}}"
    )

    screen_uuid = str(uuid.uuid4())

    # Build VideoScreen element
    vs = ET.SubElement(dmx_child_list, "VideoScreen",
                       name="Backdrop Projection",
                       uuid=screen_uuid)
    matrix_el = ET.SubElement(vs, "Matrix")
    matrix_el.text = matrix_str

    sources = ET.SubElement(vs, "Sources")
    source = ET.SubElement(sources, "Source",
                           linkedGeometry="",
                           type="NDI")
    source.text = "BackdropFeed"

    # Serialize XML
    ET.indent(tree, space="    ")
    xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=True)
    # ET writes <?xml version='1.0'... but MVR uses encoding='UTF-8'
    xml_bytes = xml_bytes.replace(
        "<?xml version='1.0' encoding='us-ascii'?>",
        "<?xml version='1.0' encoding='UTF-8'?>"
    )

    members[xml_name] = xml_bytes.encode("utf-8")

    # Write new MVR
    with zipfile.ZipFile(mvr_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)

    print(f"Added VideoScreen '{screen_uuid}' at ({center_x}, {center_y}, {center_z})")
    print(f"Written: {mvr_path}")


if __name__ == "__main__":
    main()
