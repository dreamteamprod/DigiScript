import { defineStore } from 'pinia';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';
import type {
  ScriptLine,
  StageDirectionStyle,
  CompiledScript,
  ScriptCut,
} from '@/types/api/script';
import type { Cue } from '@/types/api/cues';

export const useScriptStore = defineStore('script', {
  state: () => ({
    script: {} as Record<string, ScriptLine[]>,
    stageDirectionStyles: [] as StageDirectionStyle[],
    compiledScripts: [] as CompiledScript[],
    cuts: [] as ScriptCut[],
    maxPage: 1,
    cues: {} as Record<string, Cue[]>,
  }),

  getters: {
    getScriptPage:
      (state) =>
      (page: number | string): ScriptLine[] =>
        state.script[String(page)] ?? [],
    stageDirectionStyleById:
      (state) =>
      (id: number | null): StageDirectionStyle | null =>
        id != null ? (state.stageDirectionStyles.find((s) => s.id === id) ?? null) : null,
    cuesForLine:
      (state) =>
      (lineId: number | null): Cue[] =>
        lineId != null ? (state.cues[String(lineId)] ?? []) : [],
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
