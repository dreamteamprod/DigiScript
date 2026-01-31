"""
Shared helper functions for stage item controllers (props, scenery).

These helpers reduce code duplication by extracting common validation
and CRUD patterns used across Props and Scenery controllers.
"""

from sqlalchemy import select
from tornado import escape

from controllers.api.constants import (
    ERROR_ALLOCATION_NOT_FOUND,
    ERROR_ID_MISSING,
    ERROR_INVALID_ID,
    ERROR_NAME_MISSING,
    ERROR_SCENE_ID_MISSING,
    ERROR_SCENE_NOT_FOUND,
    ERROR_SHOW_NOT_FOUND,
)
from models.show import Scene, Show
from rbac.role import Role


async def handle_type_post(controller, type_model, ws_action, success_message):
    """
    Handle POST request for creating stage item types (PropType/SceneryType).

    :param controller: The controller instance
    :param type_model: SQLAlchemy model class for the type
    :param ws_action: WebSocket action to send on success
    :param success_message: Success message to return
    """
    current_show = controller.get_current_show()
    show_id = current_show["id"]

    with controller.make_session() as session:
        show = session.get(Show, show_id)
        if not show:
            controller.set_status(404)
            await controller.finish({"message": ERROR_SHOW_NOT_FOUND})
            return
        controller.requires_role(show, Role.WRITE)
        data = escape.json_decode(controller.request.body)

        name = data.get("name", None)
        if not name:
            controller.set_status(400)
            await controller.finish({"message": ERROR_NAME_MISSING})
            return

        description = data.get("description", "")

        new_type = type_model(show_id=show.id, name=name, description=description)
        session.add(new_type)
        session.commit()

        controller.set_status(200)
        await controller.finish({"id": new_type.id, "message": success_message})

        await controller.application.ws_send_to_all("NOOP", ws_action, {})


async def handle_type_patch(
    controller, type_model, ws_action, success_message, not_found_message
):
    """
    Handle PATCH request for updating stage item types.

    :param controller: The controller instance
    :param type_model: SQLAlchemy model class for the type
    :param ws_action: WebSocket action to send on success
    :param success_message: Success message to return
    :param not_found_message: Not found error message
    """
    current_show = controller.get_current_show()
    show_id = current_show["id"]

    with controller.make_session() as session:
        show = session.get(Show, show_id)
        if not show:
            controller.set_status(404)
            await controller.finish({"message": ERROR_SHOW_NOT_FOUND})
            return
        controller.requires_role(show, Role.WRITE)
        data = escape.json_decode(controller.request.body)

        type_id = data.get("id", None)
        if not type_id:
            controller.set_status(400)
            await controller.finish({"message": ERROR_ID_MISSING})
            return

        entry = session.get(type_model, type_id)
        if not entry:
            controller.set_status(404)
            await controller.finish({"message": not_found_message})
            return

        name = data.get("name", None)
        description = data.get("description", "")
        if not name:
            controller.set_status(400)
            await controller.finish({"message": ERROR_NAME_MISSING})
            return

        entry.name = name
        entry.description = description
        session.commit()

        controller.set_status(200)
        await controller.finish({"message": success_message})

        await controller.application.ws_send_to_all("NOOP", ws_action, {})


async def handle_type_delete(
    controller,
    type_model,
    ws_actions,
    success_message,
    not_found_message,
):
    """
    Handle DELETE request for removing stage item types.

    :param controller: The controller instance
    :param type_model: SQLAlchemy model class for the type
    :param ws_actions: List of WebSocket actions to send on success
    :param success_message: Success message to return
    :param not_found_message: Not found error message
    """
    current_show = controller.get_current_show()
    show_id = current_show["id"]

    with controller.make_session() as session:
        show = session.get(Show, show_id)
        if not show:
            controller.set_status(404)
            await controller.finish({"message": ERROR_SHOW_NOT_FOUND})
            return
        controller.requires_role(show, Role.WRITE)

        type_id_str = controller.get_argument("id", None)
        if not type_id_str:
            controller.set_status(400)
            await controller.finish({"message": ERROR_ID_MISSING})
            return

        try:
            type_id = int(type_id_str)
        except ValueError:
            controller.set_status(400)
            await controller.finish({"message": ERROR_INVALID_ID})
            return

        entry = session.get(type_model, type_id)
        if not entry:
            controller.set_status(404)
            await controller.finish({"message": not_found_message})
            return

        session.delete(entry)
        session.commit()

        controller.set_status(200)
        await controller.finish({"message": success_message})

        for ws_action in ws_actions:
            await controller.application.ws_send_to_all("NOOP", ws_action, {})


async def validate_type_id(
    controller, data, type_model, type_id_key, error_missing, show
):
    """
    Validate a type ID from request data.

    :param controller: The controller instance
    :param data: Request data dictionary
    :param type_model: SQLAlchemy model class for the type (PropType/SceneryType)
    :param type_id_key: Key to look up in data (e.g., 'prop_type_id')
    :param error_missing: Error message constant for missing type ID
    :param show: The current show object
    :returns: Tuple of (type_instance, error_occurred). If error_occurred is True,
              the response has already been sent.
    """
    type_id = data.get(type_id_key, None)
    if not type_id:
        controller.set_status(400)
        await controller.finish({"message": error_missing})
        return None, True

    try:
        type_id = int(type_id)
    except ValueError:
        controller.set_status(400)
        await controller.finish({"message": f"Invalid {type_id_key}"})
        return None, True

    with controller.make_session() as session:
        type_instance = session.get(type_model, type_id)
        if not type_instance:
            controller.set_status(404)
            await controller.finish({"message": f"{type_model.__name__} not found"})
            return None, True

        if type_instance.show_id != show.id:
            controller.set_status(400)
            await controller.finish(
                {"message": f"Invalid {type_model.__name__.lower()} for show"}
            )
            return None, True

        return type_instance, False


