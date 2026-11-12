import xml.etree.ElementTree as ET

def parse_qml_color_ramp(qml_path):
    """
    Parse a QGIS .qml file and extract the color ramp definition.

    Parameters
    ----------
    qml_path : str
        Path to the QML file.

    Returns
    -------
    list of dict
        Each entry is like:
        {
            "value": float,   # data value
            "color": (r, g, b, a)  # RGBA as 0–255 ints
        }
    """
    tree = ET.parse(qml_path)
    root = tree.getroot()

    items = []
    for item in root.findall(".//item"):
        value = float(item.get("value"))
        color_str = item.get("color")

        if "," in color_str:  # format: "r,g,b,a"
            color = tuple(map(int, color_str.split(",")))
        elif color_str.startswith("#"):  # format: "#rrggbb"
            hexval = color_str.lstrip("#")
            # Split into RGB
            r = int(hexval[0:2], 16)
            g = int(hexval[2:4], 16)
            b = int(hexval[4:6], 16)
            color = (r, g, b, 255)  # assume fully opaque
        else:
            raise ValueError(f"Unknown color format: {color_str}")

        items.append({"value": value, "color": color})

    return items


if __name__ == "__main__":
    qml_path = "/Users/valentinopapandrea/Desktop/University/GeoK/tif_comparison/01/IRIDE-S_S5-02-01_V0.qml"
    ramp = parse_qml_color_ramp(qml_path)
    for stop in ramp:
        print(stop)
