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
  // JSON round-trip instead of structuredClone — these arrays come from Pinia reactive state
  // (Proxy objects) which structuredClone cannot handle in some environments.
  const augmented: ScriptLine[] = JSON.parse(JSON.stringify(actualScriptPage)); // NOSONAR
  JSON.parse(JSON.stringify(insertedLines)) // NOSONAR
    .sort((a: number, b: number) => a - b)
    .forEach((lineIndex: number) => {
      augmented.splice(lineIndex, 0, JSON.parse(JSON.stringify(tmpScriptPage[lineIndex]))); // NOSONAR
    });

  const deepDiff = detailedDiff(augmented, tmpScriptPage);
  const addedIndices = Object.keys(deepDiff.added).map((x) => Number.parseInt(x, 10));
  return {
    added: addedIndices.filter((idx) => tmpScriptPage[idx]?.id == null),
    updated: [
      ...Object.keys(deepDiff.updated).map((x) => Number.parseInt(x, 10)),
      ...addedIndices.filter((idx) => tmpScriptPage[idx]?.id != null),
    ],
    deleted: [...deletedLines],
    inserted: [...insertedLines],
  };
}

let lineKeyCounter = 0;

/** A fresh, never-reused identity for a row — see `lineKeys` in the store below. */
function newLineKey(): string {
  lineKeyCounter += 1;
  return `line_${lineKeyCounter}`;
}

interface EditStatus {
  canRequestEdit: boolean;
  currentEditor: string | null;
}

export interface ScriptConfigParticipant {
  internal_id: string;
  username: string | null;
}

