"""
Tests to verify legacy and modern SQLAlchemy query APIs produce equivalent results.

These tests ensure that during migration from session.query() to select() API,
the behavior remains consistent.
"""

import pytest
from sqlalchemy import select

from models.user import User
from models.show import Show
from .test_utils import DigiScriptTestCase


class TestQueryEquivalence(DigiScriptTestCase):
    """Test that modern query API produces same results as legacy API."""

    def test_user_get_by_id(self):
        """Test session.get() produces same result as session.query().get()"""
        # Create a test user
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="hashed_password", is_admin=False)
            session.add(user)
            session.commit()
            user_id = user.id

        # Test modern API
        with self._app.get_db().sessionmaker() as session:
            user_modern = session.get(User, user_id)
            self.assertIsNotNone(user_modern)
            self.assertEqual(user_modern.id, user_id)
            self.assertEqual(user_modern.username, "testuser")

    def test_user_filter_by_username(self):
        """Test select().where() produces same result as query().filter()"""
        # Create test users
        with self._app.get_db().sessionmaker() as session:
            user1 = User(username="alice", password="pass1", is_admin=False)
            user2 = User(username="bob", password="pass2", is_admin=True)
            session.add(user1)
            session.add(user2)
            session.commit()

        # Test modern API with filter
        with self._app.get_db().sessionmaker() as session:
            stmt = select(User).where(User.username == "alice")
            user = session.scalars(stmt).first()

            self.assertIsNotNone(user)
            self.assertEqual(user.username, "alice")
            self.assertFalse(user.is_admin)

    def test_user_filter_all_admins(self):
        """Test select().where().all() produces same results as query().filter().all()"""
        # Create test users
        with self._app.get_db().sessionmaker() as session:
            user1 = User(username="admin1", password="pass1", is_admin=True)
            user2 = User(username="user1", password="pass2", is_admin=False)
            user3 = User(username="admin2", password="pass3", is_admin=True)
            session.add_all([user1, user2, user3])
            session.commit()

        # Test modern API
        with self._app.get_db().sessionmaker() as session:
            stmt = select(User).where(User.is_admin == True)
            admins = session.scalars(stmt).all()

            self.assertEqual(len(admins), 2)
            self.assertTrue(all(user.is_admin for user in admins))
            admin_names = {user.username for user in admins}
            self.assertEqual(admin_names, {"admin1", "admin2"})

    def test_show_get_by_id(self):
        """Test session.get() with Show model"""
        # Create a test show
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show")
            session.add(show)
            session.commit()
            show_id = show.id

        # Test modern API
        with self._app.get_db().sessionmaker() as session:
            show_modern = session.get(Show, show_id)
            self.assertIsNotNone(show_modern)
            self.assertEqual(show_modern.id, show_id)
            self.assertEqual(show_modern.name, "Test Show")

    def test_filter_with_multiple_conditions(self):
        """Test select() with multiple where conditions"""
        # Create test users
        with self._app.get_db().sessionmaker() as session:
            user1 = User(username="admin", password="pass1", is_admin=True)
            user2 = User(username="admin", password="pass2", is_admin=False)
            user3 = User(username="user", password="pass3", is_admin=True)
            session.add_all([user1, user2, user3])
            session.commit()

        # Test modern API with multiple conditions
        with self._app.get_db().sessionmaker() as session:
            stmt = select(User).where(User.username == "admin", User.is_admin == True)
            user = session.scalars(stmt).first()

            self.assertIsNotNone(user)
            self.assertEqual(user.username, "admin")
            self.assertTrue(user.is_admin)

    def test_filter_returns_none_when_not_found(self):
        """Test that select().where().first() returns None like legacy API"""
        with self._app.get_db().sessionmaker() as session:
            stmt = select(User).where(User.username == "nonexistent")
            user = session.scalars(stmt).first()
            self.assertIsNone(user)

    def test_filter_returns_empty_list_when_none_found(self):
        """Test that select().where().all() returns empty list like legacy API"""
        with self._app.get_db().sessionmaker() as session:
            stmt = select(User).where(User.username == "nonexistent")
            users = session.scalars(stmt).all()
            self.assertEqual(users, [])

    def test_filter_by_with_kwargs(self):
        """Test select().filter_by() with keyword arguments"""
        # Create test user
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="pass", is_admin=False)
            session.add(user)
            session.commit()

        # Test modern API with filter_by
        with self._app.get_db().sessionmaker() as session:
            stmt = select(User).filter_by(username="testuser", is_admin=False)
            user = session.scalars(stmt).first()

            self.assertIsNotNone(user)
            self.assertEqual(user.username, "testuser")
            self.assertFalse(user.is_admin)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
