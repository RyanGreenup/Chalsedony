from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from typing import List, Tuple, Dict, cast
from widgets__note_tree import NoteTreeWidget, TreeWidgetItem


class TreeStateHandler:
    def __init__(self, tree_widget: QTreeWidget) -> None:
        self.tree_widget = tree_widget
        self.selected_paths: List[Tuple[int, ...]] = []

    def save_state(self) -> None:
        self.selected_paths = self._get_selected_paths()
        self.fold_state: Dict[Tuple[int, ...], bool] = self._get_tree_fold_state(
            self.tree_widget.invisibleRootItem()
        )

    def restore_state(self, tree_widget: QTreeWidget | None) -> None:
        if tree_widget:
            self.tree_widget = tree_widget
        self._restore_selection()
        self._set_tree_fold_state(self.tree_widget.invisibleRootItem(), self.fold_state)

    def _get_tree_fold_state(
        self, parent: QTreeWidgetItem, path: Tuple[int, ...] = ()
    ) -> Dict[Tuple[int, ...], bool]:
        state: Dict[Tuple[int, ...], bool] = {}
        for i in range(parent.childCount()):
            child = parent.child(i)
            current_path = path + (i,)
            index = self.tree_widget.indexFromItem(child)
            state[current_path] = self.tree_widget.isExpanded(index)
            if child.childCount():
                state.update(self._get_tree_fold_state(child, current_path))
        return state

    def _set_tree_fold_state(
        self,
        parent: QTreeWidgetItem,
        state: Dict[Tuple[int, ...], bool],
        path: Tuple[int, ...] = (),
    ) -> None:
        for i in range(parent.childCount()):
            child = parent.child(i)
            current_path = path + (i,)
            if current_path in state:
                index = self.tree_widget.indexFromItem(child)
                self.tree_widget.setExpanded(index, state[current_path])
                if child.childCount():
                    self._set_tree_fold_state(child, state, current_path)

    def _get_selected_paths(self) -> List[Tuple[int, ...]]:
        """Returns a list of paths for the currently selected items."""
        selected_paths: List[Tuple[int, ...]] = []
        for item in self.tree_widget.selectedItems():
            path: List[int] = []
            while item:
                parent = item.parent()
                index = (
                    parent.indexOfChild(item)
                    if parent
                    else self.tree_widget.indexOfTopLevelItem(item)
                )
                path.append(index)
                item = parent
            selected_paths.append(tuple(reversed(path)))
        return selected_paths

    def _restore_selection(self) -> None:
        """Restore selection based on the stored paths."""
        for path in self.selected_paths:
            item = self._get_item_from_path(path)
            if item:
                item.setSelected(True)

    def _get_item_from_path(self, path: Tuple[int, ...]) -> QTreeWidgetItem | None:
        """Retrieve an item based on its path (indices) in the tree."""
        item = self.tree_widget.invisibleRootItem()
        for index in path:
            item = item.child(index)
            if item is None:
                return None
        return item


class NoteTreeStateHandler:
    """
    This class assumes that every item is a TreeeWidgetItem and has a unique ID.
    """
    def __init__(self, tree_widget: NoteTreeWidget) -> None:
        self.tree_widget = tree_widget
