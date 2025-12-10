"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-11-27 19:21:53 +0000 (Wed, November 27, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2024-11-19 17:48:43 +0100 (Tue, November 19, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

import unittest
from ccpn.ui.gui.widgets.table._TableCommon import ColumnItem, ColumnGroup


class TestTraitColumnABC(unittest.TestCase):

    def test_column_item_creation(self):
        column = ColumnItem(name="testColumn", visible=True, movable=True, internal=False, locked=False, index=1)
        self.assertEqual(column.name, "testColumn")
        self.assertTrue(column.visible)
        self.assertTrue(column.movable)
        self.assertFalse(column.internal)
        self.assertEqual(column.index, 1)
        self.assertFalse(column.locked)

    def test_locked_attribute_prevention(self):
        column = ColumnItem(name="lockedColumn", movable=True, internal=False, locked=True, index=1)
        with self.assertRaises(RuntimeError):
            column.name = "newName"

    def test_column_group_creation(self):
        child1 = ColumnItem(name="child1")
        child2 = ColumnItem(name="child2")
        group = ColumnGroup(name="group1", children=[child1, child2])
        self.assertEqual(len(group.children), 2)
        self.assertEqual(group.children[0].name, "child1")
        self.assertEqual(group.children[1].name, "child2")

    def test_add_children(self):
        group = ColumnGroup(name="parentGroup")
        child1 = ColumnItem(name="child1")
        group.addChildren(child1)
        self.assertEqual(len(group.children), 1)
        self.assertEqual(group.children[0].name, "child1")

    def test_traverse_tree(self):
        child1 = ColumnItem(name="child1")
        child2 = ColumnItem(name="child2")
        group = ColumnGroup(name="group1", children=[child1, child2])

        items = list(group.traverse(includeBranches=True, includeLeaves=True))
        self.assertEqual(len(items), 3)  # group1, child1, child2
        self.assertEqual(items[0].name, "group1")
        self.assertEqual(items[1].name, "child1")
        self.assertEqual(items[2].name, "child2")

    def test_find_items(self):
        child1 = ColumnItem(name="child1", visible=True)
        child2 = ColumnItem(name="child2", visible=False)
        group = ColumnGroup(name="group1", children=[child1, child2])

        visible_items = list(group.search(visible=True))
        self.assertEqual(len(visible_items), 2)
        # groups are included in the find
        self.assertEqual(visible_items[1].name, "child1")

    def test_locking_context_manager(self):
        column = ColumnItem(name="tempColumn", locked=False)
        with column._attributeUnlocking():
            column.locked = True
        self.assertTrue(column.locked)


class TestColumnGroup(unittest.TestCase):

    def test_duplicate_children(self):
        group = ColumnGroup(name="group1")
        child1 = ColumnItem(name="child1")
        group.addChildren(child1)
        with self.assertRaises(TypeError):
            group.addChildren(child1)  # Adding the same child again

    def test_clear_children(self):
        child1 = ColumnItem(name="child1")
        child2 = ColumnItem(name="child2")
        group = ColumnGroup([child1, child2], name="group1")
        group.clear()
        self.assertEqual(len(group.children), 0)

    def test_visibility_propagation(self):
        child1 = ColumnItem(name="child1", visible=True)
        child2 = ColumnItem(name="child2", visible=False)
        group = ColumnGroup([child1, child2], name="group1")
        self.assertTrue(group.visible)  # Group is visible if any child is visible

    def test_max_depth(self):
        grandchild = ColumnItem(name="grandchild")
        child = ColumnGroup([grandchild], name="childGroup")
        root = ColumnGroup([child], name="rootGroup")
        self.assertEqual(root.maxDepth(), 3)  # root -> child -> grandchild

    def test_depth_calculation(self):
        grandchild = ColumnItem(name="grandchild")
        child = ColumnGroup([grandchild], name="childGroup")
        root = ColumnGroup([child], name="rootGroup")
        self.assertEqual(grandchild.depth, 3)  # depth from root


