<template>
  <b-row
    ref="script-container"
    :aria-hidden="intervalActive ? 'true' : null"
    :style="{ 'margin-right': stageManagerMode ? '0px' : '-15px' }"
  >
    <b-col
      id="script-container"
      cols="12"
      class="script-container"
      :data-following="isScriptFollowing"
    >
      <div v-if="!initialLoad" class="text-center center-spinner">
        <b-spinner style="width: 10rem; height: 10rem" variant="info" />
      </div>
      <template v-else>
        <template v-if="scriptMode === 2">
          <template v-for="page in pageIter">
            <script-line-viewer-compact
              v-for="(line, index) in GET_SCRIPT_PAGE(page)"
              v-show="!isWholeLineCut(line) && line.line_type !== LINE_TYPES.SPACING"
              v-once
              :id="`page_${page}_line_${index}`"
              :key="`page_${page}_line_${index}_ADDMODE:${cueAddMode}_CUES:${SCRIPT_CUES[line.id.toString()]?.length || 0}`"
              class="script-item"
              :line-index="index"
              :line="line"
              :acts="ACT_LIST"
              :scenes="SCENE_LIST"
              :characters="CHARACTER_LIST"
              :character-groups="CHARACTER_GROUP_LIST"
              :previous-line="getPreviousLineForIndex(page, index)"
              :previous-line-index="getPreviousLineIndex(page, index)"
              :cue-types="CUE_TYPES"
              :cues="getCuesForLine(line)"
              :cuts="SCRIPT_CUTS"
              :stage-direction-styles="STAGE_DIRECTION_STYLES"
              :stage-direction-style-overrides="STAGE_DIRECTION_STYLE_OVERRIDES"
              :is-script-leader="isScriptLeader"
              :cue-add-mode="cueAddMode"
              :spacing-before="getSpacingBefore(page, index)"
              @last-line-change="handleLastLineChange"
              @first-line-change="handleFirstLineChange"
              @start-interval="configureInterval"
              @add-cue="openNewCueModal"
            />
          </template>
        </template>
        <template v-else>
          <template v-for="page in pageIter">
            <script-line-viewer
              v-for="(line, index) in GET_SCRIPT_PAGE(page)"
              v-show="!isWholeLineCut(line) && line.line_type !== LINE_TYPES.SPACING"
              v-once
              :id="`page_${page}_line_${index}`"
              :key="`page_${page}_line_${index}_ADDMODE:${cueAddMode}_CUES:${SCRIPT_CUES[line.id.toString()]?.length || 0}`"
              class="script-item"
              :line-index="index"
              :line="line"
              :acts="ACT_LIST"
              :scenes="SCENE_LIST"
              :characters="CHARACTER_LIST"
              :character-groups="CHARACTER_GROUP_LIST"
              :previous-line="getPreviousLineForIndex(page, index)"
              :previous-line-index="getPreviousLineIndex(page, index)"
              :cue-types="CUE_TYPES"
              :cues="getCuesForLine(line)"
              :cuts="SCRIPT_CUTS"
              :stage-direction-styles="STAGE_DIRECTION_STYLES"
              :stage-direction-style-overrides="STAGE_DIRECTION_STYLE_OVERRIDES"
              :is-script-leader="isScriptLeader"
              :cue-add-mode="cueAddMode"
              :spacing-before="getSpacingBefore(page, index)"
              @last-line-change="handleLastLineChange"
              @first-line-change="handleFirstLineChange"
              @start-interval="configureInterval"
              @add-cue="openNewCueModal"
            />
          </template>
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
    <b-modal
      id="start-interval-modal"
      ref="start-interval-modal"
      title="Start Interval"
      size="md"
      :ok-disabled="intervalTimerLength === 0"
      ok-title="Start"
      :ok-only="true"
      ok-variant="success"
      @show="resetIntervalState"
      @hidden="resetIntervalState"
      @ok="startInterval"
    >
      <b-container class="mx-0" fluid>
        <b-row align-h="center">
          <b-col md="auto">
            <b-time
              id="interval-time-selector"
              v-model="intervalTimerValue"
              :hour12="false"
              :show-seconds="true"
              :hide-header="true"
              label-increment="+"
              label-decrement="-"
              @context="onIntervalTimerContext"
            />
          </b-col>
        </b-row>
        <b-row align-h="center">
          <b-col md="auto">
            <b-alert show variant="info"> Select the length of the interval (HH:MM:SS) </b-alert>
          </b-col>
        </b-row>
      </b-container>
    </b-modal>
    <b-modal
      :id="`new-cue-modal`"
      title="Add New Cue"
      size="md"
      :ok-disabled="$v.newCueFormState.$invalid || submittingNewCue"
      @hidden="resetNewCueForm"
      @ok="onSubmitNewCue"
    >
      <b-form ref="new-cue-form" @submit.stop.prevent="onSubmitNewCue">
        <b-form-group id="type-input-group" label="Cue Type" label-for="type-input">
          <b-form-select
            id="type-input"
            v-model="$v.newCueFormState.cueType.$model"
            :options="cueTypeOptions"
            :state="validateNewCueState('cueType')"
            aria-describedby="cue-type-feedback"
          />
          <b-form-invalid-feedback id="cue-type-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="ident-input-group" label="Identifier" label-for="ident-input">
          <b-form-input
            id="ident-input"
            v-model="$v.newCueFormState.ident.$model"
            name="ident-input"
            :state="validateNewCueState('ident')"
            aria-describedby="ident-feedback"
          />
          <b-form-invalid-feedback id="ident-feedback">
            This is a required field.
          </b-form-invalid-feedback>
          <b-form-text v-if="isDuplicateCue" class="text-warning">
            A cue with this identifier already exists for this cue type
          </b-form-text>
        </b-form-group>
      </b-form>
    </b-modal>
  </b-row>
