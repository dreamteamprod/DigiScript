"""
Baseline performance tests for SQLAlchemy query operations.

These tests establish performance baselines before migration to SQLAlchemy 2.0
select() API. They measure:
- RBAC query performance (most complex area with dynamic tables)
- Simple query patterns (get, filter)
- Composite key lookups

Run with: pytest server/test/test_performance_baseline.py -v -s

Results should be documented and compared after migration to ensure
no performance regressions.
"""

import time
import pytest
from statistics import mean, median, stdev

from models.user import User
from models.show import Show
from models.script import (
    Script,
    ScriptRevision,
    ScriptLine,
    ScriptLineRevisionAssociation,
)
from rbac.role import Role
from .test_utils import DigiScriptTestCase


def benchmark(func, iterations=100):
    """Simple benchmark helper that runs a function multiple times.

    Args:
        func: Function to benchmark (should be a lambda or callable)
        iterations: Number of times to run the function

    Returns:
        Dictionary with timing statistics in milliseconds
    """
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to milliseconds

    return {
        "mean": mean(times),
        "median": median(times),
        "min": min(times),
        "max": max(times),
        "stdev": stdev(times) if len(times) > 1 else 0,
        "iterations": iterations,
    }


class TestPerformanceBaseline(DigiScriptTestCase):
    """Baseline performance tests for query operations."""

    def setUp(self):
        """Set up test data for performance tests."""
        super().setUp()

        # Create test users and shows for benchmarking
        with self._app.get_db().sessionmaker() as session:
            # Create 10 users
            self.users = []
            for i in range(10):
                user = User(
                    username=f"perfuser{i}", password=f"pass{i}", is_admin=False
                )
                session.add(user)
                self.users.append(user)
            session.flush()

            # Create 10 shows
            self.shows = []
            for i in range(10):
                show = Show(name=f"Performance Show {i}")
                session.add(show)
                self.shows.append(show)
            session.flush()

            # Create script with revisions and lines
            self.script = Script(show_id=self.shows[0].id)
            session.add(self.script)
            session.flush()

            self.revision = ScriptRevision(
                script_id=self.script.id, revision=1, description="Performance Test Rev"
            )
            session.add(self.revision)
            session.flush()

            # Create 20 script lines with associations
            self.lines = []
            for i in range(20):
                line = ScriptLine(page=i // 10 + 1, stage_direction=False)
                session.add(line)
                self.lines.append(line)
            session.flush()

            for i, line in enumerate(self.lines):
                assoc = ScriptLineRevisionAssociation(
                    revision_id=self.revision.id, line_id=line.id
                )
                session.add(assoc)

            session.commit()

            # Store IDs for use in tests
            self.user_ids = [u.id for u in self.users]
            self.show_ids = [s.id for s in self.shows]
            self.revision_id = self.revision.id
            self.line_ids = [l.id for l in self.lines]

    def test_baseline_simple_get_by_id(self):
        """Baseline: session.get() for simple primary key lookup"""
        print("\n" + "=" * 70)
        print("BASELINE: Simple session.get() by ID")
        print("=" * 70)

        def get_user():
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, self.user_ids[0])
                return user

        stats = benchmark(get_user, iterations=100)

        print(f"Mean:   {stats['mean']:.3f} ms")
        print(f"Median: {stats['median']:.3f} ms")
        print(f"Min:    {stats['min']:.3f} ms")
        print(f"Max:    {stats['max']:.3f} ms")
        print(f"StdDev: {stats['stdev']:.3f} ms")
        print(f"Iterations: {stats['iterations']}")

        # Sanity check - should be fast (< 10ms average)
        self.assertLess(
            stats["mean"],
            10.0,
            f"Simple get should be < 10ms, got {stats['mean']:.3f}ms",
        )

    def test_baseline_composite_key_get(self):
        """Baseline: session.get() with composite key (tuple)"""
        print("\n" + "=" * 70)
        print("BASELINE: Composite key lookup with tuple")
        print("=" * 70)

        def get_assoc():
            with self._app.get_db().sessionmaker() as session:
                assoc = session.get(
                    ScriptLineRevisionAssociation, (self.revision_id, self.line_ids[0])
                )
                return assoc

        stats = benchmark(get_assoc, iterations=100)

        print(f"Mean:   {stats['mean']:.3f} ms")
        print(f"Median: {stats['median']:.3f} ms")
        print(f"Min:    {stats['min']:.3f} ms")
        print(f"Max:    {stats['max']:.3f} ms")
        print(f"StdDev: {stats['stdev']:.3f} ms")
        print(f"Iterations: {stats['iterations']}")

        # Should also be reasonably fast
        self.assertLess(
            stats["mean"],
            10.0,
            f"Composite key get should be < 10ms, got {stats['mean']:.3f}ms",
        )

    def test_baseline_rbac_give_role(self):
        """Baseline: RBAC give_role operation (INSERT)"""
        print("\n" + "=" * 70)
        print("BASELINE: RBAC give_role (dynamic table INSERT)")
        print("=" * 70)

        iteration = [0]  # Use list to allow mutation in nested function

        def give_role():
            # Use different user/show each time to avoid duplicates
            user_idx = iteration[0] % len(self.user_ids)
            show_idx = iteration[0] % len(self.show_ids)

            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, self.user_ids[user_idx])
                show = session.get(Show, self.show_ids[show_idx])
                self._app.rbac.give_role(user, show, Role.READ)

            iteration[0] += 1

        stats = benchmark(give_role, iterations=50)  # Fewer iterations for writes

        print(f"Mean:   {stats['mean']:.3f} ms")
        print(f"Median: {stats['median']:.3f} ms")
        print(f"Min:    {stats['min']:.3f} ms")
        print(f"Max:    {stats['max']:.3f} ms")
        print(f"StdDev: {stats['stdev']:.3f} ms")
        print(f"Iterations: {stats['iterations']}")

        # Write operations are typically slower
        self.assertLess(
            stats["mean"],
            50.0,
            f"RBAC give_role should be < 50ms, got {stats['mean']:.3f}ms",
        )

    def test_baseline_rbac_has_role(self):
        """Baseline: RBAC has_role operation (SELECT with composite key)"""
        print("\n" + "=" * 70)
        print("BASELINE: RBAC has_role (dynamic table SELECT)")
        print("=" * 70)

        # Set up a role first
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, self.user_ids[0])
            show = session.get(Show, self.show_ids[0])
            self._app.rbac.give_role(user, show, Role.READ)

        def has_role():
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, self.user_ids[0])
                show = session.get(Show, self.show_ids[0])
                result = self._app.rbac.has_role(user, show, Role.READ)
                return result

        stats = benchmark(has_role, iterations=100)

        print(f"Mean:   {stats['mean']:.3f} ms")
        print(f"Median: {stats['median']:.3f} ms")
        print(f"Min:    {stats['min']:.3f} ms")
        print(f"Max:    {stats['max']:.3f} ms")
        print(f"StdDev: {stats['stdev']:.3f} ms")
        print(f"Iterations: {stats['iterations']}")

        self.assertLess(
            stats["mean"],
            20.0,
            f"RBAC has_role should be < 20ms, got {stats['mean']:.3f}ms",
        )

    def test_baseline_rbac_get_roles(self):
        """Baseline: RBAC get_roles operation (SELECT + bitwise operations)"""
        print("\n" + "=" * 70)
        print("BASELINE: RBAC get_roles (dynamic table SELECT with aggregation)")
        print("=" * 70)

        # Set up multiple roles first
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, self.user_ids[0])
            show = session.get(Show, self.show_ids[0])
            self._app.rbac.give_role(user, show, Role.READ)
            self._app.rbac.give_role(user, show, Role.WRITE)
            self._app.rbac.give_role(user, show, Role.EXECUTE)

        def get_roles():
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, self.user_ids[0])
                show = session.get(Show, self.show_ids[0])
                roles = self._app.rbac.get_roles(user, show)
                return roles

        stats = benchmark(get_roles, iterations=100)

        print(f"Mean:   {stats['mean']:.3f} ms")
        print(f"Median: {stats['median']:.3f} ms")
        print(f"Min:    {stats['min']:.3f} ms")
        print(f"Max:    {stats['max']:.3f} ms")
        print(f"StdDev: {stats['stdev']:.3f} ms")
        print(f"Iterations: {stats['iterations']}")

        self.assertLess(
            stats["mean"],
            20.0,
            f"RBAC get_roles should be < 20ms, got {stats['mean']:.3f}ms",
        )

    def test_baseline_rbac_get_all_roles(self):
        """Baseline: RBAC get_all_roles operation (complex multi-table query)"""
        print("\n" + "=" * 70)
        print("BASELINE: RBAC get_all_roles (complex multi-table JOIN)")
        print("=" * 70)

        # Set up roles across multiple shows
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, self.user_ids[0])
            for show_id in self.show_ids[:5]:  # First 5 shows
                show = session.get(Show, show_id)
                self._app.rbac.give_role(user, show, Role.READ)

        def get_all_roles():
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, self.user_ids[0])
                all_roles = self._app.rbac.get_all_roles(user)
                return all_roles

        stats = benchmark(get_all_roles, iterations=50)  # Fewer for complex query

        print(f"Mean:   {stats['mean']:.3f} ms")
        print(f"Median: {stats['median']:.3f} ms")
        print(f"Min:    {stats['min']:.3f} ms")
        print(f"Max:    {stats['max']:.3f} ms")
        print(f"StdDev: {stats['stdev']:.3f} ms")
        print(f"Iterations: {stats['iterations']}")

        # Most complex query, allow more time
        self.assertLess(
            stats["mean"],
            100.0,
            f"RBAC get_all_roles should be < 100ms, got {stats['mean']:.3f}ms",
        )

    def test_baseline_summary(self):
        """Print summary of all baseline metrics"""
        print("\n" + "=" * 70)
        print("BASELINE PERFORMANCE SUMMARY")
        print("=" * 70)
        print("\nAll baseline tests completed successfully.")
        print("\nThese metrics should be compared after migration to ensure:")
        print("  1. No significant performance regressions")
        print("  2. Complex queries (RBAC) remain performant")
        print("  3. Composite key lookups are still efficient")
        print("\nExpected results after migration:")
        print("  - Simple gets: Similar or slightly faster")
        print("  - Composite keys: Similar performance")
        print("  - RBAC operations: Similar or slightly faster")
        print("  - Complex queries: Should remain under thresholds")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
