import Vue from 'vue';

export default {
  state: {
    script: {},
  },
  mutations: {
    ADD_PAGE(state, { pageNo, pageContents }) {
      Vue.set(state.script, pageNo, pageContents);
    },
    REMOVE_PAGE(state, pageNo) {
      Vue.delete(state.script, pageNo);
    },
    ADD_BLANK_LINE(state, { pageNo, lineObj }) {
      const line = JSON.parse(JSON.stringify(lineObj));
      line.page = pageNo;
      if (state.script[pageNo].length > 0) {
        const previousLine = state.script[pageNo][state.script[pageNo].length - 1];
        if (previousLine != null) {
          line.act_id = previousLine.act_id;
          line.scene_id = previousLine.scene_id;
        }
      }
      state.script[pageNo].push(line);
    },
    SET_LINE(state, { pageNo, lineIndex, lineObj }) {
      Vue.set(state.script[pageNo], lineIndex, lineObj);
    },
  },
  actions: {
    ADD_BLANK_PAGE(context, pageNo) {
      const pageNoStr = pageNo.toString();
      const pageContents = context.getters.GET_SCRIPT_PAGE(pageNoStr);
      context.commit('ADD_PAGE', {
        pageNo,
        pageContents,
      });
    },
  },
  getters: {
    TMP_SCRIPT(state) {
      return state.script;
    },
  },
};
