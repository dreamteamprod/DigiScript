import Vue from 'vue';
import { detailedDiff } from 'deep-object-diff';
import log from 'loglevel';
import type { Module } from 'vuex';

import { makeURL } from '@/js/utils';
import type { RootState } from '@/types/store';
import type { ScriptLine, PageStatus } from '@/types/api/script';

interface EditStatus {
  canRequestEdit: boolean;
  currentEditor: string | null;
}

interface ScriptConfigState {
  tmpScript: Record<string, ScriptLine[]>;
  deletedLines: Record<string, number[]>;
  editStatus: EditStatus;
  cutMode: boolean;
  insertedLines: Record<string, number[]>;
}

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

const VueToast = Vue as typeof Vue & { $toast: { error: (m: string) => void } };

const module: Module<ScriptConfigState, RootState> = {
  state: {
    tmpScript: {},
    deletedLines: {},
    editStatus: {
      canRequestEdit: false,
      currentEditor: null,
    },
    cutMode: false,
    insertedLines: {},
  },
  mutations: {
    SET_EDIT_STATUS(state: ScriptConfigState, editStatus: EditStatus) {
      state.editStatus = editStatus;
    },
    ADD_PAGE(
      state: ScriptConfigState,
      { pageNo, pageContents }: { pageNo: number; pageContents: ScriptLine[] }
    ) {
      Vue.set(state.tmpScript, pageNo, pageContents);
    },
    REMOVE_PAGE(state: ScriptConfigState, pageNo: number) {
      Vue.delete(state.tmpScript, pageNo);
    },
    ADD_BLANK_LINE(
      state: ScriptConfigState,
      { pageNo, lineObj }: { pageNo: number; lineObj: ScriptLine }
    ) {
      const line: ScriptLine = JSON.parse(JSON.stringify(lineObj));
      line.page = pageNo;
      state.tmpScript[pageNo].push(line);
    },
    INSERT_BLANK_LINE(
      state: ScriptConfigState,
      { pageNo, lineIndex, lineObj }: { pageNo: number; lineIndex: number; lineObj: ScriptLine }
    ) {
      const pageNoStr = pageNo.toString();

      if (
        Object.keys(state.deletedLines).includes(pageNoStr) &&
        state.deletedLines[pageNoStr].includes(lineIndex)
      ) {
        const lineId = state.tmpScript[pageNoStr][lineIndex].id;
        const line: ScriptLine = JSON.parse(JSON.stringify(lineObj));
        line.page = pageNo;
        line.id = lineId;
        state.tmpScript[pageNo].splice(lineIndex, 1, line);
        state.deletedLines[pageNoStr].splice(state.deletedLines[pageNoStr].indexOf(lineIndex), 1);
      } else {
        const line: ScriptLine = JSON.parse(JSON.stringify(lineObj));
        line.page = pageNo;
        state.tmpScript[pageNo].splice(lineIndex, 0, line);
        if (!Object.keys(state.insertedLines).includes(pageNoStr)) {
          Vue.set(state.insertedLines, pageNoStr, []);
        }
        state.insertedLines[pageNoStr].push(lineIndex);
      }
    },
    SET_LINE(
      state: ScriptConfigState,
      { pageNo, lineIndex, lineObj }: { pageNo: number; lineIndex: number; lineObj: ScriptLine }
    ) {
      Vue.set(state.tmpScript[pageNo], lineIndex, lineObj);
    },
    DELETE_LINE(
      state: ScriptConfigState,
      { pageNo, lineIndex }: { pageNo: number; lineIndex: number }
    ) {
      const pageNoStr = pageNo.toString();
      if (state.tmpScript[pageNoStr][lineIndex].id !== null) {
        if (!Object.keys(state.deletedLines).includes(pageNoStr)) {
          Vue.set(state.deletedLines, pageNoStr, []);
        }
        state.deletedLines[pageNoStr].push(lineIndex);
      } else {
        state.tmpScript[pageNoStr].splice(lineIndex, 1);
      }
      if (
        Object.keys(state.insertedLines).includes(pageNoStr) &&
        state.insertedLines[pageNoStr].includes(lineIndex)
      ) {
        state.insertedLines[pageNoStr].splice(lineIndex, 1);
      }
    },
    RESET_DELETED(state: ScriptConfigState, pageNo: number) {
      const pageNoStr = pageNo.toString();
      if (Object.keys(state.deletedLines).includes(pageNoStr)) {
        Vue.set(state.deletedLines, pageNoStr, []);
      }
    },
    RESET_INSERTED(state: ScriptConfigState, pageNo: number) {
      const pageNoStr = pageNo.toString();
      if (Object.keys(state.insertedLines).includes(pageNoStr)) {
        Vue.set(state.insertedLines, pageNoStr, []);
      }
    },
    EMPTY_SCRIPT(state: ScriptConfigState) {
      state.tmpScript = {};
    },
    SET_CUT_MODE(state: ScriptConfigState, cutMode: boolean) {
      state.cutMode = cutMode;
    },
  },
  actions: {
    REQUEST_EDIT_FAILURE(context) {
      VueToast.$toast.error('Unable to edit script');
      context.dispatch('GET_SCRIPT_CONFIG_STATUS');
      context.commit('SET_CUT_MODE', false);
    },
    async GET_SCRIPT_CONFIG_STATUS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/script/config')}`);
      if (response.ok) {
        const status = await response.json();
        context.commit('SET_EDIT_STATUS', status);
      } else {
        log.error('Unable to get script config status');
      }
    },
    ADD_BLANK_PAGE(context, pageNo: number) {
      const pageNoStr = pageNo.toString();
      const pageContents = JSON.parse(JSON.stringify(context.getters.GET_SCRIPT_PAGE(pageNoStr)));
      context.commit('ADD_PAGE', {
        pageNo,
        pageContents,
      });
    },
    RESET_TO_SAVED(context, pageNo: number) {
      context.commit('EMPTY_SCRIPT');
      context.dispatch('ADD_BLANK_PAGE', pageNo);
    },
    async SAVE_NEW_PAGE(context, pageNo: number) {
      const searchParams = new URLSearchParams({
        page: String(pageNo),
      });
      const response = await fetch(`${makeURL('/api/v1/show/script')}?${searchParams}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(context.getters.TMP_SCRIPT[pageNo.toString()]),
      });
      if (!response.ok) {
        log.error('Failed to save new script page');
        return false;
      }
      return true;
    },
    async SAVE_CHANGED_PAGE(context, pageNo: number) {
      const tmpScriptPage: ScriptLine[] = context.getters.TMP_SCRIPT[pageNo.toString()];
      const pageStatus = computePageStatus(
        context.getters.GET_SCRIPT_PAGE(pageNo),
        tmpScriptPage,
        context.getters.DELETED_LINES(pageNo),
        context.getters.INSERTED_LINES(pageNo)
      );
      const searchParams = new URLSearchParams({
        page: String(pageNo),
      });
      const response = await fetch(`${makeURL('/api/v1/show/script')}?${searchParams}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          page: context.getters.TMP_SCRIPT[pageNo.toString()],
          status: pageStatus,
        }),
      });
      if (!response.ok) {
        log.error('Failed to edit script page');
        return false;
      }
      return true;
    },
  },
  getters: {
    TMP_SCRIPT(state: ScriptConfigState) {
      return state.tmpScript;
    },
    DELETED_LINES: (state: ScriptConfigState) => (page: number | string) => {
      const pageStr = page.toString();
      if (Object.keys(state.deletedLines).includes(pageStr)) {
        return state.deletedLines[pageStr];
      }
      return [];
    },
    ALL_DELETED_LINES(state: ScriptConfigState) {
      return state.deletedLines;
    },
    CAN_REQUEST_EDIT(state: ScriptConfigState) {
      return state.editStatus.canRequestEdit;
    },
    CURRENT_EDITOR(state: ScriptConfigState) {
      return state.editStatus.currentEditor;
    },
    IS_CUT_MODE(state: ScriptConfigState) {
      return state.cutMode;
    },
    INSERTED_LINES: (state: ScriptConfigState) => (page: number | string) => {
      const pageStr = page.toString();
      if (Object.keys(state.insertedLines).includes(pageStr)) {
        return state.insertedLines[pageStr];
      }
      return [];
    },
  },
};

export default module;
