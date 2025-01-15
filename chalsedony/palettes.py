from typing import Any
from PySide6.QtGui import QColor, QPalette


class CustomPalette(QPalette):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.custom_colors: dict[str, QColor]


light_colors = {
    "Rosewater": {
        "Hex": "#dc8a78",
    },
    "Flamingo": {
        "Hex": "#dd7878",
    },
    "Pink": {
        "Hex": "#ea76cb",
    },
    "Mauve": {
        "Hex": "#8839ef",
    },
    "Red": {
        "Hex": "#d20f39",
    },
    "Maroon": {
        "Hex": "#e64553",
    },
    "Peach": {
        "Hex": "#fe640b",
    },
    "Yellow": {
        "Hex": "#df8e1d",
    },
    "Green": {
        "Hex": "#40a02b",
    },
    "Teal": {
        "Hex": "#179299",
    },
    "Sky": {
        "Hex": "#04a5e5",
    },
    "Sapphire": {
        "Hex": "#209fb5",
    },
    "Blue": {
        "Hex": "#1e66f5",
    },
    "Lavender": {
        "Hex": "#7287fd",
    },
    "Text": {
        "Hex": "#4c4f69",
    },
    "Subtext 1": {
        "Hex": "#5c5f77",
    },
    "Subtext 0": {
        "Hex": "#6c6f85",
    },
    "Overlay 2": {
        "Hex": "#7c7f93",
    },
    "Overlay 1": {
        "Hex": "#8c8fa1",
    },
    "Overlay 0": {
        "Hex": "#9ca0b0",
    },
    "Surface 2": {
        "Hex": "#acb0be",
    },
    "Surface 1": {
        "Hex": "#bcc0cc",
    },
    "Surface 0": {
        "Hex": "#ccd0da",
    },
    "Base": {
        "Hex": "#eff1f5",
    },
    "Mantle": {
        "Hex": "#e6e9ef",
    },
    "Crust": {
        "Hex": "#dce0e8",
    },
}

dark_colors = {
    "Rosewater": {
        "Hex": "#f5e0dc",
    },
    "Flamingo": {
        "Hex": "#f2cdcd",
    },
    "Pink": {
        "Hex": "#f5c2e7",
    },
    "Mauve": {
        "Hex": "#cba6f7",
    },
    "Red": {
        "Hex": "#f38ba8",
    },
    "Maroon": {
        "Hex": "#eba0ac",
    },
    "Peach": {
        "Hex": "#fab387",
    },
    "Yellow": {
        "Hex": "#f9e2af",
    },
    "Green": {
        "Hex": "#a6e3a1",
    },
    "Teal": {
        "Hex": "#94e2d5",
    },
    "Sky": {
        "Hex": "#89dceb",
    },
    "Sapphire": {
        "Hex": "#74c7ec",
    },
    "Blue": {
        "Hex": "#89b4fa",
    },
    "Lavender": {
        "Hex": "#b4befe",
    },
    "Text": {
        "Hex": "#cdd6f4",
    },
    "Subtext 1": {
        "Hex": "#bac2de",
    },
    "Subtext 0": {
        "Hex": "#a6adc8",
    },
    "Overlay 2": {
        "Hex": "#9399b2",
    },
    "Overlay 1": {
        "Hex": "#7f849c",
    },
    "Overlay 0": {
        "Hex": "#6c7086",
    },
    "Surface 2": {
        "Hex": "#585b70",
    },
    "Surface 1": {
        "Hex": "#45475a",
    },
    "Surface 0": {
        "Hex": "#313244",
    },
    "Base": {
        "Hex": "#1e1e2e",
    },
    "Mantle": {
        "Hex": "#181825",
    },
    "Crust": {
        "Hex": "#11111b",
    },
}


def create_palette(colors: dict[str, dict[str, str]]) -> CustomPalette:
    palette = CustomPalette()

    # Map QPalette roles to their corresponding color names
    role_color_map = {
        QPalette.ColorRole.Window: "Base",
        QPalette.ColorRole.WindowText: "Text",
        QPalette.ColorRole.Base: "Surface 0",
        QPalette.ColorRole.AlternateBase: "Surface 1",
        QPalette.ColorRole.ToolTipBase: "Surface 2",
        QPalette.ColorRole.ToolTipText: "Text",
        QPalette.ColorRole.Text: "Subtext 0",
        QPalette.ColorRole.Button: "Crust",
        QPalette.ColorRole.ButtonText: "Text",
        QPalette.ColorRole.BrightText: "Red",
        QPalette.ColorRole.Link: "Blue",
        QPalette.ColorRole.Highlight: "Sapphire",
        QPalette.ColorRole.HighlightedText: "Surface 0",
        QPalette.ColorRole.Shadow: "Surface 2",
        QPalette.ColorRole.Midlight: "Surface 1",
    }

    # Set palette colors using the mapping
    for role, color_name in role_color_map.items():
        palette.setColor(role, QColor(colors[color_name]["Hex"]))

    # Add our custom colors as a dictionary attribute
    # TODO these aren't in the dark theme
    custom_colors_dict = dict()
    for k, v in colors.items():
        custom_colors_dict[k] = QColor(v["Hex"])

    custom_colors_dict.update(
        {
            "Heading": QColor(colors["Text"]["Hex"]),
            "Subheading": QColor(colors["Subtext 0"]["Hex"]),
            "Background": QColor(colors["Surface 0"]["Hex"]),
        }
    )
    palette.custom_colors = custom_colors_dict

    return palette


def create_light_palette() -> CustomPalette:
    """
    A Light palette based on the Latte theme by https://catppuccin.com/palette
    """
    return create_palette(light_colors)


def create_dark_palette() -> CustomPalette:
    """
    A Dark palette based on the Mocha theme by https://catppuccin.com/palette
    """
    return create_palette(dark_colors)
