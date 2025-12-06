"""
Tests for RBAC system query migration.

These tests verify that the RBAC dynamic table mapping system works correctly
with modern SQLAlchemy select() API, particularly for:
- Dynamic table creation
- Composite key lookups with dict-based columns
- filter_by() with kwargs for runtime-generated tables
"""

import pytest
from sqlalchemy import select

from models.user import User
from models.show import Show
from rbac.role import Role
from .test_utils import DigiScriptTestCase


class TestRBACMigration(DigiScriptTestCase):
    """Test RBAC system with modern SQLAlchemy API."""

    def setUp(self):
        """Set up test data for RBAC tests."""
        super().setUp()

        # Create test users and show
        with self._app.get_db().sessionmaker() as session:
            self.user1 = User(username="user1", password="pass1", is_admin=False)
            self.user2 = User(username="user2", password="pass2", is_admin=False)
            session.add_all([self.user1, self.user2])
            session.flush()

            self.show1 = Show(name="Show 1")
            self.show2 = Show(name="Show 2")
            session.add_all([self.show1, self.show2])
            session.commit()

            self.user1_id = self.user1.id
            self.user2_id = self.user2.id
            self.show1_id = self.show1.id
            self.show2_id = self.show2.id

    def test_rbac_give_role(self):
        """Test giving a role to a user for a resource"""
        # Give user1 READ access to show1
        self._app.rbac.give_role(self.user1, self.show1, Role.READ)

        # Verify the role was assigned
        has_role = self._app.rbac.has_role(self.user1, self.show1, Role.READ)
        self.assertTrue(has_role)

    def test_rbac_get_roles(self):
        """Test getting all roles for a user on a resource"""
        # Give user1 multiple roles on show1
        self._app.rbac.give_role(self.user1, self.show1, Role.READ)
        self._app.rbac.give_role(self.user1, self.show1, Role.WRITE)

        # Get all roles
        roles = self._app.rbac.get_roles(self.user1, self.show1)

        self.assertTrue(Role.READ in roles)
        self.assertTrue(Role.WRITE in roles)
        self.assertFalse(Role.EXECUTE in roles)

    def test_rbac_revoke_role(self):
        """Test revoking a role from a user"""
        # Give and then revoke role
        self._app.rbac.give_role(self.user1, self.show1, Role.READ)
        self.assertTrue(self._app.rbac.has_role(self.user1, self.show1, Role.READ))

        self._app.rbac.revoke_role(self.user1, self.show1, Role.READ)
        self.assertFalse(self._app.rbac.has_role(self.user1, self.show1, Role.READ))

    def test_rbac_multiple_users_same_resource(self):
        """Test multiple users with different permissions on same resource"""
        # Give different permissions to different users
        self._app.rbac.give_role(self.user1, self.show1, Role.READ)
        self._app.rbac.give_role(self.user2, self.show1, Role.WRITE)

        # Verify each user has their specific role
        self.assertTrue(self._app.rbac.has_role(self.user1, self.show1, Role.READ))
        self.assertFalse(self._app.rbac.has_role(self.user1, self.show1, Role.WRITE))

        self.assertFalse(self._app.rbac.has_role(self.user2, self.show1, Role.READ))
        self.assertTrue(self._app.rbac.has_role(self.user2, self.show1, Role.WRITE))

    def test_rbac_multiple_resources_same_user(self):
        """Test one user with different permissions on different resources"""
        # Give user1 different permissions on different shows
        self._app.rbac.give_role(self.user1, self.show1, Role.READ)
        self._app.rbac.give_role(self.user1, self.show2, Role.WRITE | Role.EXECUTE)

        # Verify permissions are resource-specific
        roles_show1 = self._app.rbac.get_roles(self.user1, self.show1)
        roles_show2 = self._app.rbac.get_roles(self.user1, self.show2)

        self.assertTrue(Role.READ in roles_show1)
        self.assertFalse(Role.WRITE in roles_show1)

        self.assertFalse(Role.READ in roles_show2)
        self.assertTrue(Role.WRITE in roles_show2)
        self.assertTrue(Role.EXECUTE in roles_show2)

    def test_rbac_get_all_roles(self):
        """Test getting all roles for a user within current show context"""
        # Give user1 roles on multiple shows
        self._app.rbac.give_role(self.user1, self.show1, Role.READ)
        self._app.rbac.give_role(self.user1, self.show2, Role.WRITE)

        # Set current show to show1 (required for get_all_roles to work)
        self._app.digi_settings.settings["current_show"].set_value(self.show1_id, False)

        # Get all roles - should only return roles for current show
        all_roles = self._app.rbac.get_all_roles(self.user1)

        # Verify structure: {resource_table: [[object, roles], ...]}
        self.assertIn("shows", all_roles)
        show_roles = all_roles["shows"]

        # Should only return the current show (show1), not all shows
        self.assertEqual(len(show_roles), 1)

        # Verify it's show1 with READ role
        obj, roles = show_roles[0]
        self.assertEqual(obj.id, self.show1_id)
        self.assertTrue(Role.READ in roles)

    def test_rbac_dynamic_table_mapping(self):
        """Test that dynamic RBAC table mapping works correctly"""
        # This tests the internal dynamic table creation
        rbac_db = self._app.rbac.rbac_db

        # Get the mapping table name for User -> Show
        table_name = "rbac_user_shows"
        self.assertIn(table_name, rbac_db._mappings)

        # Verify the mapping class was created dynamically
        mapping_class = rbac_db._mappings[table_name]
        self.assertIsNotNone(mapping_class)

    def test_rbac_delete_actor(self):
        """Test that deleting a user removes their RBAC assignments"""
        # Give user1 roles
        self._app.rbac.give_role(self.user1, self.show1, Role.READ)
        self.assertTrue(self._app.rbac.has_role(self.user1, self.show1, Role.READ))

        # Delete the user (actor)
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, self.user1_id)
            self._app.rbac.delete_actor(user)

        # Verify roles are gone
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, self.user1_id)
            # The user still exists but should have no roles
            has_role = self._app.rbac.has_role(user, self.show1, Role.READ)
            self.assertFalse(has_role)

    def test_rbac_delete_resource(self):
        """Test that deleting a resource removes RBAC assignments for it"""
        # Give users roles on show1
        self._app.rbac.give_role(self.user1, self.show1, Role.READ)
        self._app.rbac.give_role(self.user2, self.show1, Role.WRITE)

        # Delete the resource (show)
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show1_id)
            self._app.rbac.rbac_db.delete_resource(show)

        # Verify roles are gone for both users
        with self._app.get_db().sessionmaker() as session:
            user1 = session.get(User, self.user1_id)
            show1 = session.get(Show, self.show1_id)
            has_role = self._app.rbac.has_role(user1, show1, Role.READ)
            self.assertFalse(has_role)

    def test_rbac_composite_role_assignment(self):
        """Test assigning multiple roles at once using bitwise OR"""
        # Give user multiple roles in one operation
        combined_role = Role.READ | Role.WRITE
        self._app.rbac.give_role(self.user1, self.show1, combined_role)

        # Verify both roles are present
        self.assertTrue(self._app.rbac.has_role(self.user1, self.show1, Role.READ))
        self.assertTrue(self._app.rbac.has_role(self.user1, self.show1, Role.WRITE))
        self.assertFalse(self._app.rbac.has_role(self.user1, self.show1, Role.EXECUTE))

    def test_rbac_get_objects_for_resource(self):
        """Test getting all objects for a resource type"""
        # This tests the complex query that navigates relationships
        objects = self._app.rbac.rbac_db.get_objects_for_resource(Show)

        # Should return shows for the current show (if set) or empty list
        self.assertIsInstance(objects, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
