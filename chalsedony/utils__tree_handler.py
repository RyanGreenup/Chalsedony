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
    def __init__(self, tree_widget: NoteTreeWidget) -> None:
        self.tree_widget = tree_widget
        self.selected_ids: List[str] = []
        self.fold_state: Dict[str, bool] = {}

    def save_state(self) -> None:
        """Save the current selection and fold states using item IDs"""
        self.selected_ids = self._get_selected_ids()
        self.fold_state = self._get_tree_fold_state(self.tree_widget.invisibleRootItem())

    def restore_state(self, tree_widget: NoteTreeWidget | None = None) -> None:
        """Restore the saved selection and fold states"""
        if tree_widget:
            self.tree_widget = tree_widget
        self._restore_selection()
        self._set_tree_fold_state(self.tree_widget.invisibleRootItem())

    def _get_tree_fold_state(self, parent: QTreeWidgetItem) -> Dict[str, bool]:
        """Get fold state for all items using their IDs as keys"""
        state: Dict[str, bool] = {}
        
        for i in range(parent.childCount()):
            child = cast(TreeWidgetItem, parent.child(i))
            if isinstance(child, TreeWidgetItem):
                item_id = child.get_id()
                index = self.tree_widget.indexFromItem(child)
                state[item_id] = self.tree_widget.isExpanded(index)
                
                # Recursively get state for children
                if child.childCount():
                    state.update(self._get_tree_fold_state(child))
        
        return state

    def _set_tree_fold_state(self, parent: QTreeWidgetItem) -> None:
        """Set fold state for all items using their IDs"""
        for i in range(parent.childCount()):
            child = cast(TreeWidgetItem, parent.child(i))
            if isinstance(child, TreeWidgetItem):
                item_id = child.get_id()
                if item_id in self.fold_state:
                    index = self.tree_widget.indexFromItem(child)
                    self.tree_widget.setExpanded(index, self.fold_state[item_id])
                
                if child.childCount():
                    self._set_tree_fold_state(child)

    def _get_selected_ids(self) -> List[str]:
        """Get IDs of all selected items"""
        selected_ids: List[str] = []
        for item in self.tree_widget.selectedItems():
            if isinstance(item, TreeWidgetItem):
                selected_ids.append(item.get_id())
        return selected_ids

    def _restore_selection(self) -> None:
        """Restore selection using saved IDs"""
        self.tree_widget.clearSelection()
        for item_id in self.selected_ids:
            item = self._find_item_by_id(self.tree_widget.invisibleRootItem(), item_id)
            if item:
                item.setSelected(True)

    def _find_item_by_id(self, parent: QTreeWidgetItem, item_id: str) -> TreeWidgetItem | None:
        """Find an item by its ID in the tree"""
        for i in range(parent.childCount()):
            child = cast(TreeWidgetItem, parent.child(i))
            if isinstance(child, TreeWidgetItem):
                if child.get_id() == item_id:
                    return child
                
                # Recursively search children
                if child.childCount():
                    if found := self._find_item_by_id(child, item_id):
                        return found
        return None
