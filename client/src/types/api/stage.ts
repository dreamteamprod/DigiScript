export interface Crew {
  id: number;
  show_id: number;
  first_name: string;
  last_name: string | null;
}

export interface CrewAssignment {
  id: number;
  crew_id: number;
  scene_id: number;
  assignment_type: 'set' | 'strike';
  prop_id: number | null;
  scenery_id: number | null;
}

export interface SceneryType {
  id: number;
  show_id: number;
  name: string;
  description: string | null;
}

export interface Scenery {
  id: number;
  show_id: number;
  scenery_type_id: number;
  name: string;
  description: string | null;
}

export interface SceneryAllocation {
  id: number;
  scenery_id: number;
  scene_id: number;
}

export interface PropType {
  id: number;
  show_id: number;
  name: string;
  description: string | null;
}

export interface Props {
  id: number;
  show_id: number;
  prop_type_id: number;
  name: string;
  description: string | null;
}

export interface PropsAllocation {
  id: number;
  props_id: number;
  scene_id: number;
}
