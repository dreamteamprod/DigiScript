import Vue from 'vue';
import { detailedDiff } from 'deep-object-diff';
import log from 'loglevel';

import { makeURL } from '@/js/utils';

export default {
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
    SET_EDIT_STATUS(state, editStatus) {
      state.editStatus = editStatus;
    },
    ADD_PAGE(state, { pageNo, pageContents }) {
      Vue.set(state.tmpScript, pageNo, pageContents);
    },
    REMOVE_PAGE(state, pageNo) {
      Vue.delete(state.tmpScript, pageNo);
    },
    ADD_BLANK_LINE(state, { pageNo, lineObj }) {
      const line = JSON.parse(JSON.stringify(lineObj));
      line.page = pageNo;
      state.tmpScript[pageNo].push(line);
    },
    INSERT_BLANK_LINE(state, { pageNo, lineIndex, lineObj }) {
      const pageNoStr = pageNo.toString();

      if (Object.keys(state.deletedLines).includes(pageNoStr)
          && state.deletedLines[pageNoStr].includes(lineIndex)) {
        const lineId = state.tmpScript[pageNoStr][lineIndex].id;
        const line = JSON.parse(JSON.stringify(lineObj));
        line.page = pageNo;
        line.id = lineId;
        state.tmpScript[pageNo].splice(lineIndex, 1, line);
        state.deletedLines[pageNoStr].splice(state.deletedLines[pageNoStr].indexOf(lineIndex), 1);
      } else {
        const line = JSON.parse(JSON.stringify(lineObj));
        line.page = pageNo;
        state.tmpScript[pageNo].splice(lineIndex, 0, line);
        if (!Object.keys(state.insertedLines).includes(pageNoStr)) {
          Vue.set(state.insertedLines, pageNoStr, []);
        }
        state.insertedLines[pageNoStr].push(lineIndex);
      }
    },
    SET_LINE(state, { pageNo, lineIndex, lineObj }) {
      Vue.set(state.tmpScript[pageNo], lineIndex, lineObj);
    },
    DELETE_LINE(state, { pageNo, lineIndex }) {
      const pageNoStr = pageNo.toString();
      if (state.tmpScript[pageNoStr][lineIndex].id !== null) {
        if (!Object.keys(state.deletedLines).includes(pageNoStr)) {
          Vue.set(state.deletedLines, pageNoStr, []);
        }
        state.deletedLines[pageNoStr].push(lineIndex);
      } else {
        state.tmpScript[pageNoStr].splice(lineIndex, 1);
      }
      if (Object.keys(state.insertedLines).includes(pageNoStr)
          && state.insertedLines[pageNoStr].includes(lineIndex)) {
        state.insertedLines[pageNoStr].splice(lineIndex, 1);
      }
    },
    RESET_DELETED(state, pageNo) {
      const pageNoStr = pageNo.toString();
      if (Object.keys(state.deletedLines).includes(pageNoStr)) {
        Vue.set(state.deletedLines, pageNoStr, []);
      }
    },
    RESET_INSERTED(state, pageNo) {
      const pageNoStr = pageNo.toString();
      if (Object.keys(state.insertedLines).includes(pageNoStr)) {
        Vue.set(state.insertedLines, pageNoStr, []);
      }
    },
    EMPTY_SCRIPT(state) {
      state.tmpScript = {};
    },
    SET_CUT_MODE(state, cutMode) {
      state.cutMode = cutMode;
    },
  },
  actions: {
    REQUEST_EDIT_FAILURE(context) {
      Vue.$toast.error('Unable to edit script');
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
    ADD_BLANK_PAGE(context, pageNo) {
      const pageNoStr = pageNo.toString();
      const pageContents = JSON.parse(JSON.stringify(context.getters.GET_SCRIPT_PAGE(pageNoStr)));
      context.commit('ADD_PAGE', {
        pageNo,
        pageContents,
      });
    },
    RESET_TO_SAVED(context, pageNo) {
      context.commit('EMPTY_SCRIPT');
      context.dispatch('ADD_BLANK_PAGE', pageNo);
    },
    async SAVE_NEW_PAGE(context, pageNo) {
      const searchParams = new URLSearchParams({
        page: pageNo,
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
    async SAVE_CHANGED_PAGE(context, pageNo) {
      let actualScriptPage = context.getters.GET_SCRIPT_PAGE(pageNo);
      const tmpScriptPage = context.getters.TMP_SCRIPT[pageNo.toString()];

      // Need to augment the actual script page to include the inserted pages, this is a hack,
      // but it will allow all the other pages to show as not edited if the really haven't been
      // changed
      actualScriptPage = JSON.parse(JSON.stringify(actualScriptPage));
      JSON.parse(JSON.stringify(context.getters.INSERTED_LINES(pageNo)))
        .sort((a, b) => a - b)
        .forEach((lineIndex) => {
          actualScriptPage.splice(
            lineIndex,
            0,
            JSON.parse(JSON.stringify(tmpScriptPage[lineIndex])),
          );
        });

      const deepDiff = detailedDiff(actualScriptPage, tmpScriptPage);
      const pageStatus = {
        added: Object.keys(deepDiff.added).map((x) => parseInt(x, 10)),
        updated: Object.keys(deepDiff.updated).map((x) => parseInt(x, 10)),
        deleted: [...context.getters.DELETED_LINES(pageNo)],
        inserted: [...context.getters.INSERTED_LINES(pageNo)],
      };
      const searchParams = new URLSearchParams({
        page: pageNo,
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
    TMP_SCRIPT(state) {
      return state.tmpScript;
    },
    DELETED_LINES: (state) => (page) => {
      const pageStr = page.toString();
      if (Object.keys(state.deletedLines).includes(pageStr)) {
        return state.deletedLines[pageStr];
      }
      return [];
    },
    ALL_DELETED_LINES(state) {
      return state.deletedLines;
    },
    CAN_REQUEST_EDIT(state) {
      return state.editStatus.canRequestEdit;
    },
    CURRENT_EDITOR(state) {
      return state.editStatus.currentEditor;
    },
    IS_CUT_MODE(state) {
      return state.cutMode;
    },
    INSERTED_LINES: (state) => (page) => {
      const pageStr = page.toString();
      if (Object.keys(state.insertedLines).includes(pageStr)) {
        return state.insertedLines[pageStr];
      }
      return [];
    },
  },
};
