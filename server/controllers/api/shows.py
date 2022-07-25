from controllers.base_controller import BaseAPIController
from route import ApiRoute, ApiVersion


@ApiRoute('show', ApiVersion.v1)
class ShowController(BaseAPIController):
    def get(self):
        """
        Get a show
        """
        pass

    def post(self):
        """
        Create a new show
        """
        pass

    def patch(self):
        """
        Update a show
        """
        pass

    def delete(self):
        """
        Delete a show
        """
        pass