export const useScriptConfigStore = defineStore('scriptConfig', {
  state: () => ({
    tmpScript: {} as Record<string, ScriptLine[]>,
    deletedLines: {} as Record<string, number[]>,
    insertedLines: {} as Record<string, number[]>,
    // A stable identity per row of `tmpScript`, in a parallel array rather than a field
    // on the lines: `tmpScript` is deep-compared with the saved script (computePageStatus,
    // the editor's own scriptChanges) and sent to the server, so a client-only field on
    // the lines would mark every line changed. Kept in lockstep with `tmpScript`'s own
    // splices below; used by ScriptEditor.vue as the `v-for` key, so a row's editor
    // instance follows its line when an insert/delete shifts its index, instead of being
    // reused for whichever line now sits at that index. `addPage` always creates a page's
    // array; the mutations below only touch an existing one (`?.`) and never create one,
    // since an array started mid-page would be misaligned with `tmpScript` — a page
    // populated without `addPage` just keeps the index-derived fallback keys.
    lineKeys: {} as Record<string, string[]>,
    editStatus: { canRequestEdit: false, currentEditor: null } as EditStatus,
    cutMode: false,
    // Collab model fields, kept alongside the old single-editor editStatus above
    // rather than in the newer scriptDraft store, since GET_SCRIPT_CONFIG_STATUS can
    // only be handled by one store's action (useWebSocket dispatches by camelCase
    // name, first match wins, across every instantiated store). scriptDraft.ts
    // exposes these same values via getters that read from here instead of
    // duplicating the fetch.
    editors: [] as ScriptConfigParticipant[],
    cutters: [] as ScriptConfigParticipant[],
    hasDraft: false,
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
    /** Stable row key for the line at `lineIndex`. Falls back to an index-derived key
     * for a page whose `tmpScript` was populated without going through these actions. */
    getLineKey:
      (state) =>
      (page: number | string, lineIndex: number): string =>
        state.lineKeys[String(page)]?.[lineIndex] ?? `page_${page}_line_${lineIndex}`,
  },

  actions: {
    addPage(page: number, contents: ScriptLine[]): void {
      // JSON round-trip instead of structuredClone — reactive Pinia arrays (Proxy objects)
      // cannot be structuredCloned in some environments.
      this.tmpScript[String(page)] = JSON.parse(JSON.stringify(contents)); // NOSONAR
      this.lineKeys[String(page)] = contents.map(() => newLineKey());
      if (!this.deletedLines[String(page)]) this.deletedLines[String(page)] = [];
      if (!this.insertedLines[String(page)]) this.insertedLines[String(page)] = [];
    },

    removePage(page: number): void {
      delete this.tmpScript[String(page)];
      delete this.lineKeys[String(page)];
      delete this.deletedLines[String(page)];
      delete this.insertedLines[String(page)];
    },

    addBlankLine(page: number, line: ScriptLine): void {
      const l = structuredClone(line);
      l.page = page;
      this.tmpScript[String(page)].push(l);
      this.lineKeys[String(page)]?.push(newLineKey());
    },

    insertBlankLine(page: number, lineIndex: number, line: ScriptLine): void {
      const pageStr = String(page);
      if (this.deletedLines[pageStr]?.includes(lineIndex)) {
        // Reuses the tombstoned slot in place (a replace, not a splice) — the
        // array's length doesn't change, so no other index needs renumbering.
        const l = structuredClone(line);
        l.page = page;
        l.id = this.tmpScript[pageStr][lineIndex].id;
        this.tmpScript[pageStr].splice(lineIndex, 1, l);
        // New content in a reused slot: a fresh key, so it doesn't look like the
        // tombstoned line it replaced.
        this.lineKeys[pageStr]?.splice(lineIndex, 1, newLineKey());
        this.deletedLines[pageStr].splice(this.deletedLines[pageStr].indexOf(lineIndex), 1);
      } else {
        const l = structuredClone(line);
        l.page = page;
        this.tmpScript[pageStr].splice(lineIndex, 0, l);
        this.lineKeys[pageStr]?.splice(lineIndex, 0, newLineKey());
        // Splicing shifts every later index up by one — deletedLines/insertedLines
        // index into the same array, so they must shift too, or a tombstone/insert
        // recorded before this one silently starts pointing at the wrong line.
        this.deletedLines[pageStr] = (this.deletedLines[pageStr] ?? []).map((i) =>
          i >= lineIndex ? i + 1 : i
        );
        this.insertedLines[pageStr] = (this.insertedLines[pageStr] ?? []).map((i) =>
          i >= lineIndex ? i + 1 : i
        );
        this.insertedLines[pageStr].push(lineIndex);
      }
    },

    setLine(page: number, lineIndex: number, line: ScriptLine): void {
      this.tmpScript[String(page)][lineIndex] = line;
    },

    deleteLine(page: number, lineIndex: number): void {
      const pageStr = String(page);
      if (this.tmpScript[pageStr][lineIndex].id === null) {
        this.tmpScript[pageStr].splice(lineIndex, 1);
        this.lineKeys[pageStr]?.splice(lineIndex, 1);
        // Splicing shifts every later index down by one — see insertBlankLine's
        // own copy of this reasoning, same bug in the opposite direction.
        this.deletedLines[pageStr] = (this.deletedLines[pageStr] ?? []).map((i) =>
          i > lineIndex ? i - 1 : i
        );
        this.insertedLines[pageStr] = (this.insertedLines[pageStr] ?? [])
          .filter((i) => i !== lineIndex)
          .map((i) => (i > lineIndex ? i - 1 : i));
      } else {
        this.deletedLines[pageStr] ??= [];
        this.deletedLines[pageStr].push(lineIndex);
        if (this.insertedLines[pageStr]?.includes(lineIndex)) {
          this.insertedLines[pageStr].splice(this.insertedLines[pageStr].indexOf(lineIndex), 1);
        }
      }
    },

    resetTracking(page: number): void {
      this.deletedLines[String(page)] = [];
      this.insertedLines[String(page)] = [];
    },

    emptyScript(): void {
      this.tmpScript = {};
      this.lineKeys = {};
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
        this.editors = data.editors ?? [];
        this.cutters = data.cutters ?? [];
        this.hasDraft = data.hasDraft ?? false;
      } else {
        log.error('Unable to get script config status');
      }
    },

    async requestEditFailure(data?: { reason?: string }): Promise<void> {
      // Also fires for a rejected REQUEST_SCRIPT_CUTS (same ACTION, e.g. a cutter or
      // editor already in the way, or a live show) — "Unable to edit script" is the
      // closest one-size-fits-all label. The server sends a reason (mode mismatch, a
      // live show, a cutter/editor in the way, missing permission); show it.
      toast.error(data?.reason ? `Unable to edit script: ${data.reason}` : 'Unable to edit script');
      await this.getScriptConfigStatus();
      this.cutMode = false;
    },
  },
});
