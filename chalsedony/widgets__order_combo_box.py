from dataclasses import dataclass
from typing import final
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QWidget

from chalsedony.note_model import OrderField, OrderType


@dataclass
class Order:
    field: OrderField
    order_type: OrderType


@final
class OrderComboBox(QWidget):
    order_changed = Signal(Order)

    def __init__(self) -> None:
        super().__init__()

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Field selection combo
        self.field_combo = QComboBox()
        self.fields: dict[str, OrderField] = {
            field.value.replace("_", " ").capitalize(): field for field in OrderField
        }
        self.field_combo.addItems([f for f in self.fields.keys()])
        self.field_combo.setCurrentIndex(0)

        # Type selection combo
        self.type_combo = QComboBox()
        self.types: dict[str, OrderType] = {
            type_.value.capitalize(): type_ for type_ in OrderType
        }
        self.type_combo.addItems([t for t in self.types.keys()])
        self.type_combo.setCurrentIndex(0)

        # Add to layout
        layout.addWidget(self.field_combo)
        layout.addWidget(self.type_combo)

        # Connect signals
        self.field_combo.currentTextChanged.connect(self._on_order_changed)
        self.type_combo.currentTextChanged.connect(self._on_order_changed)

    def _on_order_changed(self, _: str) -> None:
        field = self.fields[self.field_combo.currentText()]
        order_type = self.types[self.type_combo.currentText()]
        self.order_changed.emit(Order(field, order_type))

    def current_order(self) -> Order:
        return Order(
            self.fields[self.field_combo.currentText()],
            self.types[self.type_combo.currentText()],
        )
