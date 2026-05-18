import { defineStore } from 'pinia';
import { detailedDiff } from 'deep-object-diff';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';
import type { ScriptLine, PageStatus } from '@/types/api/script';

/**
 * Computes the page status object (added/updated/deleted/inserted) to send to the PATCH endpoint.
 *
 * deepDiff.added fires on a line index whenever *any* nested property is new — including a new
 * element in line_parts. Only lines with id == null are truly new; lines with an existing id that
 * have nested additions must be treated as updates instead.
 */
export function computePageStatus(
  actualScriptPage: ScriptLine[],
  tmpScriptPage: ScriptLine[],
  deletedLines: number[],
  insertedLines: number[]
): PageStatus {
  const augmented: ScriptLine[] = JSON.parse(JSON.stringify(actualScriptPage));
  JSON.parse(JSON.stringify(insertedLines))
    .sort((a: number, b: number) => a - b)
    .forEach((lineIndex: number) => {
      augmented.splice(lineIndex, 0, JSON.parse(JSON.stringify(tmpScriptPage[lineIndex])));
    });

  const deepDiff = detailedDiff(augmented, tmpScriptPage);
  const addedIndices = Object.keys(deepDiff.added).map((x) => parseInt(x, 10));
  return {
    added: addedIndices.filter((idx) => tmpScriptPage[idx]?.id == null),
    updated: [
      ...Object.keys(deepDiff.updated).map((x) => parseInt(x, 10)),
      ...addedIndices.filter((idx) => tmpScriptPage[idx]?.id != null),
    ],
    deleted: [...deletedLines],
    inserted: [...insertedLines],
  };
}

interface EditStatus {
  canRequestEdit: boolean;
  currentEditor: string | null;
}

export const useScriptConfigStore = defineStore('scriptConfig', {
  state: () => ({
    tmpScript: {} as Record<string, ScriptLine[]>,
    deletedLines: {} as Record<string, number[]>,
    insertedLines: {} as Record<string, number[]>,
    editStatus: { canRequestEdit: false, currentEditor: null } as EditStatus,
    cutMode: false,
  }),

  getters: {
    getTmpPage:
      (state) =>
      (page: number | string): ScriptLine[] =>
        state.tmpScript[String(page)] ?? [],
    getDeletedLines:
      (state) =>
      (page: number | string): number[] =>
        state.deletedLines[String(page)] ?? [],
    getInsertedLines:
      (state) =>
      (page: number | string): number[] =>
        state.insertedLines[String(page)] ?? [],
  },

  actions: {
    addPage(page: number, contents: ScriptLine[]): void {
      // JSON round-trip instead of structuredClone — reactive Pinia arrays (Proxy objects)
      // cannot be structuredCloned in some environments.
      this.tmpScript[String(page)] = JSON.parse(JSON.stringify(contents));
      if (!this.deletedLines[String(page)]) this.deletedLines[String(page)] = [];
      if (!this.insertedLines[String(page)]) this.insertedLines[String(page)] = [];
    },

    removePage(page: number): void {
      delete this.tmpScript[String(page)];
      delete this.deletedLines[String(page)];
      delete this.insertedLines[String(page)];
    },

    addBlankLine(page: number, line: ScriptLine): void {
      const l = JSON.parse(JSON.stringify(line));
      l.page = page;
      this.tmpScript[String(page)].push(l);
    },

    insertBlankLine(page: number, lineIndex: number, line: ScriptLine): void {
      const pageStr = String(page);
      if (this.deletedLines[pageStr]?.includes(lineIndex)) {
        const l = JSON.parse(JSON.stringify(line));
        l.page = page;
        l.id = this.tmpScript[pageStr][lineIndex].id;
        this.tmpScript[pageStr].splice(lineIndex, 1, l);
        this.deletedLines[pageStr].splice(this.deletedLines[pageStr].indexOf(lineIndex), 1);
      } else {
        const l = JSON.parse(JSON.stringify(line));
        l.page = page;
        this.tmpScript[pageStr].splice(lineIndex, 0, l);
        if (!this.insertedLines[pageStr]) this.insertedLines[pageStr] = [];
        this.insertedLines[pageStr].push(lineIndex);
      }
    },

    setLine(page: number, lineIndex: number, line: ScriptLine): void {
      this.tmpScript[String(page)][lineIndex] = line;
    },

    deleteLine(page: number, lineIndex: number): void {
      const pageStr = String(page);
      if (this.tmpScript[pageStr][lineIndex].id !== null) {
        if (!this.deletedLines[pageStr]) this.deletedLines[pageStr] = [];
        this.deletedLines[pageStr].push(lineIndex);
      } else {
        this.tmpScript[pageStr].splice(lineIndex, 1);
      }
      if (this.insertedLines[pageStr]?.includes(lineIndex)) {
        this.insertedLines[pageStr].splice(this.insertedLines[pageStr].indexOf(lineIndex), 1);
      }
    },

    resetTracking(page: number): void {
      this.deletedLines[String(page)] = [];
      this.insertedLines[String(page)] = [];
    },

    emptyScript(): void {
      this.tmpScript = {};
      this.deletedLines = {};
      this.insertedLines = {};
    },

    setCutMode(val: boolean): void {
      this.cutMode = val;
    },

    setEditStatus(status: EditStatus): void {
      this.editStatus = status;
    },

    async getScriptConfigStatus(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show/script/config'));
      if (response.ok) {
        const data = await response.json();
        this.editStatus = {
          canRequestEdit: data.canRequestEdit,
          currentEditor: data.currentEditor,
        };
      } else {
        log.error('Unable to get script config status');
      }
    },

    async requestEditFailure(): Promise<void> {
      toast.error('Unable to edit script');
      await this.getScriptConfigStatus();
      this.cutMode = false;
    },
  },
});
