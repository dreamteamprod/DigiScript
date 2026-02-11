"""Shared test fixture helpers for stage-related tests.

These helpers reduce duplication across test setUp methods that need
Show / Act / Scene / Prop / Scenery / Crew / User scaffolding.
"""

from models.show import Act, Scene, Show, ShowScriptType
from models.stage import Crew, Props, PropType, Scenery, SceneryType
from models.user import User


def create_show(session, name="Test Show"):
    """Create a show and return its ID.

    :param session: SQLAlchemy session.
    :param name: Show name.
    :returns: The new show's ID.
    :rtype: int
    """
    show = Show(name=name, script_mode=ShowScriptType.FULL)
    session.add(show)
    session.flush()
    return show.id


def create_act_with_scenes(
    session,
    show_id,
    act_name,
    num_scenes,
    *,
    interval_after=False,
    previous_act_id=None,
    link_to_show=False,
):
    """Create an act with a linked-list of scenes.

    Scenes are named "Scene 1", "Scene 2", etc. and wired via
    ``previous_scene_id``.  The act's ``first_scene`` is set automatically.

    :param session: SQLAlchemy session.
    :param show_id: Parent show ID.
    :param act_name: Display name for the act.
    :param num_scenes: Number of scenes to create.
    :param interval_after: Whether the act has an interval after it.
    :param previous_act_id: ID of the preceding act (for linked-list ordering).
    :param link_to_show: If ``True``, sets ``show.first_act`` to this act.
    :returns: Tuple of ``(act_id, [scene_id, ...])``.
    :rtype: tuple[int, list[int]]
    """
    act = Act(
        show_id=show_id,
        name=act_name,
        interval_after=interval_after,
        previous_act_id=previous_act_id,
    )
    session.add(act)
    session.flush()

    scene_ids = []
    previous_scene_id = None
    for i in range(1, num_scenes + 1):
        scene = Scene(
            show_id=show_id,
            act_id=act.id,
            name=f"Scene {i}",
            previous_scene_id=previous_scene_id,
        )
        session.add(scene)
        session.flush()
        if i == 1:
            act.first_scene = scene
        previous_scene_id = scene.id
        scene_ids.append(scene.id)

    if link_to_show:
        show = session.get(Show, show_id)
        show.first_act = act

    return act.id, scene_ids


def create_prop(session, show_id, name="Sword", type_name="Hand Props"):
    """Create a prop type and prop, returning both IDs.

    :param session: SQLAlchemy session.
    :param show_id: Parent show ID.
    :param name: Prop name.
    :param type_name: Prop type name.
    :returns: Tuple of ``(prop_type_id, prop_id)``.
    :rtype: tuple[int, int]
    """
    prop_type = PropType(show_id=show_id, name=type_name, description="")
    session.add(prop_type)
    session.flush()

    prop = Props(
        show_id=show_id,
        prop_type_id=prop_type.id,
        name=name,
        description="",
    )
    session.add(prop)
    session.flush()
    return prop_type.id, prop.id


def create_scenery(session, show_id, name="Castle Wall", type_name="Backdrops"):
    """Create a scenery type and scenery item, returning both IDs.

    :param session: SQLAlchemy session.
    :param show_id: Parent show ID.
    :param name: Scenery name.
    :param type_name: Scenery type name.
    :returns: Tuple of ``(scenery_type_id, scenery_id)``.
    :rtype: tuple[int, int]
    """
    scenery_type = SceneryType(show_id=show_id, name=type_name, description="")
    session.add(scenery_type)
    session.flush()

    scenery = Scenery(
        show_id=show_id,
        scenery_type_id=scenery_type.id,
        name=name,
        description="",
    )
    session.add(scenery)
    session.flush()
    return scenery_type.id, scenery.id


def create_crew(session, show_id, first_name="John", last_name="Doe"):
    """Create a crew member and return the ID.

    :param session: SQLAlchemy session.
    :param show_id: Parent show ID.
    :param first_name: First name.
    :param last_name: Last name.
    :returns: The new crew member's ID.
    :rtype: int
    """
    crew = Crew(show_id=show_id, first_name=first_name, last_name=last_name)
    session.add(crew)
    session.flush()
    return crew.id


def create_admin_user(session, username="admin"):
    """Create an admin user and return the ID.

    :param session: SQLAlchemy session.
    :param username: Username.
    :returns: The new user's ID.
    :rtype: int
    """
    admin = User(username=username, is_admin=True, password="test")
    session.add(admin)
    session.flush()
    return admin.id
