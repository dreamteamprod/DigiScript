from datetime import datetime
from dateutil import parser
from tornado import escape, web

from models.script import Script, ScriptRevision
from models.show import Show
from rbac.role import Role
from schemas.schemas import ShowSchema
from utils.web.base_controller import BaseAPIController
from utils.web.web_decorators import requires_show, require_admin
from utils.web.route import ApiRoute, ApiVersion
from digi_server.logger import get_logger


@ApiRoute('show', ApiVersion.V1)
class ShowController(BaseAPIController):

    @web.authenticated
    @require_admin
    async def post(self):
        """
        Create a new show
        """
        data = escape.json_decode(self.request.body)
        get_logger().debug(f'New show data posted: {data}')

        # Name
        show_name = data.get('name', None)
        if not show_name:
            self.set_status(400)
            self.write({'message': 'Show name missing'})
            return

        # Start date
        start_date = data.get('start', None)
        if not start_date:
            self.set_status(400)
            self.write({'message': 'Start date missing'})
            return
        try:
            start_date = parser.parse(start_date)
            if not start_date:
                raise Exception
        except BaseException:
            self.set_status(400)
            self.write({'message': 'Unable to parse start date value'})
            return

        # End date
        end_date = data.get('end', None)
        if not end_date:
            self.set_status(400)
            self.write({'message': 'End date missing'})
            return
        try:
            end_date = parser.parse(end_date)
            if not end_date:
                raise Exception
        except BaseException:
            self.set_status(400)
            self.write({'message': 'Unable to parse end date value'})
            return

        if start_date > end_date or end_date < start_date:
            self.set_status(400)
            self.write({'message': 'Start date must be before or the same as the end date'})
            return

        with self.make_session() as session:
            now_time = datetime.utcnow()
            show = Show(name=show_name,
                        start_date=start_date,
                        end_date=end_date,
                        created_at=now_time,
                        edited_at=now_time)
            session.add(show)
            session.flush()

            # Configure the new script for this show
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            # Auto insert the first script revision
            script_revision = ScriptRevision(script_id=script.id,
                                             revision=1,
                                             created_at=now_time,
                                             edited_at=now_time,
                                             description='Initial script revision')
            session.add(script_revision)
            session.flush()

            # Update the script to point to the new revision
            script.current_revision = script_revision.id

            session.commit()

            should_load = bool(self.get_query_argument('load', default='False'))
            if should_load:
                await self.application.digi_settings.set('current_show', show.id)

        self.set_status(200)
        self.write({'message': 'Successfully created show'})

    @requires_show
    def get(self):
        current_show = self.get_current_show()

        show_id = current_show['id']
        show_schema = ShowSchema()
        show = None

        if show_id:
            with self.make_session() as session:
                show = session.query(Show).get(show_id)
                if show:
                    show = show_schema.dump(show)

        if show:
            self.set_status(200)
            self.write(show)
        else:
            self.set_status(404)
            self.write({'message': '404 show not found'})

    @requires_show
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show: Show = session.query(Show).get(show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                # Name
                show_name = data.get('name', None)
                if not show_name:
                    self.set_status(400)
                    self.write({'message': 'Show name missing'})
                    return
                show.name = show_name

                # Start date
                start_date = data.get('start_date', None)
                if not start_date:
                    self.set_status(400)
                    self.write({'message': 'Start date missing'})
                    return
                try:
                    start_date = parser.parse(start_date)
                    if not start_date:
                        raise Exception
                except BaseException:
                    self.set_status(400)
                    self.write({'message': 'Unable to parse start date value'})
                    return

                # End date
                end_date = data.get('end_date', None)
                if not end_date:
                    self.set_status(400)
                    self.write({'message': 'End date missing'})
                    return
                try:
                    end_date = parser.parse(end_date)
                    if not end_date:
                        raise Exception
                except BaseException:
                    self.set_status(400)
                    self.write({'message': 'Unable to parse end date value'})
                    return

                if start_date > end_date or end_date < start_date:
                    self.set_status(400)
                    self.write({
                        'message': 'Start date must be before or the same as the end date'
                    })
                    return
                show.start_date = start_date
                show.end_date = end_date

                # First act
                show.first_act_id = data.get('first_act_id', None)

                show.edited_at = datetime.utcnow()
                session.commit()

                self.set_status(200)
                await self.finish({'message': 'Successfully updated act'})

                await self.application.ws_send_to_all('NOOP', 'GET_SHOW_DETAILS', {})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})


@ApiRoute('shows', ApiVersion.V1)
class ShowsController(BaseAPIController):

    def get(self):
        shows = []
        show_schema = ShowSchema()
        with self.make_session() as session:
            shows = session.query(Show).all()
            shows = [show_schema.dump(s) for s in shows]

        self.set_status(200)
        self.write({'shows': shows})
