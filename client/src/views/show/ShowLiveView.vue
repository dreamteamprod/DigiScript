<template>
  <b-container class="mx-0" fluid>
    <b-row class="session-header" style="padding-top: .1rem; padding-bottom: .1rem">
      <b-col cols="4" style="text-align: left">
        <b>
          {{ CURRENT_SHOW.name }}
        </b>
      </b-col>
      <b-col cols="4">
        <b>
          Page {{ currentFirstPage }}
        </b>
      </b-col>
      <b-col cols="4" style="text-align: right">
        <b>
          Elapsed Time: {{ msToTimer(elapsedTime) }}
        </b>
      </b-col>
    </b-row>
    <b-row>
      <b-col cols="12" class="script-container" id="script-container">
        <div class="text-center center-spinner" v-if="!initialLoad">
          <b-spinner style="width: 10rem; height: 10rem;" variant="info" />
        </div>
        <template v-else>
          <template v-for="page in currentLoadedPage">
            <script-line-viewer v-for="(line, index) in GET_SCRIPT_PAGE(page)"
                                v-show="page >= currentFirstPage - 1"
                                class="script-item"
                                :key="`page_${page}_line_${index}`"
                                :line-index="index" :line="line" :acts="ACT_LIST"
                                :scenes="SCENE_LIST" :characters="CHARACTER_LIST"
                                :character-groups="CHARACTER_GROUP_LIST"
                                :previous-line="getPreviousLineForIndex(page, index)"
                                :cue-types="CUE_TYPES"
                                :cues="getCuesForLine(line)"
                                @last-line-page="handleLastPageChange"
                                @first-page="handleFirstPageChange" />
          </template>
          <b-row v-show="initialLoad" class="script-footer">
            <b-col>
              <b-button-group>
                <b-button @click.stop="stopShow" variant="danger" :disabled="stoppingSession">
                  End Show
                </b-button>
              </b-button-group>
            </b-col>
          </b-row>
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
      stoppingSession: false,
      initialLoad: false,
      currentFirstPage: 0,
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
      await this.GET_CUE_TYPES();
      await this.LOAD_CUES();
      await this.getMaxScriptPage();

      this.updateElapsedTime();
      this.computeContentSize();
      this.computeScriptBoundaries();

      this.elapsedTimer = setInterval(this.updateElapsedTime, 1000);
      this.scrollTimer = setInterval(this.computeScriptBoundaries, 25);
      window.addEventListener('resize', debounce(this.computeContentSize, 100));

      await this.loadNextPage();
      this.initialLoad = true;
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
      if ((this.currentLoadedPage === lastPage || this.currentLoadedPage - 2 === lastPage)
        && this.currentLoadedPage - 2 < this.currentMaxPage) {
        await this.loadNextPage();
        await this.loadNextPage();
      }
    },
    handleFirstPageChange(firstPage) {
      this.currentFirstPage = firstPage;
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
    async stopShow() {
      this.stoppingSession = true;
      const response = await fetch(`${makeURL('/api/v1/show/sessions/stop')}`, {
        method: 'POST',
      });
      if (response.ok) {
        this.$toast.success('Stopped show session');
      } else {
        log.error('Unable to stop show session');
        this.$toast.error('Unable to stop show session');
      }
      this.stoppingSession = false;
    },
    getCuesForLine(line) {
      if (Object.keys(this.SCRIPT_CUES).includes(line.id.toString())) {
        return this.SCRIPT_CUES[line.id.toString()];
      }
      return [];
    },
    ...mapActions(['GET_SHOW_SESSION_DATA', 'LOAD_SCRIPT_PAGE', 'GET_ACT_LIST', 'GET_SCENE_LIST',
      'GET_CHARACTER_LIST', 'GET_CHARACTER_GROUP_LIST', 'LOAD_CUES', 'GET_CUE_TYPES']),
  },
  computed: {
    ...mapGetters(['CURRENT_SHOW_SESSION', 'GET_SCRIPT_PAGE', 'ACT_LIST', 'SCENE_LIST',
      'CHARACTER_LIST', 'CHARACTER_GROUP_LIST', 'CURRENT_SHOW', 'CUE_TYPES', 'SCRIPT_CUES']),
  },
};
</script>

<style scoped>
  .script-container {
    overflow: scroll;
    width: 100vw;
  }

  .session-header {
    border-bottom: .1rem solid #3498db;
  }

  .script-footer {
    border-top: .1rem solid #3498db;
    padding-top: .5rem;
    padding-bottom: .1rem;
  }
</style>
