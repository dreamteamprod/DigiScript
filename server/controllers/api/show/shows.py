from datetime import datetime
from dateutil import parser
from tornado import escape

from utils.base_controller import BaseAPIController
from models.models import Show
from models.schemas import ShowSchema
from utils.route import ApiRoute, ApiVersion
from utils.logger import get_logger


@ApiRoute('show', ApiVersion.v1)
class ShowController(BaseAPIController):
    def post(self):
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
            session.add(Show(name=show_name,
                             start_date=start_date,
                             end_date=end_date,
                             created_at=datetime.utcnow()))
            session.commit()

        self.set_status(200)
        self.write({'message': 'Successfully created show'})

    def get(self):
        current_show = self.get_current_show()

        if not current_show:
            self.set_status(400)
            self.finish({'message': 'No show loaded'})
            return

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


@ApiRoute('shows', ApiVersion.v1)
class ShowsController(BaseAPIController):

    def get(self):
        shows = []
        show_schema = ShowSchema()
        with self.make_session() as session:
            shows = session.query(Show).all()
            shows = [show_schema.dump(s) for s in shows]

        self.set_status(200)
        self.write({'shows': shows})
