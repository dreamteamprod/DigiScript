import asyncio

from sqlalchemy import select
from tornado import escape
from tornado.httpclient import HTTPRequest

from models.user import User


async def assert_concurrent_first_run_creates_one_admin(test_case, path: str) -> None:
    """Fire several simultaneous first-run create requests at *path*.

    Exactly one must succeed; the rest must be refused as unauthenticated, and
    only one user may exist afterwards.

    :param test_case: A ``DigiScriptTestCase`` (provides the client and app).
    :param path: The create-user endpoint to hit.
    """

    def make(name):
        return HTTPRequest(
            test_case.get_url(path),
            method="POST",
            body=escape.json_encode(
                {"username": name, "password": "adminpass", "is_admin": True}
            ),
        )

    responses = await asyncio.gather(
        *[
            test_case.http_client.fetch(make(f"admin{i}"), raise_error=False)
            for i in range(4)
        ]
    )
    test_case.assertEqual([200, 401, 401, 401], sorted(r.code for r in responses))
    with test_case._app.get_db().sessionmaker() as session:
        test_case.assertEqual(1, len(session.scalars(select(User)).all()))
