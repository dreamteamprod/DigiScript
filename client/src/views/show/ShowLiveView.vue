<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <p>
          Elapsed Time: {{ msToTimer(elapsedTime) }}
        </p>
      </b-col>
    </b-row>
    <b-row>
      <b-col cols="12" class="script-container" id="script-container">
        <template v-for="page in currentLoadedPage">
          <script-line-viewer v-for="(line, index) in GET_SCRIPT_PAGE(page)"
                              class="script-item"
                              :key="`page_${page}_line_${index}`"
                              :line-index="index" :line="line" :acts="ACT_LIST" :scenes="SCENE_LIST"
                              :characters="CHARACTER_LIST" :character-groups="CHARACTER_GROUP_LIST"
                              :previous-line="getPreviousLineForIndex(page, index)"
                              @last-line-page="handleLastPageChange" />
        </template>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import $ from 'jquery';
import { debounce } from 'lodash';
import log from 'loglevel';

import { makeURL, msToTimer } from '@/js/utils';
import ScriptLineViewer from '@/vue_components/show/live/ScriptLineViewer.vue';

export default {
  name: 'ShowLiveView',
  components: {
    ScriptLineViewer,
  },
  data() {
    return {
      elapsedTime: 0,
      elapsedTimer: null,
      scrollTimer: null,
      currentLoadedPage: 0,
      currentMaxPage: 0,
    };
  },
  async mounted() {
    await this.GET_SHOW_SESSION_DATA();
    if (this.CURRENT_SHOW_SESSION == null) {
      this.$toast.warning('No live session started!');
      this.$router.replace('/');
    } else {
      await this.GET_ACT_LIST();
      await this.GET_SCENE_LIST();
      await this.GET_CHARACTER_LIST();
      await this.GET_CHARACTER_GROUP_LIST();
      await this.getMaxScriptPage();

      this.updateElapsedTime();
      this.computeContentSize();
      this.computeScriptBoundaries();

      this.elapsedTimer = setInterval(this.updateElapsedTime, 1000);
      this.scrollTimer = setInterval(this.computeScriptBoundaries, 50);
      window.addEventListener('resize', debounce(this.computeContentSize, 100));

      await this.loadNextPage();
    }
  },
  destroyed() {
    clearInterval(this.elapsedTimer);
    clearInterval(this.scrollTimer);
  },
  methods: {
    msToTimer,
    updateElapsedTime() {
      const now = new Date().getTime();
      const startTime = Date.parse(this.CURRENT_SHOW_SESSION.start_date_time);
      this.elapsedTime = now - startTime;
    },
    computeScriptBoundaries() {
      const scriptContainer = $('#script-container');
      const cutoffTop = scriptContainer.offset().top;
      const cutoffBottom = scriptContainer.offset().top + scriptContainer.height();
      const scriptSelector = $('.script-item');

      scriptSelector.each(function () {
        if ($(this).offset().top + $(this).height() > cutoffTop) {
          if (!$(this).attr('class').split(/\s+/).includes('first-script-element')) {
            $('.script-item').removeClass('first-script-element');
            $(this).addClass('first-script-element');
          }
          return false;
        }
        return true;
      });

      scriptSelector.each(function () {
        if ($(this).offset().top >= cutoffBottom) {
          if (!$(this).attr('class').split(/\s+/).includes('last-script-element')) {
            $('.script-item').removeClass('last-script-element');
            $(this).addClass('last-script-element');
          }
          return false;
        }
        return true;
      });
    },
    computeContentSize() {
      const scriptContainer = $('#script-container');
      const startPos = scriptContainer.offset().top;
      const boxHeight = document.documentElement.clientHeight - startPos;
      scriptContainer.height(boxHeight - 10);
    },
    async loadNextPage() {
      this.currentLoadedPage += 1;
      await this.LOAD_SCRIPT_PAGE(this.currentLoadedPage);
      console.log(`Loading page ${this.currentLoadedPage}`);
    },
    async getMaxScriptPage() {
      const response = await fetch(`${makeURL('/api/v1/show/script/max_page')}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const respJson = await response.json();
        this.currentMaxPage = respJson.max_page;
      } else {
        log.error('Unable to get current max page');
      }
    },
    async handleLastPageChange(lastPage) {
      if ((this.currentLoadedPage === lastPage || this.currentLoadedPage - 1 === lastPage)
        && this.currentLoadedPage < this.currentMaxPage) {
        await this.loadNextPage();
      }
    },
    getPreviousLineForIndex(pageIndex, lineIndex) {
      if (lineIndex > 0) {
        return this.GET_SCRIPT_PAGE(pageIndex)[lineIndex - 1];
      }
      let loopPageNo = pageIndex - 1;
      while (loopPageNo >= 1) {
        let loopPage = null;
        loopPage = this.GET_SCRIPT_PAGE(loopPageNo);
        if (loopPage.length > 0) {
          return loopPage[loopPage.length - 1];
        }
        loopPageNo -= 1;
      }
      return null;
    },
    ...mapActions(['GET_SHOW_SESSION_DATA', 'LOAD_SCRIPT_PAGE', 'GET_ACT_LIST', 'GET_SCENE_LIST',
      'GET_CHARACTER_LIST', 'GET_CHARACTER_GROUP_LIST']),
  },
  computed: {
    ...mapGetters(['CURRENT_SHOW_SESSION', 'GET_SCRIPT_PAGE', 'ACT_LIST', 'SCENE_LIST',
      'CHARACTER_LIST', 'CHARACTER_GROUP_LIST']),
  },
};
</script>

<style scoped>
  .script-container {
    overflow: scroll;
    width: 100vw;
  }
</style>
