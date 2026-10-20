from collections import defaultdict

from sqlalchemy import inspect
from tornado.web import HTTPError

from models.user import User
from rbac.role import Role
from registry.schema import get_registry
from utils.web.base_controller import BaseAPIController
from utils.web.json_body import get_json_object
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import (
    allow_when_password_required,
    api_authenticated,
    require_admin,
)


def _parse_role_change(data: dict) -> tuple[str, dict, int, Role]:
    """Validate the body of a role grant/revoke request.

    :param data: The decoded JSON request body.
    :returns: ``(resource, object, user_id, role)`` with types normalised.
    :raises HTTPError: With status 400 if a field is missing or has the wrong type,
        or if ``role`` is not a valid role value.
    """
    resource = data.get("resource", None)
    rbac_object = data.get("object", None)
    user = data.get("user", None)
    role = data.get("role", None)

    for name, value in (
        ("resource", resource),
        ("object", rbac_object),
        ("user", user),
        ("role", role),
    ):
        if not value:
            raise HTTPError(400, reason=f"{name} body parameter not fulfilled")

    if not isinstance(resource, str):
        raise HTTPError(400, reason="resource must be a string")
    if not isinstance(rbac_object, dict):
        raise HTTPError(400, reason="object must be an object")
    try:
        user_id = int(user)
    except (TypeError, ValueError):
        raise HTTPError(400, reason="user must be an integer") from None
    try:
        role_value = Role(role)
    except (TypeError, ValueError):
        raise HTTPError(400, reason="invalid role") from None
    return resource, rbac_object, user_id, role_value


@ApiRoute("rbac/roles", ApiVersion.V1)
class RBACRolesHandler(BaseAPIController):
    @allow_when_password_required
    async def get(self):
        self.set_status(200)
        await self.finish(
            {"roles": [{"key": role.name, "value": role.value} for role in Role]}
        )


@ApiRoute("rbac/user/resources", ApiVersion.V1)
class RBACUsersHandler(BaseAPIController):
    @api_authenticated
    @require_admin
    async def get(self):
        resources = self.application.rbac.get_resources_for_actor(User)
        res = []
        for resource in resources:
            r_inspect = inspect(resource)
            res.append(r_inspect.persist_selectable.fullname)
        self.set_status(200)
        await self.finish({"resources": res})


@ApiRoute("rbac/user/objects", ApiVersion.V1)
class RBACObjectsHandler(BaseAPIController):
    @api_authenticated
    @require_admin
    async def get(self):
        resource = self.get_query_argument("resource", None)
        user = self.get_query_argument("user", None)
        if not resource:
            self.set_status(400)
            await self.finish({"message": "resource query parameter not fulfilled"})
            return

        mapper = self.application.get_db().get_mapper_for_table(resource)
        if not mapper:
            self.set_status(404)
            await self.finish({"message": "object not found"})
            return

        objects = self.application.rbac.get_objects_for_resource(mapper)

        if not user:
            self.set_status(200)
            await self.finish(
                {
                    "objects": [
                        get_registry().get_schema_by_model(o.__class__)().dump(o)
                        for o in objects
                    ],
                    "display_fields": self.application.rbac.get_display_fields(mapper),
                }
            )
        else:
            with self.make_session() as session:
                user = session.get(User, int(user))
                if not user:
                    self.set_status(404)
                    await self.finish({"message": "user not found"})
                    return

                self.set_status(200)
                await self.finish(
                    {
                        "objects": [
                            (
                                get_registry()
                                .get_schema_by_model(o.__class__)()
                                .dump(o),
                                self.application.rbac.get_roles(user, o).value,
                            )
                            for o in objects
                        ],
                        "display_fields": self.application.rbac.get_display_fields(
                            mapper
                        ),
                    }
                )


@ApiRoute("rbac/user/roles", ApiVersion.V1)
class RBACUserRolesHandler(BaseAPIController):
    @api_authenticated
    @allow_when_password_required
    async def get(self):
        with self.make_session() as session:
            res = defaultdict(list)
            user = session.get(User, self.current_user["id"])
            roles = self.application.rbac.get_all_roles(user)
            for resource in roles:
                for role in roles[resource]:
                    res[resource].append(
                        [
                            get_registry()
                            .get_schema_by_model(role[0].__class__)()
                            .dump(role[0]),
                            role[1].value,
                        ]
                    )
            self.set_status(200)
            await self.finish({"roles": res})


class _RBACRoleChangeHandler(BaseAPIController):
    """Shared request handling for granting and revoking a role."""

    def _apply_role(self, user: User, rbac_object, role: Role) -> None:
        """Apply the role change.

        :param user: The user whose role is changing.
        :param rbac_object: The resource object the role applies to.
        :param role: The role to grant or revoke.
        """
        raise NotImplementedError

    @api_authenticated
    @require_admin
    async def post(self):
        data = get_json_object(self)
        resource, rbac_object, user, role = _parse_role_change(data)

        mapper = self.application.get_db().get_mapper_for_table(resource)
        if not mapper:
            self.set_status(404)
            await self.finish({"message": "resource not found"})
            return

        with self.make_session() as session:
            user = session.get(User, user)
            if not user:
                self.set_status(404)
                await self.finish({"message": "user not found"})
                return
            cols = {
                col.key: rbac_object.get(col.key) for col in inspect(mapper).primary_key
            }
            if any(v is None for v in cols.values()):
                self.set_status(400)
                await self.finish({"message": "object is missing primary key fields"})
                return
            rbac_object = session.get(mapper, cols)
            if not rbac_object:
                self.set_status(404)
                await self.finish({"message": "object not found"})
                return
            self._apply_role(user, rbac_object, role)
            for socket in self.application.get_all_ws(user.id):
                await socket.write_message(
                    {"OP": "NOOP", "DATA": {}, "ACTION": "GET_CURRENT_RBAC"}
                )


@ApiRoute("rbac/user/roles/grant", ApiVersion.V1)
class RBACRolesGrantHandler(_RBACRoleChangeHandler):
    def _apply_role(self, user, rbac_object, role):
        self.application.rbac.give_role(user, rbac_object, role)


@ApiRoute("rbac/user/roles/revoke", ApiVersion.V1)
class RBACRolesRevokeHandler(_RBACRoleChangeHandler):
    def _apply_role(self, user, rbac_object, role):
        self.application.rbac.revoke_role(user, rbac_object, role)