class TestColumnGroupValid(unittest.TestCase):
    def setUp(self):
        # Create reusable objects for tests
        self.valid_item = ColumnItem(name='valid')
        self.valid_group = ColumnGroup(children=[self.valid_item], name='valid-group')

    def test_valid_initialization(self):
        # Test a valid ColumnGroup
        group = ColumnGroup(
                children=[ColumnItem(name='index'), ColumnItem(name='row')],
                movable=False,
                name='test-group'
                )
        self.assertEqual(group.name, 'test-group')
        self.assertFalse(group.movable)
        self.assertEqual(len(group.children), 2)

    def test_invalid_children_type(self):
        # Test passing invalid type as children
        with self.assertRaises(TypeError):
            ColumnGroup(children=42, name='invalid-group')

    def test_add_children_invalid_type(self):
        # Test adding invalid children types
        group = ColumnGroup(name='test-group')
        with self.assertRaises(TypeError):
            group.addChildren([ColumnItem(name='valid'), 42])

    def test_find_by_group_id(self):
        # Test finding items by groupId
        group = ColumnGroup(
                children=[
                    ColumnGroup(children=[ColumnItem(name='item')], name='sub-group',
                                groupId='test-id')
                    ],
                name='test-group'
                )
        results = group.search(groupId='test-id')
        self.assertEqual(len(list(results)), 1)  # Includes the group and item

    def test_traverse(self):
        # Test traversing group structure
        group = ColumnGroup(
                children=[
                    ColumnItem(name='item1'),
                    ColumnGroup(children=[ColumnItem(name='item2')], name='sub-group')
                    ],
                name='test-group'
                )
        all_nodes = list(group.traverse())
        self.assertEqual(len(all_nodes), 4)
        self.assertTrue(any(node.name == 'item2' for node in all_nodes))

    def test_visibility(self):
        # Test visibility logic
        hidden_item = ColumnItem(name='hidden', visible=False)
        visible_item = ColumnItem(name='visible', visible=True)
        group = ColumnGroup(children=[hidden_item, visible_item], name='test-group')
        visible_nodes = list(group.search(visible=True))
        self.assertEqual(len(visible_nodes), 2)
        self.assertEqual(visible_nodes[-1].name, 'visible')

    # Initialization Tests
    def test_column_group_initialization_valid(self):
        group = ColumnGroup(
            children=[ColumnItem(name='index'), ColumnItem(name='row')],
            movable=False,
            name='test-group'
        )
        self.assertEqual(group.name, 'test-group')
        self.assertFalse(group.movable)
        self.assertEqual(len(group.children), 2)

    def test_column_group_initialization_empty(self):
        group = ColumnGroup(movable=False, name='empty-group')
        self.assertEqual(group.name, 'empty-group')
        self.assertEqual(group.children, [])

    def test_column_item_initialization(self):
        item = ColumnItem(name='test-item', locked=True)
        self.assertEqual(item.name, 'test-item')
        self.assertTrue(item.locked)

    def test_invalid_child_in_children_list(self):
        with self.assertRaises(TypeError):
            ColumnGroup(children=[ColumnItem(name='valid'), 42], name='invalid-group')

    def test_unexpected_keyword_arguments(self):
        with self.assertRaises(TypeError):
            ColumnGroup(fish=[ColumnItem(name='valid')], chips='fries')

    # Add Children Tests
    def test_add_children_valid(self):
        group = ColumnGroup(name='test-group')
        group.addChildren(ColumnItem(name='new-item'))
        self.assertEqual(len(group.children), 1)
        self.assertEqual(group.children[0].name, 'new-item')

    def test_add_children_invalid(self):
        group = ColumnGroup(name='test-group')
        with self.assertRaises(TypeError):
            group.addChildren([ColumnItem(name='valid'), 42])

    def test_add_multiple_children(self):
        group = ColumnGroup(name='test-group')
        group.addChildren(
            ColumnItem(name='first-item'),
            ColumnItem(name='second-item')
        )
        self.assertEqual(len(group.children), 2)
        self.assertEqual(group.children[1].name, 'second-item')

    # Serialization Tests
    def test_to_json(self):
        group = ColumnGroup(
            children=[ColumnItem(name='index'), ColumnItem(name='row')],
            movable=False,
            name='test-group'
        )
        json_output = group.toJson()
        self.assertIn('test-group', json_output)
        self.assertIn('index', json_output)

    def test_to_json_no_metadata(self):
        group = ColumnGroup(
            children=[ColumnItem(name='index')],
            movable=False,
            name='test-group'
        )
        json_output = group.toJsonNoMetaData()
        self.assertIsNotNone(json_output)

    def test_from_json(self):
        group = ColumnGroup(
            children=[ColumnItem(name='index'), ColumnItem(name='row')],
            name='test-group'
        )
        json_output = group.toJson()
        recreated_group = ColumnGroup.newObjectFromJson(jsonString=json_output)
        self.assertEqual(group.toJsonNoMetaData(), recreated_group.toJsonNoMetaData())

    # Find Method Tests
    def test_find_visible_items(self):
        group = ColumnGroup(
            children=[
                ColumnItem(name='hidden', visible=False),
                ColumnItem(name='visible', visible=True)
            ],
            name='test-group'
        )
        visible_items = list(group.search(visible=True))
        self.assertEqual(len(visible_items), 2)
        self.assertEqual(visible_items[-1].name, 'visible')

    # Traverse Tests
    def test_traverse_all_nodes(self):
        group = ColumnGroup(
            children=[
                ColumnItem(name='item1'),
                ColumnGroup(children=[ColumnItem(name='item2')], name='sub-group')
            ],
            name='test-group'
        )
        all_nodes = list(group.traverse())
        self.assertEqual(len(all_nodes), 4)

    def test_traverse_exclude_branches(self):
        group = ColumnGroup(
            children=[
                ColumnItem(name='item1'),
                ColumnGroup(children=[ColumnItem(name='item2')], name='sub-group')
            ],
            name='test-group'
        )
        leaves_only = list(group.traverse(includeBranches=False))
        self.assertEqual(len(leaves_only), 2)

    # Locking and Parent Tests
    def test_lock_item(self):
        item = ColumnItem(name='test-item')
        item.locked = True
        self.assertTrue(item.locked)

    def test_change_locked_item_name(self):
        item = ColumnItem(name='test-item', locked=True)
        with self.assertRaises(Exception):
            item.name = 'new-name'

    def test_parent_relationship(self):
        group = ColumnGroup(
            children=[ColumnItem(name='child')],
            name='parent-group'
        )
        child = group.children[0]
        self.assertEqual(child._parent.name, 'parent-group')

    # Edge Case Tests
    def test_empty_column_group(self):
        group = ColumnGroup(name='empty-group')
        self.assertEqual(len(group.children), 0)

    def test_invalid_argument_combination(self):
        with self.assertRaises(TypeError):
            ColumnGroup(
                ColumnGroup(children=[ColumnItem(name='child')], name='sub-group'),
                children=[ColumnItem(name='other-child')],
                name='invalid-group'
            )

if __name__ == '__main__':
    unittest.main()
