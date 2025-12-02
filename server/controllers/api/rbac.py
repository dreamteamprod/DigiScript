from collections import defaultdict

from sqlalchemy import inspect
from tornado import escape

from models.user import User
from rbac.role import Role
from registry.schema import get_registry
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import api_authenticated, require_admin


@ApiRoute("rbac/roles", ApiVersion.V1)
class RBACRolesHandler(BaseAPIController):
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
            res.append(r_inspect.mapped_table.fullname)
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
                user = session.query(User).get(int(user))
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
    async def get(self):
        with self.make_session() as session:
            res = defaultdict(list)
            user = session.query(User).get(self.current_user["id"])
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


@ApiRoute("rbac/user/roles/grant", ApiVersion.V1)
class RBACRolesGrantHandler(BaseAPIController):
    @api_authenticated
    @require_admin
    async def post(self):
        data = escape.json_decode(self.request.body)
        resource = data.get("resource", None)
        rbac_object = data.get("object", None)
        user = data.get("user", None)
        role = data.get("role", None)

        if not resource:
            self.set_status(400)
            await self.finish({"message": "resource body parameter not fulfilled"})
            return
        if not rbac_object:
            self.set_status(400)
            await self.finish({"message": "object body parameter not fulfilled"})
            return
        if not user:
            self.set_status(400)
            await self.finish({"message": "user body parameter not fulfilled"})
            return
        if not role:
            self.set_status(400)
            await self.finish({"message": "role body parameter not fulfilled"})
            return

        mapper = self.application.get_db().get_mapper_for_table(resource)
        if not mapper:
            self.set_status(404)
            await self.finish({"message": "resource not found"})
            return

        with self.make_session() as session:
            user = session.query(User).get(int(user))
            if not user:
                self.set_status(404)
                await self.finish({"message": "user not found"})
                return
            resource = inspect(mapper)
            cols = {}
            cols.update(
                {col.key: rbac_object.get(col.key) for col in resource.primary_key}
            )
            rbac_object = session.query(mapper).get(cols)
            if not rbac_object:
                self.set_status(404)
                await self.finish({"message": "object not found"})
                return
            self.application.rbac.give_role(user, rbac_object, Role(role))
            for socket in self.application.get_all_ws(user.id):
                await socket.write_message(
                    {"OP": "NOOP", "DATA": {}, "ACTION": "GET_CURRENT_RBAC"}
                )


@ApiRoute("rbac/user/roles/revoke", ApiVersion.V1)
class RBACRolesRevokeHandler(BaseAPIController):
    @api_authenticated
    @require_admin
    async def post(self):
        data = escape.json_decode(self.request.body)
        resource = data.get("resource", None)
        rbac_object = data.get("object", None)
        user = data.get("user", None)
        role = data.get("role", None)

        if not resource:
            self.set_status(400)
            await self.finish({"message": "resource body parameter not fulfilled"})
            return
        if not rbac_object:
            self.set_status(400)
            await self.finish({"message": "object body parameter not fulfilled"})
            return
        if not user:
            self.set_status(400)
            await self.finish({"message": "user body parameter not fulfilled"})
            return
        if not role:
            self.set_status(400)
            await self.finish({"message": "role body parameter not fulfilled"})
            return

        mapper = self.application.get_db().get_mapper_for_table(resource)
        if not mapper:
            self.set_status(404)
            await self.finish({"message": "resource not found"})
            return

        with self.make_session() as session:
            user = session.query(User).get(int(user))
            if not user:
                self.set_status(404)
                await self.finish({"message": "user not found"})
                return
            resource = inspect(mapper)
            cols = {}
            cols.update(
                {col.key: rbac_object.get(col.key) for col in resource.primary_key}
            )
            rbac_object = session.query(mapper).get(cols)
            if not rbac_object:
                self.set_status(404)
                await self.finish({"message": "object not found"})
                return
            self.application.rbac.revoke_role(user, rbac_object, Role(role))
            for socket in self.application.get_all_ws(user.id):
                await socket.write_message(
                    {"OP": "NOOP", "DATA": {}, "ACTION": "GET_CURRENT_RBAC"}
                )