async def handle_allocation_post(
    controller,
    item_model,
    item_id_key,
    allocation_model,
    allocation_item_fk,
    ws_action,
    error_item_id_missing,
    error_item_not_found,
    allocation_exists_message,
):
    """
    Handle POST request for creating allocations (props or scenery to scenes).

    :param controller: The controller instance
    :param item_model: SQLAlchemy model class for the item (Props/Scenery)
    :param item_id_key: Key in request data (e.g., 'props_id', 'scenery_id')
    :param allocation_model: SQLAlchemy model class for allocation
    :param allocation_item_fk: Name of FK column on allocation model (e.g., 'props_id')
    :param ws_action: WebSocket action to send on success
    :param error_item_id_missing: Error constant for missing item ID
    :param error_item_not_found: Error constant for item not found
    :param allocation_exists_message: Message for duplicate allocation error
    """
    current_show = controller.get_current_show()
    show_id = current_show["id"]

    with controller.make_session() as session:
        show = session.get(Show, show_id)
        if not show:
            controller.set_status(404)
            await controller.finish({"message": ERROR_SHOW_NOT_FOUND})
            return

        controller.requires_role(show, Role.WRITE)
        data = escape.json_decode(controller.request.body)

        # Validate item_id
        item_id = data.get(item_id_key, None)
        if item_id is None:
            controller.set_status(400)
            await controller.finish({"message": error_item_id_missing})
            return

        try:
            item_id = int(item_id)
        except ValueError:
            controller.set_status(400)
            await controller.finish({"message": f"Invalid {item_id_key}"})
            return

        item = session.get(item_model, item_id)
        if not item:
            controller.set_status(404)
            await controller.finish({"message": error_item_not_found})
            return

        if item.show_id != show_id:
            controller.set_status(404)
            await controller.finish({"message": error_item_not_found})
            return

        # Validate scene_id
        scene_id = data.get("scene_id", None)
        if scene_id is None:
            controller.set_status(400)
            await controller.finish({"message": ERROR_SCENE_ID_MISSING})
            return

        try:
            scene_id = int(scene_id)
        except ValueError:
            controller.set_status(400)
            await controller.finish({"message": "Invalid scene_id"})
            return

        scene: Scene = session.get(Scene, scene_id)
        if not scene:
            controller.set_status(404)
            await controller.finish({"message": ERROR_SCENE_NOT_FOUND})
            return

        if scene.show_id != show_id:
            controller.set_status(404)
            await controller.finish({"message": ERROR_SCENE_NOT_FOUND})
            return

        # Check for duplicate allocation
        item_fk_attr = getattr(allocation_model, allocation_item_fk)
        existing = session.scalars(
            select(allocation_model).where(
                item_fk_attr == item_id,
                allocation_model.scene_id == scene_id,
            )
        ).first()
        if existing:
            controller.set_status(400)
            await controller.finish({"message": allocation_exists_message})
            return

        # Create allocation using keyword arguments
        new_allocation = allocation_model(
            **{allocation_item_fk: item_id, "scene_id": scene_id}
        )
        session.add(new_allocation)
        session.commit()

        controller.set_status(200)
        await controller.finish(
            {"id": new_allocation.id, "message": "Successfully added allocation"}
        )

        await controller.application.ws_send_to_all("NOOP", ws_action, {})


async def handle_allocation_delete(
    controller,
    item_model,
    allocation_model,
    allocation_item_fk,
    ws_action,
):
    """
    Handle DELETE request for removing allocations.

    :param controller: The controller instance
    :param item_model: SQLAlchemy model class for the item (Props/Scenery)
    :param allocation_model: SQLAlchemy model class for allocation
    :param allocation_item_fk: Name of FK column on allocation model
    :param ws_action: WebSocket action to send on success
    """
    current_show = controller.get_current_show()
    show_id = current_show["id"]

    with controller.make_session() as session:
        show = session.get(Show, show_id)
        if not show:
            controller.set_status(404)
            await controller.finish({"message": ERROR_SHOW_NOT_FOUND})
            return

        controller.requires_role(show, Role.WRITE)

        allocation_id_str = controller.get_argument("id", None)
        if not allocation_id_str:
            controller.set_status(400)
            await controller.finish({"message": ERROR_ID_MISSING})
            return

        try:
            allocation_id = int(allocation_id_str)
        except ValueError:
            controller.set_status(400)
            await controller.finish({"message": ERROR_INVALID_ID})
            return

        allocation = session.get(allocation_model, allocation_id)
        if not allocation:
            controller.set_status(404)
            await controller.finish({"message": ERROR_ALLOCATION_NOT_FOUND})
            return

        # Verify the allocation belongs to an item in this show
        item_id = getattr(allocation, allocation_item_fk)
        item = session.get(item_model, item_id)
        if not item or item.show_id != show_id:
            controller.set_status(404)
            await controller.finish({"message": ERROR_ALLOCATION_NOT_FOUND})
            return

        session.delete(allocation)
        session.commit()

        controller.set_status(200)
        await controller.finish({"message": "Successfully deleted allocation"})

        await controller.application.ws_send_to_all("NOOP", ws_action, {})
