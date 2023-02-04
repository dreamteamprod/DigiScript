import bcrypt
from tornado import escape, web
from tornado.ioloop import IOLoop

from models.show import Show
from models.user import User
from utils.base_controller import BaseAPIController
from utils.route import ApiRoute, ApiVersion


@ApiRoute('auth/create', ApiVersion.v1)
class UserCreateController(BaseAPIController):

    async def post(self):
        data = escape.json_decode(self.request.body)

        username = data.get('username', '')
        if not username:
            self.set_status(400)
            await self.finish({'message': 'Username missing'})
            return

        password = data.get('password', '')
        if not password:
            self.set_status(400)
            await self.finish({'message': 'Password missing'})
            return
        if len(password) < 6:
            self.set_status(400)
            await self.finish({'message': 'Password must be at least 6 characters long'})
            return

        show_id = data.get('show_id', None)
        is_admin = data.get('is_admin', False)

        if not show_id and not is_admin:
            self.set_status(400)
            await self.finish({'message': 'Non admin user requires a show allocation'})
            return

        if is_admin and show_id:
            self.set_status(400)
            await self.finish({'message': 'Admin user cannot have a show allocation'})
            return

        with self.make_session() as session:
            if show_id:
                show = session.query(Show).get(show_id)
                if not show:
                    self.set_status(400)
                    await self.finish({'message': 'Show not found'})
                    return

            conflict_user = session.query(User).filter(User.username == username).first()
            if conflict_user:
                self.set_status(400)
                await self.finish({'message': 'Username already taken'})
                return

            hashed_password = await IOLoop.current().run_in_executor(
                None, bcrypt.hashpw, escape.utf8(password), bcrypt.gensalt())
            hashed_password = escape.to_unicode(hashed_password)

            session.add(User(
                username=username,
                password=hashed_password,
                show_id=show_id,
                is_admin=is_admin))
            session.commit()

            if is_admin:
                await self.application.digi_settings.set('has_admin_user', True)

            self.set_status(200)
            await self.finish({'message': 'Successfully created user'})


@ApiRoute('auth/login', ApiVersion.v1)
class LoginHandler(BaseAPIController):
    async def post(self):
        data = escape.json_decode(self.request.body)

        username = data.get('username', '')
        if not username:
            self.set_status(400)
            await self.finish({'message': 'Username missing'})
            return

        password = data.get('password', '')
        if not password:
            self.set_status(400)
            await self.finish({'message': 'Password missing'})
            return

        with self.make_session() as session:
            user = session.query(User).filter(User.username == username).first()
            if not user:
                self.set_status(401)
                await self.finish({'message': 'Invalid username/password'})
                return

            if not user.is_admin:
                if not self.get_current_show():
                    self.set_status(403)
                    await self.finish({
                        'message': 'Non admin user cannot log in without a loaded show'
                    })
                    return

                if user.show_id != self.get_current_show()['id']:
                    self.set_status(403)
                    await self.finish({'message': 'Loaded show does not match user'})
                    return

            password_equal = await IOLoop.current().run_in_executor(
                None,
                bcrypt.checkpw,
                escape.utf8(password),
                escape.utf8(user.password),
            )

            if password_equal:
                self.set_secure_cookie('digiscript_user_id', str(user.id))
                self.set_status(200)
                await self.finish({'message': 'Successful log in'})
            else:
                self.set_status(401)
                await self.finish({'message': 'Invalid username/password'})


@ApiRoute('auth/logout', ApiVersion.v1)
class LogoutHandler(BaseAPIController):
    @web.authenticated
    async def post(self):
        if self.current_user:
            self.clear_cookie('digiscript_user_id')
            self.set_status(200)
            await self.finish({'message': 'Successfully logged out'})
        else:
            self.set_status(401)
            await self.finish({'message': 'No user logged in'})


@ApiRoute('/auth', ApiVersion.v1)
class AuthHandler(BaseAPIController):
    @web.authenticated
    def get(self):
        self.set_status(200)
        self.finish(self.current_user)
