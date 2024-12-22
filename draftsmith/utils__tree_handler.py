from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem


class TreeStateHandler:
    def __init__(self, tree_widget: QTreeWidget):
        self.tree_widget = tree_widget
        self.selected_paths = []

    def save_state(self):
        self.selected_paths = self._get_selected_paths()
        self.fold_state = self._get_tree_fold_state(
            self.tree_widget.invisibleRootItem()
        )

    def restore_state(self, tree_widget: QTreeWidget | None):
        if tree_widget:
            self.tree_widget = tree_widget

        self._restore_selection()
        self._set_tree_fold_state(self.tree_widget.invisibleRootItem(), self.fold_state)

    def _get_tree_fold_state(self, parent: QTreeWidgetItem, path=()) -> dict:
        state = {}
        for i in range(parent.childCount()):
            child = parent.child(i)
            current_path = path + (i,)
            index = self.tree_widget.indexFromItem(child)
            state[current_path] = self.tree_widget.isExpanded(index)
            if child.childCount():
                state.update(self._get_tree_fold_state(child, current_path))
        return state

    def _set_tree_fold_state(self, parent: QTreeWidgetItem, state: dict, path=()):
        for i in range(parent.childCount()):
            child = parent.child(i)
            current_path = path + (i,)
            if current_path in state:
                index = self.tree_widget.indexFromItem(child)
                self.tree_widget.setExpanded(index, state[current_path])
                if child.childCount():
                    self._set_tree_fold_state(child, state, current_path)

    def _get_selected_paths(self):
        """Returns a list of paths for the currently selected items."""
        selected_paths = []
        for item in self.tree_widget.selectedItems():
            path = []
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

    def _restore_selection(self):
        """Restore selection based on the stored paths."""
        for path in self.selected_paths:
            item = self._get_item_from_path(path)
            if item:
                item.setSelected(True)

    def _get_item_from_path(self, path):
        """Retrieve an item based on its path (indices) in the tree."""
        item = self.tree_widget.invisibleRootItem()
        for index in path:
            item = item.child(index)
            if item is None:
                return None
        return item
