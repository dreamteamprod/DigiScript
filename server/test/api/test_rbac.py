from models.show import Show
from models.user import User
from rbac.role import Role
from test.utils import DigiScriptTestCase


class TestRBAC(DigiScriptTestCase):
    def test_delete_actor_removes_rbac_assignments(self):
        """Test that delete_actor removes all RBAC assignments for a user.

        This tests the query at line 247 in rbac/rbac_db.py:
        session.query(self._mappings[table_name]).filter_by(**cols).all()

        We create a user, assign them roles for resources, then call delete_actor
        and verify the RBAC table entries were deleted.
        """
        # Create test data
        with self._app.get_db().sessionmaker() as session:
            # Create a show (resource)
            show = Show(name="Test Show")
            session.add(show)
            session.flush()

            # Create a user (actor)
            user = User(username="testuser", password="test")
            session.add(user)
            session.commit()
            user_id = user.id
            show_id = show.id

        # Assign RBAC role to user for the show
        # This creates an entry in the dynamic rbac_user_shows table
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, user_id)
            show = session.get(Show, show_id)
            self._app.rbac.give_role(user, show, Role.READ)

        # Verify RBAC assignment exists by checking user has the role
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, user_id)
            show = session.get(Show, show_id)
            has_role = self._app.rbac.has_role(user, show, Role.READ)
            self.assertTrue(has_role, "User should have READ role for show")

        # Call the actual delete_actor method
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, user_id)
            # This should delete all RBAC assignments for this user
            self._app.rbac.delete_actor(user)

        # Verify RBAC assignment was deleted
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, user_id)
            show = session.get(Show, show_id)
            has_role = self._app.rbac.has_role(user, show, Role.READ)
            self.assertFalse(has_role, "RBAC assignment should be deleted")
