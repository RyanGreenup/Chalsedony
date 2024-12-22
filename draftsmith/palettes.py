from PySide6.QtGui import QColor, QPalette


def create_light_palette() -> QPalette:
    """
    A Light palette based on the Latte theme by https://catppuccin.com/palette
    """
    palette = QPalette()

    colors = {
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

    # Set the palette colors for dark theme
    palette.setColor(QPalette.ColorRole.Window, QColor(colors["Base"]["Hex"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors["Surface 0"]["Hex"]))
    palette.setColor(
        QPalette.ColorRole.AlternateBase, QColor(colors["Surface 1"]["Hex"])
    )
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["Surface 2"]["Hex"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors["Subtext 0"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors["Crust"]["Hex"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(colors["Red"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Link, QColor(colors["Blue"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["Sapphire"]["Hex"]))
    palette.setColor(
        QPalette.ColorRole.HighlightedText, QColor(colors["Surface 0"]["Hex"])
    )
    palette.setColor(QPalette.ColorRole.Shadow, QColor(colors["Surface 2"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Midlight, QColor(colors["Surface 1"]["Hex"]))

    return palette


def create_dark_palette() -> QPalette:
    """
    A Dark palette based on the Mocha theme by https://catppuccin.com/palette
    """
    palette = QPalette()

    colors = {
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

    # Set the palette colors for a mocha theme
    palette.setColor(QPalette.ColorRole.Window, QColor(colors["Base"]["Hex"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(colors["Mantle"]["Hex"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["Crust"]["Hex"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["Surface 0"]["Hex"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(colors["Subtext 0"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(colors["Crust"]["Hex"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["Text"]["Hex"]))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(colors["Rosewater"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Link, QColor(colors["Blue"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["Sapphire"]["Hex"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["Base"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Shadow, QColor(colors["Surface 2"]["Hex"]))
    palette.setColor(QPalette.ColorRole.Midlight, QColor(colors["Surface 1"]["Hex"]))

    return palette