</template>

<script>
import { required } from 'vuelidate/lib/validators';
import { mapGetters, mapActions, mapMutations } from 'vuex';
import $ from 'jquery';
import { debounce } from 'lodash';
import log from 'loglevel';

import { makeURL } from '@/js/utils';
import ScriptLineViewer from '@/vue_components/show/live/ScriptLineViewer.vue';
import ScriptLineViewerCompact from '@/vue_components/show/live/ScriptLineViewerCompact.vue';
import { LINE_TYPES } from '@/constants/lineTypes';
import { isWholeLineCut as isWholeLineCutUtil } from '@/js/scriptUtils';

export default {
  name: 'ScriptViewPane',
  components: {
    ScriptLineViewer,
    ScriptLineViewerCompact,
  },
  props: {
    isScriptFollowing: {
      type: Boolean,
      required: true,
    },
    isScriptLeader: {
      type: Boolean,
      required: true,
    },
    sessionFollowData: {
      type: Object,
      required: true,
    },
    initialLineRef: {
      type: String,
      default: null,
    },
    intervalActive: {
      type: Boolean,
      required: true,
    },
    scriptMode: {
      type: Number,
      required: true,
    },
    stageManagerMode: {
      type: Boolean,
      required: true,
    },
  },
  data() {
    return {
      LINE_TYPES,
      // Page loading state
      currentLoadedPage: 0,
      currentMaxPage: 0,
      currentFirstPage: 1,
      currentLastPage: 1,
      currentMinLoadedPage: null,
      pageBatchSize: 3,
      previousFirstPage: 1,
      previousLastPage: 1,

      // Script load state
      initialLoad: false,
      fullLoad: false,
      assignedLastLine: false,

      // Navigation state
      currentPage: 1,
      currentLineOnPage: 0,
      currentLine: null,
      previousLine: null,
      isScrollingProgrammatically: false,

      // UI state
      cueAddMode: false,
      debounceContentSize: debounce(this.computeContentSize, 100),

      // Cue modal state
      newCueFormState: {
        cueType: null,
        ident: null,
        lineId: null,
      },
      submittingNewCue: false,

      // Interval modal state
      intervalActId: null,
      intervalTimerValue: '00:00:00',
      intervalTimerContext: null,

      // Session control
      stoppingSession: false,
    };
  },
  validations: {
    newCueFormState: {
      cueType: {
        required,
      },
      ident: {
        required,
      },
      lineId: {
        required,
      },
    },
  },
  computed: {
    pageIter() {
      return [...Array(this.currentMaxPage).keys()].map((i) => i + 1);
    },
    intervalTimerLength() {
      if (this.intervalTimerContext == null) {
        return 0;
      }
      return (
        this.intervalTimerContext.hours * 60 * 60 +
        this.intervalTimerContext.minutes * 60 +
        this.intervalTimerContext.seconds
      );
    },
    cueTypeOptions() {
      return [
        { value: null, text: 'N/A' },
        ...this.CUE_TYPES.map((cueType) => ({
          value: cueType.id,
          text: `${cueType.prefix}: ${cueType.description}`,
        })),
      ];
    },
    totalCueCount() {
      let count = 0;
      Object.keys(this.SCRIPT_CUES).forEach((line) => {
        count += this.SCRIPT_CUES[line].length;
      }, this);
      return count;
    },
    flatScriptCues() {
      return Object.keys(this.SCRIPT_CUES)
        .map((key) => this.SCRIPT_CUES[key])
        .flat();
    },
    isDuplicateCue() {
      if (!this.newCueFormState.ident || !this.newCueFormState.cueType) {
        return false;
      }
      return this.flatScriptCues.some(
        (cue) =>
          cue.cue_type_id === this.newCueFormState.cueType &&
          cue.ident === this.newCueFormState.ident
      );
    },
    ...mapGetters([
      'GET_SCRIPT_PAGE',
      'ACT_LIST',
      'SCENE_LIST',
      'CHARACTER_LIST',
      'CHARACTER_GROUP_LIST',
      'CURRENT_SHOW',
      'CUE_TYPES',
      'SCRIPT_CUES',
      'SCRIPT_CUTS',
      'STAGE_DIRECTION_STYLES',
      'STAGE_DIRECTION_STYLE_OVERRIDES',
      'IS_SHOW_EDITOR',
      'CURRENT_USER',
    ]),
  },
  watch: {
    sessionFollowData() {
      if (this.isScriptFollowing && this.sessionFollowData.current_line) {
        const currentLineElement = document.getElementById(this.sessionFollowData.current_line);
        if (currentLineElement != null) {
          const idParts = this.sessionFollowData.current_line.split('_');
          const page = parseInt(idParts[1], 10);
          const line = parseInt(idParts[3], 10);

          $('.script-item').removeClass('current-line');
          $(currentLineElement).addClass('current-line');

          const contextLines = 3;
          const contextElement = this.findContextElement(page, line, contextLines);

          if (contextElement) {
            this.scrollToElement(contextElement);
          } else {
            this.scrollToElement(currentLineElement);
          }
          this.currentPage = page;
          this.$emit('page-change', page);
          this.computeScriptBoundaries();
        }
      }
    },
    totalCueCount() {
      this.$nextTick(() => {
        if (this.initialLoad) {
          this.resumeNavigation();
        }
      });
    },
  },
  async mounted() {
    // Load all independent data in parallel
    await Promise.all([
      // User data (style overrides loaded after user resolves)
      this.GET_CURRENT_USER().then(() => {
        if (this.CURRENT_USER != null) {
          return Promise.all([
            this.GET_STAGE_DIRECTION_STYLE_OVERRIDES(),
            this.GET_CUE_COLOUR_OVERRIDES(),
          ]);
        }
        return Promise.resolve();
      }),
      // Show metadata
      this.GET_SCENE_LIST(),
      this.GET_CHARACTER_LIST(),
      this.GET_CHARACTER_GROUP_LIST(),
      this.GET_CUE_TYPES(),
      this.LOAD_CUES(),
      this.GET_CUTS(),
      this.GET_STAGE_DIRECTION_STYLES(),
      // Script page count
      this.getMaxScriptPage(),
    ]);

    this.computeContentSize();

    const loadedCompiledScript = await this.loadCompiledScript();

    if (this.isScriptFollowing || this.isScriptLeader) {
      if (this.initialLineRef != null) {
        const loadCurrentPage = parseInt(this.initialLineRef.split('_')[1], 10);

        if (!loadedCompiledScript) {
          this.currentMinLoadedPage = 1;
          for (let loadIndex = 0; loadIndex < this.currentMaxPage; loadIndex++) {
            await this.loadNextPage();
          }
          this.currentFirstPage = loadCurrentPage;
          this.currentLastPage = loadCurrentPage;
        }

        await this.$nextTick();
        this.initialLoad = true;
        await this.$nextTick();
        this.computeScriptBoundaries();
        this.scrollToElement(document.getElementById(this.initialLineRef));
        await this.$nextTick();
        this.computeScriptBoundaries();
      } else {
        if (!loadedCompiledScript) {
          this.currentMinLoadedPage = 1;
          for (let loadIndex = 0; loadIndex < this.currentMaxPage; loadIndex++) {
            await this.loadNextPage();
          }
        }
        this.initialLoad = true;
        await this.$nextTick();
        this.computeScriptBoundaries();
      }
    } else {
      if (!loadedCompiledScript) {
        this.currentMinLoadedPage = 1;
        for (let loadIndex = 0; loadIndex < this.currentMaxPage; loadIndex++) {
          await this.loadNextPage();
        }
      }
      this.initialLoad = true;
      await this.$nextTick();
      this.computeScriptBoundaries();
    }

    this.fullLoad = true;
    this.setupNavigation();
    this.$nextTick(() => {
      if (this.initialLoad) {
        this.initializeNavigation();
      }
    });

    window.addEventListener('resize', this.debounceContentSize);
    this.$emit('script-loaded');
  },
  destroyed() {
    this.removeNavigation();
    window.removeEventListener('resize', this.debounceContentSize);
  },
  methods: {
    // Navigation setup/teardown
    setupNavigation() {
      window.addEventListener('keydown', this.handleKeyPress);
      const scriptContainer = document.getElementById('script-container');
      if (scriptContainer) {
        scriptContainer.addEventListener('wheel', this.handleWheelNavigation, { passive: false });
      }
    },
    removeNavigation() {
      window.removeEventListener('keydown', this.handleKeyPress);
      const scriptContainer = document.getElementById('script-container');
      if (scriptContainer) {
        scriptContainer.removeEventListener('wheel', this.handleWheelNavigation);
      }
    },

    // Navigation execution
    navigateTo(targetPage, targetLineOnPage, preventScroll = false) {
      if (targetPage > Number(this.currentLoadedPage)) {
        return false;
      }

      const pageLines = this.GET_SCRIPT_PAGE(targetPage);
      if (!pageLines || targetLineOnPage >= pageLines.length) {
        return false;
      }

      this.currentPage = targetPage;
      this.currentLineOnPage = targetLineOnPage;
      this.$emit('page-change', targetPage);

      const targetElementId = `page_${targetPage}_line_${targetLineOnPage}`;
      const targetElement = document.getElementById(targetElementId);

      if (!targetElement) {
        log.error(`Could not find element for line: ${targetElementId}`);
        return false;
      }

      $('.script-item').removeClass('current-line');
      $(targetElement).addClass('current-line');

      this.previousLine = this.currentLine;
      this.currentLine = targetElementId;

      if (!preventScroll) {
        this.isScrollingProgrammatically = true;
        const contextLines = 3;
        const contextElement = this.findContextElement(targetPage, targetLineOnPage, contextLines);

        if (contextElement) {
          this.scrollToElement(contextElement);
        } else {
          this.scrollToElement(targetElement);
        }

        if (this.fullLoad) {
          this.$socket.sendObj({
            OP: 'SCRIPT_SCROLL',
            DATA: {
              previous_line: this.previousLine,
              current_line: this.currentLine,
            },
          });
        }

        setTimeout(() => {
          this.isScrollingProgrammatically = false;
          this.computeScriptBoundaries();
        }, 50);
      }

      return true;
    },
    findContextElement(targetPage, targetLineOnPage, contextLines) {
      let currentPage = targetPage;
      let currentLine = targetLineOnPage;
      let visibleLinesFound = 0;

      while (visibleLinesFound < contextLines && currentPage >= 1) {
        currentLine--;

        if (currentLine < 0) {
          currentPage--;
          if (currentPage < 1) {
            return document.getElementById('page_1_line_0');
          }

          const prevPageLines = this.GET_SCRIPT_PAGE(currentPage);
          if (!prevPageLines || prevPageLines.length === 0) {
            continue;
          }

          currentLine = prevPageLines.length - 1;
        }

        const pageLines = this.GET_SCRIPT_PAGE(currentPage);
        if (pageLines && currentLine < pageLines.length) {
          const line = pageLines[currentLine];
          if (!this.isWholeLineCut(line)) {
            visibleLinesFound++;

            if (visibleLinesFound >= contextLines) {
              return document.getElementById(`page_${currentPage}_line_${currentLine}`);
            }
          }
        }
      }

      if (visibleLinesFound > 0) {
        return document.getElementById(`page_${currentPage}_line_${currentLine}`);
      }

      return null;
    },
    navigateRelative(deltaPage, deltaLine) {
      if (deltaLine === 0 && deltaPage === 0) return true;

      const direction = deltaLine > 0 ? 1 : -1;

      let newPage = this.currentPage;
      let newLineOnPage = this.currentLineOnPage;

      let visibleLinesMoved = 0;

      while (visibleLinesMoved < Math.abs(deltaLine)) {
        newLineOnPage += direction;

        if (newLineOnPage < 0) {
          newPage--;
          if (newPage < 1) {
            newPage = 1;
            newLineOnPage = 0;
            break;
          } else {
            const prevPageLines = this.GET_SCRIPT_PAGE(newPage);
            if (!prevPageLines) break;
            newLineOnPage = prevPageLines.length - 1;
            if (newLineOnPage < 0) newLineOnPage = 0;
          }
        } else {
          const currentPageLines = this.GET_SCRIPT_PAGE(newPage);
          if (!currentPageLines) break;
          if (newLineOnPage >= currentPageLines.length) {
            newPage++;
            if (newPage > this.currentLoadedPage) {
              newPage = this.currentLoadedPage;
              newLineOnPage = currentPageLines.length - 1;
              break;
            } else {
              newLineOnPage = 0;
            }
          }
        }

        const pageLines = this.GET_SCRIPT_PAGE(newPage);
        if (pageLines && newLineOnPage < pageLines.length) {
          const currentLine = pageLines[newLineOnPage];
          if (!this.isWholeLineCut(currentLine)) {
            visibleLinesMoved++;
          }
          if (visibleLinesMoved >= Math.abs(deltaLine)) {
            break;
          }
        } else {
          break;
        }
      }

      return this.navigateTo(newPage, newLineOnPage);
    },

    // Input handlers
    handleKeyPress(event) {
      if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
        this.handleKeyNavigation(event);
      } else if (event.key === 'PageUp' || event.key === 'PageDown') {
        this.handlePageNavigation(event);
      } else if (event.key === 'C') {
        this.handleCueEditToggle(event);
      }
    },
    handleCueEditToggle(event) {
      event.preventDefault();
      if (this.IS_SHOW_EDITOR) {
        this.cueAddMode = !this.cueAddMode;
        this.$nextTick(() => {
          if (this.initialLoad) {
            this.resumeNavigation();
          }
        });
      } else {
        this.cueAddMode = false;
      }
    },
    handleKeyNavigation(event) {
      if (
        !this.isScriptLeader ||
        !this.initialLoad ||
        this.isScrollingProgrammatically ||
        this.intervalTimerContext != null ||
        this.intervalActive
      )
        return;

      event.preventDefault();

      const delta = event.key === 'ArrowDown' ? 1 : -1;
      this.navigateRelative(0, delta);
    },
    handlePageNavigation(event) {
      if (
        !this.isScriptLeader ||
        !this.initialLoad ||
        this.isScrollingProgrammatically ||
        this.intervalTimerContext != null ||
        this.intervalActive
      )
        return;

      event.preventDefault();

      const isPageDown = event.key === 'PageDown';
      let targetPage = this.currentPage + (isPageDown ? 1 : -1);

      if (targetPage < 1) {
        targetPage = 1;
      } else if (targetPage > this.currentLoadedPage) {
        return;
      }

      this.navigateTo(targetPage, 0);
    },
    handleWheelNavigation(event) {
      if (
        !this.isScriptLeader ||
        !this.initialLoad ||
        this.isScrollingProgrammatically ||
        this.intervalTimerContext != null ||
        this.intervalActive
      )
        return;

      const scriptContainer = document.getElementById('script-container');
      const isAtTop = scriptContainer.scrollTop === 0;
      const isAtBottom =
        scriptContainer.scrollHeight - scriptContainer.scrollTop === scriptContainer.clientHeight;

      if ((event.deltaY > 0 && !isAtBottom) || (event.deltaY < 0 && !isAtTop)) {
        event.preventDefault();

        const delta = event.deltaY > 0 ? 1 : -1;
        this.navigateRelative(0, delta);
      }
    },

    // Navigation initialization
    initializeNavigation() {
      if (this.initialLineRef) {
        const parts = this.initialLineRef.split('_');
        if (parts.length >= 4) {
          const page = parseInt(parts[1], 10);
          const line = parseInt(parts[3], 10);

          if (this.initialLoad) {
            this.navigateTo(page, line);
          } else {
            this.currentPage = page;
            this.currentLineOnPage = line;
          }
        }
      } else {
        this.navigateTo(1, 0);
      }
    },
    resumeNavigation() {
      if (this.sessionFollowData.current_line) {
        const parts = this.sessionFollowData.current_line.split('_');
        if (parts.length >= 4) {
          const page = parseInt(parts[1], 10);
          const line = parseInt(parts[3], 10);

          if (this.initialLoad) {
            this.navigateTo(page, line);
          } else {
            this.currentPage = page;
            this.currentLineOnPage = line;
          }
        }
      }
    },

    // Script loading
    async loadCompiledScript() {
      const response = await fetch(`${makeURL('/api/v1/show/script/compiled')}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        let maxLoadedPage = 1;
        let minLoadedPage = Number.POSITIVE_INFINITY;
        const respJson = await response.json();
        Object.entries(respJson).forEach((value) => {
          const pageNumber = parseInt(value[0], 10);
          const pageContents = value[1];

          if (pageNumber > maxLoadedPage) {
            maxLoadedPage = pageNumber;
          }
          if (pageNumber < minLoadedPage) {
            minLoadedPage = pageNumber;
          }
          this.SET_SCRIPT_PAGE({
            pageNumber,
            page: pageContents,
          });
        }, this);
        this.currentLoadedPage = maxLoadedPage;
        this.currentMinLoadedPage = minLoadedPage;
        return true;
      }
      return false;
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

    // UI computation
    computeScriptBoundaries() {
      if (this.isScrollingProgrammatically) return;

      const scriptContainer = $('#script-container');
      const cutoffTop = scriptContainer.offset().top;
      const cutoffBottom = scriptContainer.offset().top + scriptContainer.outerHeight();
      const scriptSelector = $('.script-item');

      scriptSelector.each(function filterFirst() {
        if ($(this).offset() && $(this).offset().top >= cutoffTop) {
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
      scriptSelector.each(function filterLast() {
        if ($(this).offset()) {
          if (lastObject == null) {
            lastObject = this;
          } else if (
            $(lastObject).offset() &&
            $(this).offset().top > $(lastObject).offset().top &&
            $(this).offset().top < cutoffBottom
          ) {
            lastObject = this;
          }

          if ($(this).offset().top >= cutoffBottom) {
            scriptSelector.removeClass('last-script-element');
            $(this).addClass('last-script-element');
            assignedLastScript = true;
            return false;
          }
        }
        return true;
      });

      this.assignedLastLine = assignedLastScript;
      if (!assignedLastScript && lastObject && $(lastObject).offset()) {
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

    // Line/cue helpers
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
    getCuesForLine(line) {
      if (Object.keys(this.SCRIPT_CUES).includes(line.id.toString())) {
        return this.SCRIPT_CUES[line.id.toString()];
      }
      return [];
    },
    isWholeLineCut(line) {
      return isWholeLineCutUtil(line, this.SCRIPT_CUTS);
    },
    getSpacingBefore(page, index) {
      let spacingCount = 0;
      let currentPage = page;
      let currentIndex = index - 1;

      while (currentPage >= 1) {
        const pageLines = this.GET_SCRIPT_PAGE(currentPage);

        if (currentIndex < 0) {
          currentPage--;
          if (currentPage < 1) break;

          const prevPageLines = this.GET_SCRIPT_PAGE(currentPage);
          if (!prevPageLines || prevPageLines.length === 0) break;
          currentIndex = prevPageLines.length - 1;

          continue;
        }

        if (!pageLines || currentIndex >= pageLines.length) break;

        const line = pageLines[currentIndex];

        if (line.line_type === LINE_TYPES.SPACING) {
          spacingCount++;
          currentIndex--;
        } else {
          break;
        }
      }

      return spacingCount;
    },

    // Line change handlers
    async handleLastLineChange(lastPage, lineIndex) {
      this.previousLastPage = this.currentLastPage;
      this.currentLastPage = lastPage;
      const cutoffPage = this.currentLoadedPage - this.pageBatchSize;
      if (lastPage >= cutoffPage && this.currentLoadedPage < this.currentMaxPage) {
        for (let pageLoop = 0; pageLoop < this.pageBatchSize; pageLoop++) {
          await this.loadNextPage();
        }
        this.computeScriptBoundaries();
        while (!this.assignedLastLine && this.currentLoadedPage <= this.currentMaxPage) {
          await this.loadNextPage();
          this.computeScriptBoundaries();

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

            await this.LOAD_SCRIPT_PAGE(this.currentMinLoadedPage);
          }
        }
      }
    },

    // Interval modal methods
    configureInterval(actId) {
      this.intervalActId = actId;
      this.$bvModal.show('start-interval-modal');
    },
    resetIntervalState() {
      this.intervalTimerContext = null;
      this.intervalTimerValue = '00:00:00';
    },
    onIntervalTimerContext(ctx) {
      this.intervalTimerContext = ctx;
    },
    startInterval() {
      this.$socket.sendObj({
        OP: 'BEGIN_INTERVAL',
        DATA: {
          actId: this.intervalActId,
          length: this.intervalTimerLength,
        },
      });
      this.$toast.success('Interval started!');
    },

    // Cue modal methods
    openNewCueModal(lineId) {
      this.resetNewCueForm();
      this.newCueFormState.lineId = lineId;
      this.$bvModal.show('new-cue-modal');
    },
    resetNewCueForm() {
      this.newCueFormState = {
        cueType: null,
        ident: null,
        lineId: null,
      };
      this.submittingNewCue = false;

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    validateNewCueState(name) {
      const { $dirty, $error } = this.$v.newCueFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNewCue(event) {
      this.$v.newCueFormState.$touch();
      if (this.$v.newCueFormState.$anyError || this.submittingNewCue) {
        event.preventDefault();
        return;
      }

      this.submittingNewCue = true;
      try {
        await this.ADD_NEW_CUE(this.newCueFormState);
        this.$bvModal.hide('new-cue-modal');
        this.resetNewCueForm();
      } catch (error) {
        log.error('Error submitting new cue:', error);
        event.preventDefault();
      } finally {
        this.submittingNewCue = false;
      }
    },

    // Scroll helper - scrolls element into view within the script container only
    scrollToElement(element) {
      const container = document.getElementById('script-container');
      if (!container || !element) return;

      // Calculate the element's position relative to the container
      const elementRect = element.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();

      // Calculate where the element is relative to the container's scroll position
      const elementTopRelativeToContainer =
        elementRect.top - containerRect.top + container.scrollTop;

      // Scroll the container to show the element at the top
      container.scrollTop = elementTopRelativeToContainer;
    },

    // Exposed methods (called via ref from parent)
    focusScript() {
      this.$refs['script-container']?.focus();
    },

    // Session control
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

    ...mapActions([
      'LOAD_SCRIPT_PAGE',
      'ADD_NEW_CUE',
      'GET_CURRENT_USER',
      'GET_STAGE_DIRECTION_STYLE_OVERRIDES',
      'GET_CUE_COLOUR_OVERRIDES',
      'GET_SCENE_LIST',
      'GET_CHARACTER_LIST',
      'GET_CHARACTER_GROUP_LIST',
      'GET_CUE_TYPES',
      'LOAD_CUES',
      'GET_CUTS',
      'GET_STAGE_DIRECTION_STYLES',
    ]),
    ...mapMutations(['SET_SCRIPT_PAGE']),
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
  width: 0 !important;
}

.script-container[data-following='true'] {
  overflow: hidden !important;
}

.script-footer {
  border-top: 0.1rem solid #3498db;
  padding-top: 0.5rem;
  padding-bottom: 0.1rem;
}

.center-spinner {
  margin-top: 20vh;
}
</style>
