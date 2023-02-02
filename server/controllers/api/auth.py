import bcrypt
from tornado import escape
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
