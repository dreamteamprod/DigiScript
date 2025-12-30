from collections import defaultdict
from typing import Dict, List, Tuple

from sqlalchemy import select
from tornado import escape

from models.mics import Microphone, MicrophoneAllocation
from models.script import Script, ScriptRevision
from models.show import Act, Character, Scene, Show
from rbac.role import Role
from schemas.schemas import MicrophoneAllocationSchema, MicrophoneSchema
from utils.show.mic_assignment import collect_character_appearances, find_best_mic
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/microphones", ApiVersion.V1)
class MicrophoneController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        mic_schema = MicrophoneSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                mics: List[Microphone] = session.scalars(
                    select(Microphone).where(Microphone.show_id == show.id)
                ).all()
                mics = [mic_schema.dump(c) for c in mics]
                self.set_status(200)
                self.finish({"microphones": mics})
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                name: str = data.get("name", None)
                if not name:
                    self.set_status(400)
                    await self.finish({"message": "Name missing"})
                    return

                other_named = session.scalars(
                    select(Microphone).where(
                        Microphone.show_id == show_id, Microphone.name == name
                    )
                ).first()
                if other_named:
                    self.set_status(400)
                    await self.finish({"message": "Name already taken"})
                    return

                description: str = data.get("description", None)

                new_microphone = Microphone(
                    show_id=show_id, name=name, description=description
                )
                session.add(new_microphone)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {
                        "id": new_microphone.id,
                        "message": "Successfully added microphone",
                    }
                )

                await self.application.ws_send_to_all("NOOP", "GET_MICROPHONE_LIST", {})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                microphone_id = data.get("id", None)
                if not microphone_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                microphone: Microphone = session.get(Microphone, microphone_id)
                if not microphone:
                    self.set_status(404)
                    await self.finish({"message": "404 microphone not found"})
                    return

                name: str = data.get("name", None)
                if not name:
                    self.set_status(400)
                    await self.finish({"message": "Name missing"})
                    return

                other_named = session.scalars(
                    select(Microphone).where(
                        Microphone.show_id == show_id,
                        Microphone.name == name,
                        Microphone.id != microphone_id,
                    )
                ).first()
                if other_named:
                    self.set_status(400)
                    await self.finish({"message": "Name already taken"})
                    return

                description: str = data.get("description", None)

                microphone.name = name
                microphone.description = description
                session.commit()

                self.set_status(200)
                await self.finish({"message": "Successfully updated microphone"})

                await self.application.ws_send_to_all("NOOP", "GET_MICROPHONE_LIST", {})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def delete(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                microphone_id = data.get("id", None)
                if not microphone_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                entry: Microphone = session.get(Microphone, microphone_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully deleted microphone"})

                    await self.application.ws_send_to_all(
                        "NOOP", "GET_MICROPHONE_LIST", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish({"message": "404 microphone not found"})
            else:
                self.set_status(404)
                await self.finish({"message": "404 microphone not found"})


@ApiRoute("show/microphones/allocations", ApiVersion.V1)
class MicrophoneAllocationsController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        allocation_schema = MicrophoneAllocationSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                mics: List[Microphone] = session.scalars(
                    select(Microphone).where(Microphone.show_id == show.id)
                ).all()

                allocations = {}
                for mic in mics:
                    allocations[mic.id] = [
                        allocation_schema.dump(alloc) for alloc in mic.allocations
                    ]

                self.set_status(200)
                self.finish({"allocations": allocations})
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                for microphone_id in data:
                    mic = session.get(Microphone, microphone_id)
                    if not mic:
                        self.set_status(404)
                        await self.finish({"message": "404 microphone not found"})
                        return

                    for scene_id in data[microphone_id]:
                        scene = session.get(Scene, scene_id)
                        if not scene:
                            self.set_status(404)
                            await self.finish({"message": "404 scene not found"})
                            return

                        existing_allocation: MicrophoneAllocation = session.scalars(
                            select(MicrophoneAllocation).where(
                                MicrophoneAllocation.scene_id == scene.id,
                                MicrophoneAllocation.mic_id == mic.id,
                            )
                        ).first()

                        character_id = data[microphone_id][scene_id]
                        if character_id:
                            character = session.get(Character, character_id)
                            if not character:
                                self.set_status(404)
                                await self.finish(
                                    {"message": "404 character not found"}
                                )
                                return

                            if existing_allocation:
                                existing_allocation.character_id = character.id
                            else:
                                session.add(
                                    MicrophoneAllocation(
                                        mic_id=mic.id,
                                        scene_id=scene.id,
                                        character_id=character.id,
                                    )
                                )
                        elif existing_allocation:
                            session.delete(existing_allocation)

                        session.flush()
                await self.application.ws_send_to_all("NOOP", "GET_MIC_ALLOCATIONS", {})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})


@ApiRoute("show/microphones/suggest", ApiVersion.V1)
class MicrophoneAutoAssignmentController(BaseAPIController):
    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                if "excluded_mics" not in data:
                    self.set_status(400)
                    await self.finish({"message": "excluded_mics missing"})
                    return
                excluded_mics: List[int] = data["excluded_mics"]

                if "static_characters" not in data:
                    self.set_status(400)
                    await self.finish({"message": "static_characters missing"})
                    return
                static_characters: List[int] = data["static_characters"]

                if "gap_mode" not in data:
                    self.set_status(400)
                    await self.finish({"message": "gap_mode missing"})
                    return
                gap_mode: str = data["gap_mode"]
                if gap_mode not in ["leave_gaps", "no_gaps"]:
                    self.set_status(400)
                    await self.finish({"message": "Invalid gap_mode value"})
                    return

                # Get all scenes in the show, and construct a list of lists, where each inner list
                # is a list of scenes in order which are not separated by an interval
                ordered_acts: List[Act] = []
                iter_act: Act = show.first_act
                if not iter_act:
                    self.set_status(400)
                    await self.finish({"message": "No acts in show"})
                    return
                while iter_act:
                    ordered_acts.append(iter_act)
                    iter_act = iter_act.next_act

                ordered_scenes: List[List[Scene]] = []
                current_scenes = []
                for act in ordered_acts:
                    iter_scene = act.first_scene
                    while iter_scene:
                        current_scenes.append(iter_scene)
                        iter_scene = iter_scene.next_scene
                    if act.interval_after:
                        ordered_scenes.append(current_scenes)
                        current_scenes = []
                if current_scenes:
                    ordered_scenes.append(current_scenes)

                if not ordered_scenes:
                    self.set_status(400)
                    await self.finish({"message": "No scenes in show"})
                    return

                # Get available microphones
                mics: List[Microphone] = session.scalars(
                    select(Microphone).where(Microphone.show_id == show.id)
                ).all()
                if not mics:
                    self.set_status(400)
                    await self.finish({"message": "No microphones available"})
                    return
                available_mic_ids = [mic.id for mic in mics]

                # Filter out excluded mics - this list is used in the allocation algorithm
                allocatable_mic_ids = [
                    mic_id
                    for mic_id in available_mic_ids
                    if mic_id not in excluded_mics
                ]
                if not allocatable_mic_ids:
                    self.set_status(400)
                    await self.finish(
                        {"message": "No microphones available for allocation"}
                    )
                    return

                # Get script and current revision
                script: Script = session.scalars(
                    select(Script).where(Script.show_id == show.id)
                ).first()
                if not script or not script.current_revision:
                    self.set_status(400)
                    await self.finish(
                        {"message": "No script or current revision available"}
                    )
                    return
                revision: ScriptRevision = session.get(
                    ScriptRevision, script.current_revision
                )

                # Load existing allocations
                existing_allocations: List[MicrophoneAllocation] = session.scalars(
                    select(MicrophoneAllocation).where(
                        MicrophoneAllocation.mic_id.in_(available_mic_ids)
                    )
                ).all()

                # Collect character appearances (only unallocated pairs)
                unallocated_appearances, character_total_lines = (
                    collect_character_appearances(
                        session, revision, existing_allocations
                    )
                )

                # Sort characters by total line count (descending) - high priority first
                sorted_characters = sorted(
                    character_total_lines.keys(),
                    key=lambda char_id: character_total_lines[char_id],
                    reverse=True,
                )

                # Build scene index map for swap cost calculations
                scene_index_map: Dict[int, int] = {}
                for scene_group in ordered_scenes:
                    for scene_index, scene in enumerate(scene_group):
                        scene_index_map[scene.id] = scene_index

                # Initialize mic usage tracker with existing allocations
                mic_usage_tracker: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
                for alloc in existing_allocations:
                    if alloc.scene_id in scene_index_map:
                        mic_usage_tracker[alloc.mic_id].append(
                            (scene_index_map[alloc.scene_id], alloc.character_id)
                        )

                new_allocations: List[Tuple[int, int, int]] = []
                hints = []

                # Assign mics per static character allocation
                static_mic_options = {
                    mic_id
                    for mic_id in allocatable_mic_ids
                    if mic_id not in mic_usage_tracker
                }
                static_sorted_characters = [
                    char_id
                    for char_id in sorted_characters
                    if char_id in static_characters
                ]
                for character_id in static_sorted_characters:
                    # Check if character already has an allocation, skip and record hint if so
                    if any(
                        alloc.character_id == character_id
                        for alloc in existing_allocations
                    ):
                        hints.append(
                            {
                                "character_id": character_id,
                                "reason": "Character already has existing microphone allocation",
                                "type": "static",
                            }
                        )
                        continue

                    # Try get next available static mic, if there are not any left, skip and record hint
                    try:
                        next_mic = static_mic_options.pop()
                    except KeyError:
                        hints.append(
                            {
                                "character_id": character_id,
                                "reason": "No available microphone for static assignment",
                                "type": "static",
                            }
                        )
                    else:
                        # Record new allocation for each scene
                        for scene_id in scene_index_map:
                            new_allocations.append((next_mic, scene_id, character_id))
                            mic_usage_tracker[next_mic].append(
                                (scene_index, character_id)
                            )

                # Assign mics per character
                for character_id in sorted_characters:
                    # Skip static characters since they are already processed
                    if character_id in static_sorted_characters:
                        continue

                    # Get all scenes where this character needs a mic (sorted by scene order)
                    character_scenes = [
                        (scene_id, line_count)
                        for (
                            scene_id,
                            char_id,
                        ), line_count in unallocated_appearances.items()
                        if char_id == character_id
                    ]
                    # Sort by scene index
                    character_scenes.sort(key=lambda x: scene_index_map.get(x[0], 0))

                    # Assign mic for each scene
                    for scene_id, line_count in character_scenes:
                        scene_index = scene_index_map.get(scene_id, 0)

                        best_mic = find_best_mic(
                            session,
                            character_id,
                            scene_id,
                            scene_index,
                            allocatable_mic_ids,
                            mic_usage_tracker,
                            existing_allocations,
                            new_allocations,
                        )

                        if best_mic:
                            # Record new allocation
                            new_allocations.append((best_mic, scene_id, character_id))
                            mic_usage_tracker[best_mic].append(
                                (scene_index, character_id)
                            )
                        else:
                            # No available mic - record hint
                            hints.append(
                                {
                                    "character_id": character_id,
                                    "scene_id": scene_id,
                                    "reason": "No available microphone",
                                    "type": "allocation",
                                }
                            )

                # Build response in PATCH-compatible format
                suggestions: Dict[int, Dict[int, int]] = {}

                # Include existing allocations in response (complete picture)
                for alloc in existing_allocations:
                    if alloc.mic_id not in suggestions:
                        suggestions[alloc.mic_id] = {}
                    suggestions[alloc.mic_id][alloc.scene_id] = alloc.character_id

                # Add new suggestions
                for mic_id, scene_id, character_id in new_allocations:
                    if mic_id not in suggestions:
                        suggestions[mic_id] = {}
                    suggestions[mic_id][scene_id] = character_id

                # Process gap mode if needed
                if gap_mode == "no_gaps":
                    for mic_id, mic_allocations in suggestions.items():
                        seen_scenes = []
                        single_character = True
                        character_id = None
                        # For each scene, see whether the same character is assigned to the mic
                        for scene_id, char_id in mic_allocations.items():
                            seen_scenes.append(scene_id)
                            if character_id is not None and char_id != character_id:
                                single_character = False
                                break
                            character_id = char_id

                        # Only proceed if a single character is assigned to this mic
                        if not single_character:
                            continue

                        # Fill in gaps for scenes where the character wasn't assigned a mic
                        gapped_scenes = set(scene_index_map.keys()) - set(seen_scenes)
                        if gapped_scenes:
                            hints.append(
                                {
                                    "character_id": character_id,
                                    "reason": "Filled gap in microphone assignment",
                                    "type": "gap_fill",
                                    "scenes": list(gapped_scenes),
                                }
                            )
                            for scene_id in gapped_scenes:
                                mic_allocations[scene_id] = character_id

                # Return response
                self.set_status(200)
                await self.finish(
                    {
                        "allocations": suggestions,
                        "hints": hints,
                    }
                )

            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
