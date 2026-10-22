"""Request-handler bodies shared by the v1 and v2 user and API-token endpoints.

The v1 and v2 controllers differ only in routing and in a few response details,
so the common work (and its audit calls) lives here, once. Each function takes
the calling controller and writes the response itself, exactly as the inline
handler bodies did.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from models.user import User
from registry.named_locks import NamedLockRegistry
from services.password_service import PasswordService
from utils.web.api_keys import ApiKeyService
from utils.web.auth_audit import actor, audit
from utils.web.json_body import get_json_object


async def create_user(controller) -> None:
    """Create a user from the request body and write the response.

    The caller must hold the ``USER_CREATE_LOCK`` so the has-any-users check and
    the insert form one critical section. Anyone may create the first user (who
    must be an admin); after that only an admin may.

    :param controller: The request handler.
    """
    with controller.make_session() as session:
        # If there are no users, allow creation without authentication, otherwise
        # require admin.
        has_any_users = session.scalars(select(User)).first() is not None
        if has_any_users:
            controller.requires_admin()

        data = get_json_object(controller)

        username = data.get("username", "")
        if not username:
            controller.set_status(400)
            await controller.finish({"message": "Username missing"})
            return

        password = data.get("password", "")
        if not password:
            controller.set_status(400)
            await controller.finish({"message": "Password missing"})
            return

        is_admin = data.get("is_admin", False)
        if not has_any_users and not is_admin:
            controller.set_status(400)
            await controller.finish({"message": "First user must be an admin"})
            return

        is_valid, error_msg = PasswordService.validate_password_strength(password)
        if not is_valid:
            audit(
                "user_create",
                "failure",
                detail="reason=weak_password",
                **actor(controller),
            )
            controller.set_status(400)
            await controller.finish({"message": error_msg})
            return

        async with NamedLockRegistry.acquire(f"UserLock::{username}"):
            conflict_user = session.scalars(
                select(User).where(User.username == username)
            ).first()
            if conflict_user:
                audit(
                    "user_create",
                    "failure",
                    detail="reason=username_taken",
                    **actor(controller),
                )
                controller.set_status(400)
                await controller.finish({"message": "Username already taken"})
                return

            hashed_password = await PasswordService.hash_password(password)

            new_user = User(
                username=username,
                password=hashed_password,
                is_admin=is_admin,
                created_on=datetime.now(tz=timezone.utc),
            )
            session.add(new_user)
            session.commit()
            audit(
                "user_create",
                "success",
                detail=f"target_user_id={new_user.id} is_admin={bool(is_admin)}",
                **actor(controller),
            )

            if is_admin:
                await controller.application.digi_settings.set("has_admin_user", True)

            controller.set_status(200)
            await controller.application.ws_send_to_all("NOOP", "GET_USERS", {})
            await controller.finish({"message": "Successfully created user"})


async def delete_user(controller, session, user_to_delete: User) -> None:
    """Delete an existing user, refusing self-deletion and the only admin.

    :param controller: The request handler (its current user is the actor).
    :param session: Open database session that loaded ``user_to_delete``.
    :param user_to_delete: The user to remove.
    """
    if user_to_delete.id == controller.current_user["id"]:
        controller.set_status(400)
        await controller.finish(
            {"message": "Cannot delete currently authenticated user"}
        )
        return

    all_admins = session.scalars(select(User).where(User.is_admin.is_(True))).all()
    if user_to_delete.is_admin and len(all_admins) <= 1:
        audit(
            "user_delete",
            "failure",
            detail=f"target_user_id={user_to_delete.id} reason=only_admin",
            **actor(controller),
        )
        controller.set_status(400)
        await controller.finish({"message": "Cannot delete the only admin user"})
        return

    async with NamedLockRegistry.acquire(f"UserLock::{user_to_delete.username}"):
        await controller.application.user_service.force_logout_all_sessions(
            session, user_to_delete
        )
        controller.application.rbac.delete_actor(user_to_delete)
        target_id = user_to_delete.id
        session.delete(user_to_delete)
        session.commit()
        audit(
            "user_delete",
            "success",
            detail=f"target_user_id={target_id}",
            **actor(controller),
        )

        controller.set_status(200)
        await controller.application.ws_send_to_all("NOOP", "GET_USERS", {})
        await controller.finish({"message": "Successfully deleted user"})


async def generate_api_token(controller) -> None:
    """Generate an API token for the current user and write the response.

    :param controller: The request handler.
    """
    with controller.make_session() as session:
        user = session.get(User, controller.current_user["id"])
        if not user:
            controller.set_status(404)
            await controller.finish({"message": "User not found"})
            return

        # Key is a random secret; only its SHA-256 digest is stored
        new_token, user.api_token = ApiKeyService.generate()
        session.commit()
        controller.application.jwt_service.api_keys.invalidate()

        audit("api_token_generate", "success", **actor(controller))
        controller.set_status(200)
        await controller.finish(
            {
                "message": "API token generated successfully",
                "api_token": new_token,
            }
        )


async def revoke_api_token(controller) -> None:
    """Revoke the current user's API token and write the response.

    :param controller: The request handler.
    """
    with controller.make_session() as session:
        user = session.get(User, controller.current_user["id"])
        if not user:
            controller.set_status(404)
            await controller.finish({"message": "User not found"})
            return

        if not user.api_token:
            audit(
                "api_token_revoke",
                "failure",
                detail="reason=no_token",
                **actor(controller),
            )
            controller.set_status(400)
            await controller.finish({"message": "No API token to revoke"})
            return

        user.api_token = None
        session.commit()
        controller.application.jwt_service.api_keys.invalidate()

        audit("api_token_revoke", "success", **actor(controller))
        controller.set_status(200)
        await controller.finish({"message": "API token revoked successfully"})
