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
    This class assumes that every item is a TreeWidgetItem and has a unique ID.
    """
    def __init__(self, tree_widget: NoteTreeWidget) -> None:
        self.tree_widget = tree_widget
        self.selected_ids: List[str] = []
        self.fold_state: Dict[str, bool] = {}

    def save_state(self) -> None:
        """Save the current selection and expansion state of the tree"""
        self.selected_ids = self._get_selected_ids()
        self.fold_state = self._get_tree_fold_state()

    def restore_state(self, tree_widget: NoteTreeWidget | None = None) -> None:
        """Restore the saved selection and expansion state"""
        if tree_widget:
            self.tree_widget = tree_widget
        self._restore_selection()
        self._restore_fold_state()

    def _get_selected_ids(self) -> List[str]:
        """Get IDs of all selected items"""
        return [item.get_id() for item in self.tree_widget.selectedItems()]

    def _get_tree_fold_state(self) -> Dict[str, bool]:
        """Get expansion state of all items by their IDs"""
        state: Dict[str, bool] = {}
        
        def traverse(item: TreeWidgetItem) -> None:
            if item.childCount() > 0:
                state[item.get_id()] = item.isExpanded()
                for i in range(item.childCount()):
                    traverse(cast(TreeWidgetItem, item.child(i)))

        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            traverse(cast(TreeWidgetItem, root.child(i)))
        
        return state

    def _restore_selection(self) -> None:
        """Restore selection state using saved IDs"""
        for item_id in self.selected_ids:
            for stored_item in self.tree_widget.tree_items.items.values():
                if stored_item.get_id() == item_id:
                    stored_item.setSelected(True)
                    break

    def _restore_fold_state(self) -> None:
        """Restore expansion state using saved IDs"""
        for item_id, is_expanded in self.fold_state.items():
            for stored_item in self.tree_widget.tree_items.items.values():
                if stored_item.get_id() == item_id:
                    stored_item.setExpanded(is_expanded)
                    break
