import { defineStore } from 'pinia';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import type {
  ScriptLine,
  StageDirectionStyle,
  CompiledScript,
  ScriptCut,
} from '@/types/api/script';
import type { Cue, CueGroup } from '@/types/api/cues';

export const useScriptStore = defineStore('script', {
  state: () => ({
    script: {} as Record<string, ScriptLine[]>,
    stageDirectionStyles: [] as StageDirectionStyle[],
    compiledScripts: [] as CompiledScript[],
    cuts: [] as ScriptCut[],
    maxPage: 1,
    cues: {} as Record<string, Cue[]>,
    cueGroups: [] as CueGroup[],
  }),

  getters: {
    getScriptPage:
      (state) =>
      (page: number | string): ScriptLine[] =>
        state.script[String(page)] ?? [],
    stageDirectionStyleById:
      (state) =>
      (id: number | null): StageDirectionStyle | null =>
        id == null ? null : (state.stageDirectionStyles.find((s) => s.id === id) ?? null),
    cuesForLine:
      (state) =>
      (lineId: number | null): Cue[] =>
        lineId == null ? [] : (state.cues[String(lineId)] ?? []),
    cueGroupById:
      (state) =>
      (id: number | null): CueGroup | null =>
        id == null ? null : (state.cueGroups.find((g) => g.id === id) ?? null),
    groupedCuesForLine:
      (state) =>
      (
        lineId: number | null
      ): {
        individual: Cue[];
        groups: { group: CueGroup; cues: Cue[] }[];
        merged: (
          | { type: 'individual'; cue: Cue; line_position: number | null }
          | { type: 'group'; group: CueGroup; cues: Cue[]; line_position: number | null }
        )[];
      } => {
        if (lineId == null) return { individual: [], groups: [], merged: [] };
        const allCues = state.cues[String(lineId)] ?? [];
        const individual = allCues.filter((c) => c.group_id == null);
        const groupMap = new Map<number, Cue[]>();
        for (const cue of allCues) {
          if (cue.group_id != null) {
            if (!groupMap.has(cue.group_id)) groupMap.set(cue.group_id, []);
            groupMap.get(cue.group_id)!.push(cue);
          }
        }
        const groups: { group: CueGroup; cues: Cue[] }[] = [];
        for (const [groupId, cues] of groupMap) {
          const group = state.cueGroups.find((g) => g.id === groupId);
          if (group) {
            const sorted = [...cues].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
            groups.push({ group, cues: sorted });
          }
        }
        const merged: (
          | { type: 'individual'; cue: Cue; line_position: number | null }
          | { type: 'group'; group: CueGroup; cues: Cue[]; line_position: number | null }
        )[] = [
          ...individual.map((c) => ({
            type: 'individual' as const,
            cue: c,
            line_position: c.line_position,
          })),
          ...groups.map((g) => ({
            type: 'group' as const,
            group: g.group,
            cues: g.cues,
            line_position: g.cues[0]?.line_position ?? null,
          })),
        ];
        merged.sort((a, b) => {
          if (a.line_position == null && b.line_position == null) return 0;
          if (a.line_position == null) return 1;
          if (b.line_position == null) return -1;
          return a.line_position - b.line_position;
        });
        return { individual, groups, merged };
      },
    lineOrderIndex(state): Map<number, { page: number; index: number }> {
      const index = new Map<number, { page: number; index: number }>();
      for (const [pageStr, lines] of Object.entries(state.script)) {
        const page = Number(pageStr);
        lines.forEach((line, lineIndex) => {
          if (line.id != null) index.set(line.id, { page, index: lineIndex });
        });
      }
      return index;
    },
    orderedCueEntries(state): { cue: Cue; page: number; index: number }[] {
      const order = this.lineOrderIndex;
      const entries: { cue: Cue; page: number; index: number }[] = [];
      for (const [lineIdStr, cuesForLine] of Object.entries(state.cues)) {
        const position = order.get(Number(lineIdStr));
        if (!position) continue;
        for (const cue of cuesForLine) {
          entries.push({ cue, page: position.page, index: position.index });
        }
      }
      entries.sort((a, b) => {
        if (a.page !== b.page) return a.page - b.page;
        if (a.index !== b.index) return a.index - b.index;
        return (a.cue.line_position ?? 0) - (b.cue.line_position ?? 0);
      });
      return entries;
    },
    lastCuePerTypeAt(): (page: number, lineIndex: number) => Record<number, Cue> {
      const entries = this.orderedCueEntries;
      return (page: number, lineIndex: number): Record<number, Cue> => {
        const result: Record<number, Cue> = {};
        for (const entry of entries) {
          if (entry.page > page || (entry.page === page && entry.index > lineIndex)) break;
          if (entry.cue.cue_type_id != null) {
            result[entry.cue.cue_type_id] = entry.cue;
          }
        }
        return result;
      };
    },
  },

  actions: {
    async loadScriptPage(page: number | string): Promise<void> {
      const params = new URLSearchParams({ page: String(page) });
      const response = await fetch(`${makeURL('/api/v1/show/script')}?${params}`);
      if (response.ok) {
        const data = await response.json();
        this.script[String(data.page)] = data.lines;
      } else {
        log.error('Unable to load script page');
      }
    },

    async scriptPageChanged(data: { page: number }): Promise<void> {
      const pageStr = String(data.page);
      if (Object.hasOwn(this.script, pageStr)) {
        await this.loadScriptPage(data.page);
        const scriptConfigStore = useScriptConfigStore();
        if (Object.hasOwn(scriptConfigStore.tmpScript, pageStr)) {
          scriptConfigStore.addPage(data.page, this.getScriptPage(data.page));
        }
      }
    },

    async saveNewPage(page: number, lines: ScriptLine[]): Promise<boolean> {
      const params = new URLSearchParams({ page: String(page) });
      const response = await fetch(`${makeURL('/api/v1/show/script')}?${params}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(lines),
      });
      return response.ok;
    },

    async saveChangedPage(
      page: number,
      payload: { page: ScriptLine[]; status: unknown }
    ): Promise<boolean> {
      const params = new URLSearchParams({ page: String(page) });
      const response = await fetch(`${makeURL('/api/v1/show/script')}?${params}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      return response.ok;
    },

    async getMaxPage(): Promise<boolean> {
      const response = await fetch(makeURL('/api/v1/show/script/max_page'));
      if (response.ok) {
        const data = await response.json();
        this.maxPage = data.max_page;
        return true;
      }
      log.error('Unable to fetch max page');
      return false;
    },

    async getStageDirectionStyles(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/script/stage_direction_styles'));
      if (response.ok) {
        const data = await response.json();
        this.stageDirectionStyles = data.styles;
      } else {
        log.error('Unable to load stage direction styles');
      }
    },

    async addStageDirectionStyle(style: Partial<StageDirectionStyle>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/script/stage_direction_styles'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(style),
      });
      if (response.ok) {
        await this.getStageDirectionStyles();
        toast.success('Added new stage direction style!');
      } else {
        toast.error('Unable to add new stage direction style');
      }
    },

    async updateStageDirectionStyle(style: Partial<StageDirectionStyle>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/script/stage_direction_styles'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(style),
      });
      if (response.ok) {
        await this.getStageDirectionStyles();
        toast.success('Updated stage direction style!');
      } else {
        toast.error('Unable to edit stage direction style');
      }
    },

    async deleteStageDirectionStyle(id: number): Promise<void> {
      const params = new URLSearchParams({ id: String(id) });
      const response = await fetch(
        `${makeURL('/api/v1/show/script/stage_direction_styles')}?${params}`,
        { method: 'DELETE' }
      );
      if (response.ok) {
        await this.getStageDirectionStyles();
        toast.success('Deleted stage direction style!');
      } else {
        toast.error('Unable to delete stage direction style');
      }
    },

    async getImportableStyles(): Promise<unknown> {
      const response = await fetch(makeURL('/api/v1/show/script/stage_direction_styles/import'));
      if (!response.ok) throw new Error('Failed to fetch importable styles');
      return response.json();
    },

    async getCompiledScripts(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/script/compiled_scripts'));
      if (response.ok) {
        const data = await response.json();
        this.compiledScripts = data.scripts;
      } else {
        log.error('Unable to load compiled scripts');
      }
    },

    async generateCompiledScript(revisionId: number): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/script/compiled_scripts'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ revision_id: revisionId }),
      });
      if (response.ok) {
        await this.getCompiledScripts();
        toast.success('Generated compiled script!');
      } else {
        toast.error('Unable to generate compiled script');
      }
    },

    async deleteCompiledScript(revisionId: number): Promise<void> {
      const params = new URLSearchParams({ revision_id: String(revisionId) });
      const response = await fetch(`${makeURL('/api/v1/show/script/compiled_scripts')}?${params}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        await this.getCompiledScripts();
        toast.success('Deleted compiled script!');
      } else {
        toast.error('Unable to delete compiled script');
      }
    },

    async getCuts(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/script/cuts'));
      if (response.ok) {
        const data = await response.json();
        this.cuts = data.cuts;
      } else {
        log.error('Unable to load script cuts');
      }
    },

    async saveCuts(cuts: ScriptCut[]): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/script/cuts'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cuts }),
      });
      if (response.ok) {
        await this.getCuts();
        toast.success('Saved script cuts!');
      } else {
        toast.error('Unable to save script cuts');
      }
    },

    clearScript(): void {
      this.script = {};
    },

    async loadCues(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/cues'));
      if (response.ok) {
        const data = await response.json();
        this.cues = data.cues as Record<string, Cue[]>;
        this.cueGroups = (data.cue_groups ?? []) as CueGroup[];
      } else {
        log.error('Unable to load cues');
      }
    },

    async addNewCue(cue: { cueType: number; ident: string; lineId: number }): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/cues'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cue),
      });
      if (response.ok) {
        await this.loadCues();
        toast.success('Added new cue!');
      } else {
        toast.error('Unable to add new cue');
      }
    },

    async editCue(cue: {
      cueId: number;
      cueType: number;
      ident: string;
      lineId: number;
    }): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/cues'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cue),
      });
      if (response.ok) {
        await this.loadCues();
        toast.success('Edited cue!');
      } else {
        toast.error('Unable to edit cue');
      }
    },

    async deleteCue(cue: { cueId: number; lineId: number }): Promise<void> {
      const params = new URLSearchParams({
        cueId: String(cue.cueId),
        lineId: String(cue.lineId),
      });
      const response = await fetch(`${makeURL('/api/v1/show/cues')}?${params}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        await this.loadCues();
        toast.success('Deleted cue!');
      } else {
        toast.error('Unable to delete cue');
      }
    },

    async addCueGroup(payload: {
      cueTypeId: number;
      labelOverride?: string;
      lineId: number;
      cues: { ident: string; sortOrder: number }[];
    }): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/cues/groups'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        await this.loadCues();
        toast.success('Added cue group!');
      } else {
        toast.error('Unable to add cue group');
      }
    },

    async editCueGroup(payload: {
      groupId: number;
      labelOverride?: string;
      lineId: number;
      cues: { id?: number; ident: string; sortOrder: number }[];
    }): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/cues/groups'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        await this.loadCues();
        toast.success('Edited cue group!');
      } else {
        toast.error('Unable to edit cue group');
      }
    },

    async deleteCueGroup(payload: { groupId: number; lineId: number }): Promise<void> {
      const params = new URLSearchParams({
        groupId: String(payload.groupId),
        lineId: String(payload.lineId),
      });
      const response = await fetch(`${makeURL('/api/v1/show/cues/groups')}?${params}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        await this.loadCues();
        toast.success('Deleted cue group!');
      } else {
        toast.error('Unable to delete cue group');
      }
    },

    async searchCues(payload: {
      identifier: string;
      cueTypeId: number;
    }): Promise<Record<string, unknown>> {
      const params = new URLSearchParams({
        identifier: payload.identifier,
        cue_type_id: String(payload.cueTypeId),
      });
      const response = await fetch(`${makeURL('/api/v1/show/cues/search')}?${params}`);
      if (response.ok) {
        return response.json() as Promise<Record<string, unknown>>;
      }
      log.error('Unable to search for cue');
      throw new Error('Cue search failed');
    },
  },
});
