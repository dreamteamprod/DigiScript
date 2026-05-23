import { defineStore } from 'pinia';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';
import type { ActiveToast } from 'vue-toast-notification';

let noLeaderToast: ActiveToast | null = null;
import { detectMicConflicts } from '@/js/micConflictUtils';
import type { MicConflict, MicConflictResult } from '@/js/micConflictUtils';
import type { Cast, Character, CharacterGroup, Act, Scene } from '@/types/api/show';
import type { CueType } from '@/types/api/cues';
import type { ShowSession, Interval, SessionTag } from '@/types/api/session';
import type { ScriptRevision } from '@/types/api/script';
import type { Microphone } from '@/types/api/microphones';
import { useSystemStore } from '@/stores/system';

interface ScriptMode {
  key: string;
  value: number;
}

export const useShowStore = defineStore('show', {
  state: () => ({
    castList: [] as Cast[],
    characterList: [] as Character[],
    characterGroupList: [] as CharacterGroup[],
    actList: [] as Act[],
    sceneList: [] as Scene[],
    cueTypes: [] as CueType[],
    sessions: [] as ShowSession[],
    currentSession: null as ShowSession | null,
    currentInterval: null as Interval | null,
    sessionFollowData: {} as Record<string, unknown>,
    microphones: [] as Microphone[],
    // API returns a dict keyed by mic ID (not a flat array)
    micAllocations: {} as Record<string, { scene_id: number; character_id: number }[]>,
    scriptModes: [] as ScriptMode[],
    sessionTags: [] as SessionTag[],
    scriptRevisions: [] as ScriptRevision[],
    currentRevision: null as number | null,
    stageManagerMode: false,
  }),

  persist: {
    pick: ['stageManagerMode'],
  },

  getters: {
    castDict: (state): Record<number, Cast> =>
      Object.fromEntries(state.castList.map((c) => [c.id, c])),
    castById:
      (state): ((id: number | null) => Cast | null) =>
      (id) => {
        const dict: Record<number, Cast> = Object.fromEntries(state.castList.map((c) => [c.id, c]));
        return id != null ? (dict[id] ?? null) : null;
      },

    characterDict: (state): Record<number, Character> =>
      Object.fromEntries(state.characterList.map((c) => [c.id, c])),
    characterById:
      (state): ((id: number | null) => Character | null) =>
      (id) => {
        const dict: Record<number, Character> = Object.fromEntries(
          state.characterList.map((c) => [c.id, c])
        );
        return id != null ? (dict[id] ?? null) : null;
      },

    actDict: (state): Record<number, Act> =>
      Object.fromEntries(state.actList.map((a) => [a.id, a])),
    actById:
      (state): ((id: number | null) => Act | null) =>
      (id) => {
        const dict: Record<number, Act> = Object.fromEntries(state.actList.map((a) => [a.id, a]));
        return id != null ? (dict[id] ?? null) : null;
      },

    sceneDict: (state): Record<number, Scene> =>
      Object.fromEntries(state.sceneList.map((s) => [s.id, s])),
    sceneById:
      (state): ((id: number | null) => Scene | null) =>
      (id) => {
        const dict: Record<number, Scene> = Object.fromEntries(
          state.sceneList.map((s) => [s.id, s])
        );
        return id != null ? (dict[id] ?? null) : null;
      },

    cueTypesDict: (state): Record<number, CueType> =>
      Object.fromEntries(state.cueTypes.map((ct) => [ct.id, ct])),
    cueTypeById:
      (state): ((id: number | null) => CueType | null) =>
      (id) => {
        const dict: Record<number, CueType> = Object.fromEntries(
          state.cueTypes.map((ct) => [ct.id, ct])
        );
        return id != null ? (dict[id] ?? null) : null;
      },

    microphoneDict: (state): Record<number, Microphone> =>
      Object.fromEntries(state.microphones.map((m) => [m.id, m])),
    microphoneById:
      (state): ((id: number | null) => Microphone | null) =>
      (id) => {
        const dict: Record<number, Microphone> = Object.fromEntries(
          state.microphones.map((m) => [m.id, m])
        );
        return id != null ? (dict[id] ?? null) : null;
      },

    sessionTagsDict: (state): Record<number, SessionTag> =>
      Object.fromEntries(state.sessionTags.map((t) => [t.id, t])),
    sessionTagById:
      (state): ((id: number | null) => SessionTag | null) =>
      (id) => {
        const dict: Record<number, SessionTag> = Object.fromEntries(
          state.sessionTags.map((t) => [t.id, t])
        );
        return id != null ? (dict[id] ?? null) : null;
      },

    scriptRevisionById:
      (state): ((id: number | null) => ScriptRevision | null) =>
      (id) => {
        return id != null ? (state.scriptRevisions.find((r) => r.id === id) ?? null) : null;
      },

    orderedScenes(state): Scene[] {
      const currentShow = useSystemStore().currentShow;
      if (!currentShow?.first_act_id || !state.sceneList.length || !state.actList.length) {
        return [];
      }
      const actById: Record<number, Act> = Object.fromEntries(state.actList.map((a) => [a.id, a]));
      const sceneById: Record<number, Scene> = Object.fromEntries(
        state.sceneList.map((s) => [s.id, s])
      );
      const scenes: Scene[] = [];
      let currentAct: Act | null = actById[currentShow.first_act_id] ?? null;
      while (currentAct != null) {
        let currentScene: Scene | null =
          currentAct.first_scene != null ? (sceneById[currentAct.first_scene] ?? null) : null;
        while (currentScene != null) {
          scenes.push(currentScene);
          currentScene =
            currentScene.next_scene != null ? (sceneById[currentScene.next_scene] ?? null) : null;
        }
        currentAct = currentAct.next_act != null ? (actById[currentAct.next_act] ?? null) : null;
      }
      return scenes;
    },

    micConflicts(state): MicConflictResult {
      const allocationsObj: Record<string, Record<string, number | null>> = {};
      Object.keys(state.micAllocations).forEach((micId) => {
        const allocs = state.micAllocations[micId];
        const sceneData: Record<string, number | null> = {};
        if (Array.isArray(allocs)) {
          allocs.forEach((alloc) => {
            sceneData[String(alloc.scene_id)] = alloc.character_id;
          });
        }
        allocationsObj[micId] = sceneData;
      });
      return detectMicConflicts(
        allocationsObj,
        state.sceneList,
        state.actList,
        useSystemStore().currentShow,
        state.characterList,
        state.castList
      );
    },

    conflictsByScene(): Record<number, MicConflict[]> {
      return this.micConflicts.conflictsByScene;
    },
    conflictsByMic(): Record<number, MicConflict[]> {
      return this.micConflicts.conflictsByMic;
    },
    micTimelineData(state): {
      scenes: Scene[];
      allocations: Record<string, { scene_id: number; character_id: number }[]>;
      conflicts: MicConflict[];
      microphones: Microphone[];
      characters: Character[];
    } {
      return {
        scenes: this.orderedScenes,
        allocations: state.micAllocations,
        conflicts: this.micConflicts.conflicts,
        microphones: state.microphones,
        characters: state.characterList,
      };
    },
  },

  actions: {
    // Cast
    async getCastList(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/cast'));
      if (response.ok) {
        const data = await response.json();
        this.castList = data.cast;
      } else {
        log.error('Unable to get cast list');
      }
    },
    async addCastMember(member: Partial<Cast>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/cast'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(member),
      });
      if (response.ok) {
        await this.getCastList();
        toast.success('Added new cast member!');
      } else {
        log.error('Unable to add new cast member');
        toast.error('Unable to add new cast member');
      }
    },
    async updateCastMember(member: Partial<Cast>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/cast'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(member),
      });
      if (response.ok) {
        await this.getCastList();
        toast.success('Updated cast member!');
      } else {
        log.error('Unable to edit cast member');
        toast.error('Unable to edit cast member');
      }
    },
    async deleteCastMember(id: number): Promise<void> {
      const params = new URLSearchParams({ id: String(id) });
      const response = await fetch(`${makeURL('/api/v1/show/cast')}?${params}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        await this.getCastList();
        toast.success('Deleted cast member!');
      } else {
        log.error('Unable to delete cast member');
        toast.error('Unable to delete cast member');
      }
    },

    // Characters
    async getCharacterList(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/character'));
      if (response.ok) {
        const data = await response.json();
        this.characterList = data.characters;
      } else {
        log.error('Unable to get characters list');
      }
    },
    async addCharacter(character: Partial<Character>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/character'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(character),
      });
      if (response.ok) {
        await this.getCharacterList();
        toast.success('Added new character!');
      } else {
        log.error('Unable to add new character');
        toast.error('Unable to add new character');
      }
    },
    async updateCharacter(character: Partial<Character>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/character'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(character),
      });
      if (response.ok) {
        await this.getCharacterList();
        toast.success('Updated character!');
      } else {
        log.error('Unable to edit character');
        toast.error('Unable to edit character');
      }
    },
    async deleteCharacter(id: number): Promise<void> {
      const params = new URLSearchParams({ id: String(id) });
      const response = await fetch(`${makeURL('/api/v1/show/character')}?${params}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        await this.getCharacterList();
        toast.success('Deleted character!');
      } else {
        log.error('Unable to delete character');
        toast.error('Unable to delete character');
      }
    },

    // Character Groups
    async getCharacterGroupList(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/character/group'));
      if (response.ok) {
        const data = await response.json();
        this.characterGroupList = data.character_groups;
        await this.getCharacterList();
      } else {
        log.error('Unable to get character groups list');
      }
    },
    async addCharacterGroup(group: Partial<CharacterGroup>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/character/group'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(group),
      });
      if (response.ok) {
        await this.getCharacterGroupList();
        toast.success('Added new character group!');
      } else {
        log.error('Unable to add new character group');
        toast.error('Unable to add new character group');
      }
    },
    async updateCharacterGroup(group: Partial<CharacterGroup>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/character/group'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(group),
      });
      if (response.ok) {
        await this.getCharacterGroupList();
        toast.success('Updated character group!');
      } else {
        log.error('Unable to edit character group');
        toast.error('Unable to edit character group');
      }
    },
    async deleteCharacterGroup(id: number): Promise<void> {
      const params = new URLSearchParams({ id: String(id) });
      const response = await fetch(`${makeURL('/api/v1/show/character/group')}?${params}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        await this.getCharacterGroupList();
        toast.success('Deleted character group!');
      } else {
        log.error('Unable to delete character group');
        toast.error('Unable to delete character group');
      }
    },

    // Acts
    async getActList(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/act'));
      if (response.ok) {
        const data = await response.json();
        this.actList = data.acts;
      } else {
        log.error('Unable to get acts list');
      }
    },
    async addAct(act: Partial<Act>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/act'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(act),
      });
      if (response.ok) {
        await this.getActList();
        toast.success('Added new act!');
      } else {
        log.error('Unable to add new act');
        toast.error('Unable to add new act');
      }
    },
    async updateAct(act: Partial<Act>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/act'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(act),
      });
      if (response.ok) {
        await this.getActList();
        toast.success('Updated act!');
      } else {
        log.error('Unable to edit act');
        toast.error('Unable to edit act');
      }
    },
    async deleteAct(id: number): Promise<void> {
      const params = new URLSearchParams({ id: String(id) });
      const response = await fetch(`${makeURL('/api/v1/show/act')}?${params}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        await this.getActList();
        toast.success('Deleted act!');
      } else {
        log.error('Unable to delete act');
        toast.error('Unable to delete act');
      }
    },
    async setActFirstScene(act: Partial<Act>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/act/first_scene'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(act),
      });
      if (response.ok) {
        await this.getActList();
        toast.success('Updated act!');
      } else {
        log.error('Unable to edit act');
        toast.error('Unable to edit act');
      }
    },

    // Scenes
    async getSceneList(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/scene'));
      if (response.ok) {
        const data = await response.json();
        this.sceneList = data.scenes;
      } else {
        log.error('Unable to get scenes list');
      }
    },
    async addScene(scene: Partial<Scene>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/scene'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scene),
      });
      if (response.ok) {
        await this.getSceneList();
        await this.getActList();
        toast.success('Added new scene!');
      } else {
        log.error('Unable to add new scene');
        toast.error('Unable to add new scene');
      }
    },
    async updateScene(scene: Partial<Scene>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/scene'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scene),
      });
      if (response.ok) {
        await this.getSceneList();
        await this.getActList();
        toast.success('Updated scene!');
      } else {
        log.error('Unable to edit scene');
        toast.error('Unable to edit scene');
      }
    },
    async deleteScene(id: number): Promise<void> {
      const params = new URLSearchParams({ id: String(id) });
      const response = await fetch(`${makeURL('/api/v1/show/scene')}?${params}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        await this.getSceneList();
        await this.getActList();
        toast.success('Deleted scene!');
      } else {
        log.error('Unable to delete scene');
        toast.error('Unable to delete scene');
      }
    },

    // Cue Types
    async getCueTypes(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/cues/types'));
      if (response.ok) {
        const data = await response.json();
        this.cueTypes = data.cue_types;
      } else {
        log.error('Unable to get cue types');
      }
    },
    async addCueType(cueType: Partial<CueType>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/cues/types'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cueType),
      });
      if (response.ok) {
        await this.getCueTypes();
        toast.success('Added new cue type!');
      } else {
        log.error('Unable to add new cue type');
        toast.error('Unable to add new cue type');
      }
    },
    async updateCueType(cueType: Partial<CueType>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/cues/types'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cueType),
      });
      if (response.ok) {
        await this.getCueTypes();
        toast.success('Updated cue type!');
      } else {
        log.error('Unable to edit cue type');
        toast.error('Unable to edit cue type');
      }
    },
    async deleteCueType(id: number): Promise<void> {
      const params = new URLSearchParams({ id: String(id) });
      const response = await fetch(`${makeURL('/api/v1/show/cues/types')}?${params}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        await this.getCueTypes();
        toast.success('Deleted cue type!');
      } else {
        log.error('Unable to delete cue type');
        toast.error('Unable to delete cue type');
      }
    },
    async getImportableCueTypes(): Promise<unknown> {
      const response = await fetch(makeURL('/api/v1/show/cues/types/import'));
      if (!response.ok) {
        log.error('Unable to fetch importable cue types');
        throw new Error('Failed to fetch importable cue types');
      }
      return response.json();
    },

    // Sessions
    async getShowSessionData(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/sessions'));
      if (response.ok) {
        const data = await response.json();
        this.sessions = data.sessions;
        this.currentSession = data.current_session;
        this.currentInterval = data.current_interval;
        if (this.currentSession?.client_internal_id != null) {
          noLeaderToast?.dismiss();
          noLeaderToast = null;
        }
      } else {
        log.error('Unable to get show sessions');
      }
    },

    // Microphones
    async getMicrophoneList(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/microphones'));
      if (response.ok) {
        const data = await response.json();
        this.microphones = data.microphones;
      } else {
        log.error('Unable to get microphone list');
      }
    },
    async addMicrophone(microphone: Partial<Microphone>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/microphones'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(microphone),
      });
      if (response.ok) {
        await this.getMicrophoneList();
        toast.success('Added new microphone!');
      } else {
        log.error('Unable to add new microphone');
        toast.error('Unable to add new microphone');
      }
    },
    async updateMicrophone(microphone: Partial<Microphone>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/microphones'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(microphone),
      });
      if (response.ok) {
        await this.getMicrophoneList();
        toast.success('Updated microphone!');
      } else {
        log.error('Unable to edit microphone');
        toast.error('Unable to edit microphone');
      }
    },
    async deleteMicrophone(id: number): Promise<void> {
      const params = new URLSearchParams({ id: String(id) });
      const response = await fetch(`${makeURL('/api/v1/show/microphones')}?${params}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        await this.getMicrophoneList();
        toast.success('Deleted microphone!');
      } else {
        log.error('Unable to delete microphone');
        toast.error('Unable to delete microphone');
      }
    },
    async getMicAllocations(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/microphones/allocations'));
      if (response.ok) {
        const data = await response.json();
        this.micAllocations = data.allocations;
      } else {
        log.error('Unable to get microphone allocations');
      }
    },
    async updateMicAllocations(allocations: unknown): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/microphones/allocations'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(allocations),
      });
      if (response.ok) {
        await this.getMicAllocations();
        toast.success('Updated microphone allocations!');
      } else {
        log.error('Unable to edit microphone allocations');
        toast.error('Unable to edit microphone allocations');
      }
    },

    // Script Modes
    async getScriptModes(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/script_modes'));
      if (response.ok) {
        const data = await response.json();
        this.scriptModes = data.script_modes ?? [];
      } else {
        log.error('Unable to fetch script modes');
      }
    },

    // Session Tags
    async getSessionTags(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/session/tags'));
      if (response.ok) {
        const data = await response.json();
        this.sessionTags = data.tags;
      } else {
        log.error('Unable to get session tags');
      }
    },
    async addSessionTag(tag: Partial<SessionTag>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/session/tags'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tag),
      });
      if (response.ok) {
        await this.getSessionTags();
        toast.success('Added new session tag!');
      } else {
        log.error('Unable to add session tag');
        toast.error('Unable to add session tag');
      }
    },
    async updateSessionTag(tag: Partial<SessionTag>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/session/tags'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tag),
      });
      if (response.ok) {
        await this.getSessionTags();
        toast.success('Updated session tag!');
      } else {
        log.error('Unable to edit session tag');
        toast.error('Unable to edit session tag');
      }
    },
    async deleteSessionTag(id: number): Promise<void> {
      const response = await fetch(`${makeURL('/api/v1/show/session/tags')}?id=${id}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        await this.getSessionTags();
        toast.success('Deleted session tag!');
      } else {
        log.error('Unable to delete session tag');
        toast.error('Unable to delete session tag');
      }
    },
    async getImportableSessionTags(): Promise<unknown> {
      const response = await fetch(makeURL('/api/v1/show/session/tags/import'));
      if (!response.ok) {
        log.error('Unable to fetch importable session tags');
        throw new Error('Failed to fetch importable session tags');
      }
      return response.json();
    },
    async updateSessionTags({
      sessionId,
      tagIds,
    }: {
      sessionId: number;
      tagIds: number[];
    }): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/sessions/assign-tags'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, tag_ids: tagIds }),
      });
      if (response.ok) {
        await this.getShowSessionData();
        toast.success('Updated session tags!');
      } else {
        const errorData: { message?: string } = await response.json().catch(() => ({}));
        log.error('Unable to update session tags:', errorData);
        toast.error(errorData.message || 'Unable to update session tags');
        throw new Error('Failed to update session tags');
      }
    },

    async getScriptRevisions(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/script/revisions'));
      if (response.ok) {
        const data = await response.json();
        this.scriptRevisions = data.revisions ?? [];
        this.currentRevision = data.current_revision ?? null;
      } else {
        log.error('Unable to get script revisions');
      }
    },

    async addScriptRevision(payload: {
      description: string;
      parent_revision_id?: number | null;
      set_as_current?: boolean | null;
    }): Promise<void> {
      const body: Record<string, unknown> = { description: payload.description };
      if (payload.parent_revision_id != null) body.parent_revision_id = payload.parent_revision_id;
      if (payload.set_as_current != null) body.set_as_current = payload.set_as_current;
      const response = await fetch(makeURL('/api/v1/show/script/revisions'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (response.ok) {
        await this.getScriptRevisions();
        toast.success('Added new script revision!');
      } else {
        let message = 'Unable to add new script revision';
        try {
          const data = await response.json();
          if (data.message) message = data.message;
        } catch {
          /* non-JSON body */
        }
        toast.error(message);
      }
    },

    async deleteScriptRevision(revisionId: number): Promise<void> {
      const params = new URLSearchParams({ rev_id: String(revisionId) });
      const response = await fetch(`${makeURL('/api/v1/show/script/revisions')}?${params}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        await this.getScriptRevisions();
        toast.success('Deleted script revision!');
      } else {
        let message = 'Unable to delete script revision';
        try {
          const data = await response.json();
          if (data.message) message = data.message;
        } catch {
          /* non-JSON body */
        }
        toast.error(message);
      }
    },

    async loadScriptRevision(revisionId: number): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/script/revisions/current'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_rev_id: revisionId }),
      });
      if (response.ok) {
        await this.getScriptRevisions();
        toast.success('Loaded script revision!');
      } else {
        let message = 'Unable to load script revision';
        try {
          const data = await response.json();
          if (data.message) message = data.message;
        } catch {
          /* non-JSON body */
        }
        toast.error(message);
      }
    },

    async scriptRevisionChanged(): Promise<void> {
      await this.getScriptRevisions();
    },

    clearCurrentShow(): void {
      this.castList = [];
      this.characterList = [];
      this.actList = [];
      this.sceneList = [];
      this.sessionTags = [];
      this.scriptRevisions = [];
      this.currentRevision = null;
    },

    // WS-triggered actions
    async electedLeader(): Promise<void> {
      noLeaderToast?.dismiss();
      noLeaderToast = null;
      toast.info('You are now leader of the script - other clients will follow your view');
    },
    async noLeader(): Promise<void> {
      await this.getShowSessionData();
      noLeaderToast?.dismiss();
      noLeaderToast = toast.warning('There is no script leader. Please scroll your own script!', {
        duration: 0,
        dismissible: true,
      });
    },
    scriptScroll(data: Record<string, unknown>): void {
      this.sessionFollowData = data;
    },
  },
});
