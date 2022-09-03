import Vue from 'vue';
import { makeURL } from '@/js/utils';

export default {
  state: {
    tmpScript: {},
    editStatus: {
      canRequestEdit: false,
      currentEditor: null,
    },
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
      if (state.tmpScript[pageNo].length > 0) {
        const previousLine = state.tmpScript[pageNo][state.tmpScript[pageNo].length - 1];
        if (previousLine != null) {
          line.act_id = previousLine.act_id;
          line.scene_id = previousLine.scene_id;
        }
      }
      state.tmpScript[pageNo].push(line);
    },
    SET_LINE(state, { pageNo, lineIndex, lineObj }) {
      Vue.set(state.tmpScript[pageNo], lineIndex, lineObj);
    },
  },
  actions: {
    REQUEST_EDIT_FAILURE(context) {
      Vue.$toast.error('Unable to edit script');
    },
    async GET_SCRIPT_CONFIG_STATUS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/script/config')}`);
      if (response.ok) {
        const status = await response.json();
        context.commit('SET_EDIT_STATUS', status);
      } else {
        console.error('Unable to get script config status');
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
  },
  getters: {
    TMP_SCRIPT(state) {
      return state.tmpScript;
    },
    CAN_REQUEST_EDIT(state) {
      return state.editStatus.canRequestEdit;
    },
    CURRENT_EDITOR(state) {
      return state.editStatus.currentEditor;
    },
  },
};
