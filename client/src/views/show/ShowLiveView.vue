<template>
  <b-container class="mx-0" fluid>
    <b-row class="session-header" style="padding-top: .1rem; padding-bottom: .1rem">
      <b-col cols="4" style="text-align: left">
        <b v-if="isScriptFollowing">
          {{ CURRENT_SHOW.name }} - Following
        </b>
        <b v-else-if="isScriptLeader">
          {{ CURRENT_SHOW.name }} - Leading
        </b>
        <b v-else>
          {{ CURRENT_SHOW.name }} - Manual
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
      <b-col id="script-container" cols="12" class="script-container" :data-following="isScriptFollowing"
        @scroll="computeScriptBoundaries" @scrollend="computeScriptBoundaries">
        <div v-if="!initialLoad" class="text-center center-spinner">
          <b-spinner style="width: 10rem; height: 10rem;" variant="info" />
        </div>
        <template v-else>
          <template v-for="page in pageIter">
            <script-line-viewer v-for="(line, index) in GET_SCRIPT_PAGE(page)" v-show="!isWholeLineCut(line)" v-once
              :id="`page_${page}_line_${index}`" :key="`page_${page}_line_${index}`" class="script-item"
              :line-index="index" :line="line" :acts="ACT_LIST" :scenes="SCENE_LIST" :characters="CHARACTER_LIST"
              :character-groups="CHARACTER_GROUP_LIST" :previous-line="getPreviousLineForIndex(page, index)"
              :previous-line-index="getPreviousLineIndex(page, index)" :cue-types="CUE_TYPES" :cues="getCuesForLine(line)"
              :cuts="SCRIPT_CUTS" @last-line-change="handleLastLineChange" @first-line-change="handleFirstLineChange" />
          </template>
          <b-row v-show="initialLoad" class="script-footer">
            <b-col>
              <b-button-group>
                <b-button variant="danger" :disabled="stoppingSession" @click.stop="stopShow">
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
      currentLoadedPage: 0,
      currentMaxPage: 0,
      stoppingSession: false,
      initialLoad: false,
      currentFirstPage: 1,
      currentLastPage: 1,
      pageBatchSize: 100,
      startTime: null,
      previousFirstPage: 1,
      previousLastPage: 1,
      assignedLastLine: false,
      currentLine: null,
      previousLine: null,
      currentMinLoadedPage: null,
      fullLoad: false,
      loadedSessionData: false,
    };
  },
  async mounted() {
    await this.GET_SHOW_SESSION_DATA();
    this.loadedSessionData = true;
    if (this.CURRENT_SHOW_SESSION == null) {
      this.$toast.warning('No live session started!');
      await this.$router.replace('/');
    } else {
      await this.GET_ACT_LIST();
      await this.GET_SCENE_LIST();
      await this.GET_CHARACTER_LIST();
      await this.GET_CHARACTER_GROUP_LIST();
      await this.GET_CUE_TYPES();
      await this.LOAD_CUES();
      await this.GET_CUTS();
      await this.getMaxScriptPage();

      this.updateElapsedTime();
      this.computeContentSize();

      this.startTime = this.createDateAsUTC(new Date(this.CURRENT_SHOW_SESSION.start_date_time.replace(' ', 'T')));
      this.elapsedTimer = setInterval(this.updateElapsedTime, 1000);
      window.addEventListener('resize', debounce(this.computeContentSize, 100));

      if (this.isScriptFollowing || this.isScriptLeader) {
        if (this.CURRENT_SHOW_SESSION.latest_line_ref != null) {
          const loadCurrentPage = parseInt(this.CURRENT_SHOW_SESSION.latest_line_ref.split('_')[1], 10);

          if (this.SETTINGS.enable_lazy_loading === false) {
            this.currentMinLoadedPage = 1;
            for (let loadIndex = 0; loadIndex < this.currentMaxPage; loadIndex++) {
              // eslint-disable-next-line no-await-in-loop
              await this.loadNextPage();
            }
          } else {
            this.currentMinLoadedPage = Math.max(0, loadCurrentPage - this.pageBatchSize - 1);
            this.currentLoadedPage = this.currentMinLoadedPage;
            for (let loadIndex = this.currentMinLoadedPage;
              loadIndex < loadCurrentPage + this.pageBatchSize; loadIndex++) {
              // eslint-disable-next-line no-await-in-loop
              await this.loadNextPage();
            }
            this.currentMinLoadedPage += 1;
          }

          this.currentFirstPage = loadCurrentPage;
          this.currentLastPage = loadCurrentPage;
          await this.$nextTick();
          this.initialLoad = true;
          await this.$nextTick();
          this.computeScriptBoundaries();
          document.getElementById(this.CURRENT_SHOW_SESSION.latest_line_ref).scrollIntoView({
            behavior: 'instant',
          });
          await this.$nextTick();
          this.computeScriptBoundaries();
        } else {
          this.currentMinLoadedPage = 1;
          if (this.SETTINGS.enable_lazy_loading === false) {
            for (let loadIndex = 0; loadIndex < this.currentMaxPage; loadIndex++) {
              // eslint-disable-next-line no-await-in-loop
              await this.loadNextPage();
            }
          } else {
            await this.loadNextPage();
          }
          this.initialLoad = true;
          await this.$nextTick();
          this.computeScriptBoundaries();
        }
      } else {
        this.currentMinLoadedPage = 1;
        if (this.SETTINGS.enable_lazy_loading === false) {
          for (let loadIndex = 0; loadIndex < this.currentMaxPage; loadIndex++) {
            // eslint-disable-next-line no-await-in-loop
            await this.loadNextPage();
          }
        } else {
          await this.loadNextPage();
        }
        this.initialLoad = true;
        await this.$nextTick();
        this.computeScriptBoundaries();
      }

      if (this.isScriptLeader) {
        const vueContext = this;
        document.addEventListener('keydown', (event) => {
          if (event.key === 'ArrowDown') {
            event.preventDefault();
            vueContext.nextLineHandler();
          }
          if (event.key === 'ArrowUp') {
            event.preventDefault();
            vueContext.prevLineHandler();
          }
        });
      }

      this.fullLoad = true;
    }
  },
  destroyed() {
    clearInterval(this.elapsedTimer);
  },
  methods: {
    msToTimer,
    createDateAsUTC(date) {
      return new Date(Date.UTC(
        date.getFullYear(),
        date.getMonth(),
        date.getDate(),
        date.getHours(),
        date.getMinutes(),
        date.getSeconds(),
      ));
    },
    updateElapsedTime() {
      if (this.startTime != null) {
        this.elapsedTime = Date.now() - this.startTime;
      }
    },
    computeScriptBoundaries() {
      const scriptContainer = $('#script-container');
      const cutoffTop = scriptContainer.offset().top;
      const cutoffBottom = scriptContainer.offset().top + scriptContainer.outerHeight();
      const scriptSelector = $('.script-item');

      scriptSelector.each(function () {
        if ($(this).offset().top >= cutoffTop) {
          if (!$(this).attr('class').split(/\s+/).includes('first-script-element')) {
            scriptSelector.removeClass('first-script-element');
            $(this).addClass('first-script-element');
          }
          return false;
        }
        return true;
      });

      let assignedLastScript = false;
      let lastObject = null;
      scriptSelector.each(function () {
        if (lastObject == null) {
          lastObject = this;
        } else if ($(this).offset().top > $(lastObject).offset().top
          && $(this).offset().top < cutoffBottom) {
          lastObject = this;
        }
        if ($(this).offset().top >= cutoffBottom) {
          if (!$(this).attr('class').split(/\s+/).includes('last-script-element')) {
            scriptSelector.removeClass('last-script-element');
            $(this).addClass('last-script-element');
          }
          assignedLastScript = true;
          return false;
        }
        return true;
      });
      this.assignedLastLine = assignedLastScript;
      if (!assignedLastScript) {
        scriptSelector.removeClass('last-script-element');
        $(lastObject).addClass('last-script-element');
      }
    },
    computeContentSize() {
      const scriptContainer = $('#script-container');
      const startPos = scriptContainer.offset().top;
      const boxHeight = document.documentElement.clientHeight - startPos;
      scriptContainer.height(boxHeight - 10);
      this.computeScriptBoundaries();
    },
    async loadNextPage() {
      if (this.currentLoadedPage < this.currentMaxPage) {
        this.currentLoadedPage += 1;
        await this.LOAD_SCRIPT_PAGE(this.currentLoadedPage);
      }
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
    async handleLastLineChange(lastPage, lineIndex) {
      this.previousLastPage = this.currentLastPage;
      this.currentLastPage = lastPage;
      const cutoffPage = this.currentLoadedPage - this.pageBatchSize;
      if (lastPage >= cutoffPage && this.currentLoadedPage < this.currentMaxPage) {
        for (let pageLoop = 0; pageLoop < this.pageBatchSize; pageLoop++) {
          // eslint-disable-next-line no-await-in-loop
          await this.loadNextPage();
        }
        this.computeScriptBoundaries();
        while (!this.assignedLastLine && this.currentLoadedPage <= this.currentMaxPage) {
          // eslint-disable-next-line no-await-in-loop
          await this.loadNextPage();
          this.computeScriptBoundaries();
          // eslint-disable-next-line no-await-in-loop
          await this.$nextTick();
        }
      }
      await this.$nextTick();
    },
    async handleFirstLineChange(firstPage, lineIndex, previousLine) {
      this.previousFirstPage = this.currentFirstPage;
      this.currentFirstPage = firstPage;
      this.previousLine = previousLine;
      this.currentLine = `page_${firstPage}_line_${lineIndex}`;

      const cutoffPage = firstPage - this.pageBatchSize;
      if (this.currentMinLoadedPage > cutoffPage) {
        for (let pageLoop = 0; pageLoop < this.pageBatchSize; pageLoop++) {
          if (this.currentMinLoadedPage > 1) {
            this.currentMinLoadedPage -= 1;
            // eslint-disable-next-line no-await-in-loop
            await this.LOAD_SCRIPT_PAGE(this.currentMinLoadedPage);
          }
        }
      }

      if (this.isScriptLeader && this.fullLoad) {
        $('.script-item').removeClass('current-line');
        $(`#${this.currentLine}`).addClass('current-line');
        console.log(this.currentLine)
        this.$socket.sendObj({
          OP: 'SCRIPT_SCROLL',
          DATA: {
            previous_line: this.previousLine,
            current_line: this.currentLine,
          },
        });
      }
    },
    prevLineHandler() {
      const scrollToLine = document.getElementById(this.previousLine);
      if (scrollToLine != null) {
        scrollToLine.scrollIntoView({
          behavior: 'instant',
        });
      }
    },
    nextLineHandler() {
      const nextLineSplit = this.currentLine.split("_");
      const nextLine = this.getNextLineForIndex(parseInt(nextLineSplit[1], 10), parseInt(nextLineSplit[3], 10));
      const scrollToLine = document.getElementById(`page_${nextLine[0]}_line_${nextLine[1]}`);
      if (scrollToLine != null) {
        scrollToLine.scrollIntoView({
          behavior: 'instant',
        });
      }
    },
    getNextLineForIndex(pageIndex, lineIndex) {
      if (lineIndex < this.GET_SCRIPT_PAGE(pageIndex).length - 1) {
        let loopLineIndex = lineIndex + 1;
        let loopLine = this.GET_SCRIPT_PAGE(pageIndex)[loopLineIndex];
        while (this.isWholeLineCut(loopLine)) {
          loopLineIndex += 1;
          if (loopLineIndex >= this.GET_SCRIPT_PAGE(pageIndex).length) {
            loopLine = null;
            break;
          }
          loopLine = this.GET_SCRIPT_PAGE(pageIndex)[loopLineIndex];
        }
        if (loopLine != null) {
          return [pageIndex, loopLineIndex];
        }
      }

      let loopPageNo = pageIndex + 1;
      while (loopPageNo <= this.currentMaxPage) {
        let loopPage = null;
        loopPage = this.GET_SCRIPT_PAGE(loopPageNo);
        if (loopPage.length > 0) {
          let loopLineIndex = 0;
          let loopLine = this.GET_SCRIPT_PAGE(loopPageNo)[loopLineIndex];
          while (this.isWholeLineCut(loopLine)) {
            loopLineIndex += 1;
            if (loopLineIndex >= this.GET_SCRIPT_PAGE(loopPageNo).length) {
              loopLine = null;
              break;
            }
            loopLine = this.GET_SCRIPT_PAGE(loopPageNo)[loopLineIndex];
          }
          if (loopLine != null) {
            return [loopPageNo, loopLineIndex];
          }
        }
        loopPageNo += 1;
      }
      return null;
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
    getPreviousLineIndex(pageIndex, lineIndex) {
      if (lineIndex > 0) {
        return lineIndex - 1;
      }
      let loopPageNo = pageIndex - 1;
      while (loopPageNo >= 1) {
        let loopPage = null;
        loopPage = this.GET_SCRIPT_PAGE(loopPageNo);
        if (loopPage.length > 0) {
          return loopPage.length - 1;
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
    isWholeLineCut(line) {
      return line.line_parts.every((linePart) => (this.SCRIPT_CUTS.includes(linePart.id)), this);
    },
    ...mapActions(['GET_SHOW_SESSION_DATA', 'LOAD_SCRIPT_PAGE', 'GET_ACT_LIST', 'GET_SCENE_LIST',
      'GET_CHARACTER_LIST', 'GET_CHARACTER_GROUP_LIST', 'LOAD_CUES', 'GET_CUE_TYPES',
      'GET_CUTS']),
  },
  computed: {
    pageIter() {
      if (this.SETTINGS.enable_live_batching) {
        return [...Array(this.currentLoadedPage).keys()].map((x) => (x + 1)).filter((x) => (
          x <= this.currentLastPage + this.pageBatchSize
            && x >= this.currentFirstPage - this.pageBatchSize));
      }
      return [...Array(this.currentMaxPage).keys()];
    },
    isScriptFollowing() {
      if (this.loadedSessionData) {
        return this.CURRENT_SHOW_SESSION.client_internal_id != null && !this.isScriptLeader;
      }
      return false;
    },
    isScriptLeader() {
      if (this.loadedSessionData) {
        return this.CURRENT_SHOW_SESSION.client_internal_id === this.INTERNAL_UUID;
      }
      return false;
    },
    ...mapGetters(['CURRENT_SHOW_SESSION', 'GET_SCRIPT_PAGE', 'ACT_LIST', 'SCENE_LIST',
      'CHARACTER_LIST', 'CHARACTER_GROUP_LIST', 'CURRENT_SHOW', 'CUE_TYPES', 'SCRIPT_CUES',
      'INTERNAL_UUID', 'SESSION_FOLLOW_DATA', 'SCRIPT_CUTS', 'SETTINGS']),
  },
  watch: {
    SESSION_FOLLOW_DATA() {
      if (this.isScriptFollowing) {
        let scrollToLine;
        if (this.SESSION_FOLLOW_DATA.previous_line != null) {
          scrollToLine = document.getElementById(this.SESSION_FOLLOW_DATA.previous_line);
        } else {
          scrollToLine = document.getElementById(this.SESSION_FOLLOW_DATA.current_line);
        }
        if (scrollToLine != null) {
          $('.script-item').removeClass('current-line');
          $(`#${this.SESSION_FOLLOW_DATA.current_line}`).addClass('current-line');
          scrollToLine.scrollIntoView({
            behavior: 'smooth',
          });
        }
      }
    },
  },
};
</script>

<style scoped>
.script-container {
  overflow: scroll;
  overflow-x: auto;
  width: 100vw;
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.script-container::-webkit-scrollbar {
  display: none;
  width: 0 !important
}

.script-container[data-following="true"] {
  overflow: hidden !important;
}

.session-header {
  border-bottom: .1rem solid #3498db;
}

.script-footer {
  border-top: .1rem solid #3498db;
  padding-top: .5rem;
  padding-bottom: .1rem;
}

.current-line {
  background: #3498db54;
}
</style>
