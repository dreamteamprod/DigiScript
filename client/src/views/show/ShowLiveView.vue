<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row
      class="session-header"
      style="padding-top: .1rem; padding-bottom: .1rem"
    >
      <b-col
        cols="4"
        style="text-align: left"
      >
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
          Page {{ currentPage }}
        </b>
      </b-col>
      <b-col
        cols="4"
        style="text-align: right"
      >
        <b>
          Elapsed Time: {{ msToTimerString(elapsedTime) }}
        </b>
      </b-col>
    </b-row>
    <b-overlay
      :show="CURRENT_SHOW_INTERVAL != null"
      rounded="sm"
      variant="secondary"
      @shown="onOverlayShown"
      @hidden="onOverlayHidden"
    >
      <template #overlay>
        <div
          ref="interval-overlay"
          class="text-center"
        >
          <b-container
            class="mx-0"
            fluid
          >
            <b-row>
              <b-col class="d-flex align-items-center justify-content-center">
                <h3>
                  {{ intervalOverlayHeading }} - Interval in Progress
                  <b-icon
                    icon="stopwatch"
                    animation="cylon"
                  />
                </h3>
              </b-col>
            </b-row>
            <b-row v-if="intervalTimer != null">
              <b-col class="d-flex align-items-center justify-content-center">
                <h1 style="margin-top: .5rem">
                  <!-- eslint-disable-next-line max-len -->
                  <span :style="intervalTimerStyle">{{ intervalTimerValues[0] }}</span>:<span :style="intervalTimerStyle">{{ intervalTimerValues[1] }}</span>:<span :style="intervalTimerStyle">{{ intervalTimerValues[2] }}</span>
                </h1>
              </b-col>
            </b-row>
            <b-row style="margin-top: .5rem">
              <b-col class="d-flex align-items-center justify-content-center">
                <b-button
                  v-if="isScriptLeader"
                  variant="primary"
                  @click.stop="stopInterval"
                >
                  Stop Interval
                </b-button>
              </b-col>
            </b-row>
          </b-container>
        </div>
      </template>
      <b-row
        ref="script-container"
        :aria-hidden="CURRENT_SHOW_INTERVAL != null ? 'true' : null"
      >
        <b-col
          id="script-container"
          cols="12"
          class="script-container"
          :data-following="isScriptFollowing"
        >
          <div
            v-if="!initialLoad"
            class="text-center center-spinner"
          >
            <b-spinner
              style="width: 10rem; height: 10rem;"
              variant="info"
            />
          </div>
          <template v-else>
            <template v-for="page in pageIter">
              <script-line-viewer
                v-for="(line, index) in GET_SCRIPT_PAGE(page)"
                v-show="!isWholeLineCut(line)"
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
                @last-line-change="handleLastLineChange"
                @first-line-change="handleFirstLineChange"
                @start-interval="configureInterval"
                @add-cue="openNewCueModal"
              />
            </template>
            <b-row
              v-show="initialLoad"
              class="script-footer"
            >
              <b-col>
                <b-button-group>
                  <b-button
                    variant="danger"
                    :disabled="stoppingSession"
                    @click.stop="stopShow"
                  >
                    End Show
                  </b-button>
                </b-button-group>
              </b-col>
            </b-row>
          </template>
        </b-col>
      </b-row>
    </b-overlay>
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
      <b-container
        class="mx-0"
        fluid
      >
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
            <b-alert
              show
              variant="info"
            >
              Select the length of the interval (HH:MM:SS)
            </b-alert>
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
      <b-form
        ref="new-cue-form"
        @submit.stop.prevent="onSubmitNewCue"
      >
        <b-form-group
          id="type-input-group"
          label="Cue Type"
          label-for="type-input"
        >
          <b-form-select
            id="type-input"
            v-model="$v.newCueFormState.cueType.$model"
            :options="cueTypeOptions"
            :state="validateNewCueState('cueType')"
            aria-describedby="cue-type-feedback"
          />
          <b-form-invalid-feedback
            id="cue-type-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="ident-input-group"
          label="Identifier"
          label-for="ident-input"
        >
          <b-form-input
            id="ident-input"
            v-model="$v.newCueFormState.ident.$model"
            name="ident-input"
            :state="validateNewCueState('ident')"
            aria-describedby="ident-feedback"
          />
          <b-form-invalid-feedback
            id="ident-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
          <b-form-text
            v-if="isDuplicateCue"
            class="text-warning"
          >
            ⚠️ A cue with this identifier already exists for this cue type
          </b-form-text>
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script>
import { required } from 'vuelidate/lib/validators';
import { mapGetters, mapActions, mapMutations } from 'vuex';
import $ from 'jquery';
import { debounce } from 'lodash';
import log from 'loglevel';

import {
  formatTimerParts, makeURL, msToTimerParts, msToTimerString,
} from '@/js/utils';
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
      currentLoadedPage: 0, // Last loaded page number (1-based)
      currentMaxPage: 0, // Total number of pages in script (1-based)
      stoppingSession: false,
      initialLoad: false,
      currentFirstPage: 1, // First visible page (1-based, initialized to page 1)
      currentLastPage: 1, // Last visible page (1-based, initialized to page 1)
      pageBatchSize: 3,
      startTime: null,
      previousFirstPage: 1,
      previousLastPage: 1,
      assignedLastLine: false,
      currentLine: null,
      previousLine: null,
      currentMinLoadedPage: null,
      fullLoad: false,
      loadedSessionData: false,
      currentPage: 1,
      currentLineOnPage: 0,
      isScrollingProgrammatically: false,
      debounceContentSize: debounce(this.computeContentSize, 100),
      intervalActId: null,
      intervalTimerValue: '00:00:00',
      intervalTimerContext: null,
      intervalTimer: null,
      intervalStartDate: null,
      isIntervalLong: false,
      intervalTimerValues: [0, 0, 0],
      intervalRemainingTime: 0,
      cueAddMode: false,
      newCueFormState: {
        cueType: null,
        ident: null,
        lineId: null,
      },
      submittingNewCue: false,
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
      // Generate 1-based page indices (DigiScript pages are numbered starting from 1, not 0)
      return [...Array(this.currentMaxPage).keys()].map((i) => i + 1);
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
    intervalTimerLength() {
      if (this.intervalTimerContext == null) {
        return 0;
      }
      return ((this.intervalTimerContext.hours * 60 * 60)
        + (this.intervalTimerContext.minutes * 60)
        + this.intervalTimerContext.seconds);
    },
    intervalOverlayHeading() {
      if (this.CURRENT_SHOW_INTERVAL == null || this.ACT_LIST.length === 0) {
        return '';
      }
      return this.ACT_LIST.find((act) => (act.id === this.CURRENT_SHOW_INTERVAL.act_id)).name;
    },
    intervalTimerColour() {
      if (this.isIntervalLong) {
        return '#cc0000';
      }
      const intervalProgress = (Math.abs(this.intervalRemainingTime)
        / (this.CURRENT_SHOW_INTERVAL.initial_length * 1000));
      if (intervalProgress > 0.25) {
        return '#00cc00';
      }
      return '#d76113';
    },
    intervalTimerStyle() {
      return {
        margin: '.5rem',
        'border-radius': '3px',
        color: '#ffffff',
        'background-color': this.intervalTimerColour,
        padding: '.25rem',
      };
    },
    cueTypeOptions() {
      return [
        { value: null, text: 'N/A' },
        ...this.CUE_TYPES.map((cueType) => ({ value: cueType.id, text: `${cueType.prefix}: ${cueType.description}` })),
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
      return Object.keys(this.SCRIPT_CUES).map((key) => this.SCRIPT_CUES[key]).flat();
    },
    isDuplicateCue() {
      if (!this.newCueFormState.ident || !this.newCueFormState.cueType) {
        return false;
      }
      return this.flatScriptCues.some((cue) => cue.cue_type_id === this.newCueFormState.cueType
        && cue.ident === this.newCueFormState.ident);
    },
    ...mapGetters(['CURRENT_SHOW_SESSION', 'GET_SCRIPT_PAGE', 'ACT_LIST', 'SCENE_LIST',
      'CHARACTER_LIST', 'CHARACTER_GROUP_LIST', 'CURRENT_SHOW', 'CUE_TYPES', 'SCRIPT_CUES',
      'INTERNAL_UUID', 'SESSION_FOLLOW_DATA', 'SCRIPT_CUTS', 'SETTINGS', 'STAGE_DIRECTION_STYLES',
      'CURRENT_USER', 'STAGE_DIRECTION_STYLE_OVERRIDES', 'CURRENT_SHOW_INTERVAL', 'IS_SHOW_EDITOR']),
  },
  watch: {
    SESSION_FOLLOW_DATA() {
      if (this.isScriptFollowing) {
        // Get the current line element
        const currentLineElement = document.getElementById(this.SESSION_FOLLOW_DATA.current_line);
        if (currentLineElement != null) {
        // Extract page and line from the ID
          const idParts = this.SESSION_FOLLOW_DATA.current_line.split('_');
          const page = parseInt(idParts[1], 10);
          const line = parseInt(idParts[3], 10);

          // Update the current line highlight
          $('.script-item').removeClass('current-line');
          $(currentLineElement).addClass('current-line');

          // Find the context element to scroll to
          const contextLines = 3; // Same as in navigateTo
          const contextElement = this.findContextElement(page, line, contextLines);

          // Scroll to the context element if found, otherwise the current line
          if (contextElement) {
            contextElement.scrollIntoView({
              behavior: 'instant',
              block: 'start',
            });
          } else {
            currentLineElement.scrollIntoView({
              behavior: 'instant',
              block: 'start',
            });
          }
          this.currentPage = page;
          this.computeScriptBoundaries();
        }
      }
    },
    CURRENT_SHOW_INTERVAL() {
      this.setupIntervalTimer();
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
    await this.GET_SHOW_SESSION_DATA();
    this.loadedSessionData = true;
    if (this.CURRENT_SHOW_INTERVAL != null) {
      this.setupIntervalTimer();
    }
    // Get the current user
    await this.GET_CURRENT_USER();

    // User related stuff
    if (this.CURRENT_USER != null) {
      await this.GET_STAGE_DIRECTION_STYLE_OVERRIDES();
      await this.GET_CUE_COLOUR_OVERRIDES();
    }

    await this.GET_ACT_LIST();
    await this.GET_SCENE_LIST();
    await this.GET_CHARACTER_LIST();
    await this.GET_CHARACTER_GROUP_LIST();
    await this.GET_CUE_TYPES();
    await this.LOAD_CUES();
    await this.GET_CUTS();
    await this.GET_STAGE_DIRECTION_STYLES();
    await this.getMaxScriptPage();

    this.updateElapsedTime();
    this.computeContentSize();

    this.startTime = this.createDateAsUTC(new Date(this.CURRENT_SHOW_SESSION.start_date_time.replace(' ', 'T')));
    this.elapsedTimer = setInterval(this.updateElapsedTime, 1000);
    window.addEventListener('resize', this.debounceContentSize);

    // Try and load the full script from the compiled endpoint
    const loadedCompiledScript = await this.loadCompiledScript();

    if (this.isScriptFollowing || this.isScriptLeader) {
      if (this.CURRENT_SHOW_SESSION.latest_line_ref != null) {
        const loadCurrentPage = parseInt(this.CURRENT_SHOW_SESSION.latest_line_ref.split('_')[1], 10);

        if (!loadedCompiledScript) {
          this.currentMinLoadedPage = 1;
          for (let loadIndex = 0; loadIndex < this.currentMaxPage; loadIndex++) {
            // eslint-disable-next-line no-await-in-loop
            await this.loadNextPage();
          }
          this.currentFirstPage = loadCurrentPage;
          this.currentLastPage = loadCurrentPage;
        }

        await this.$nextTick();
        this.initialLoad = true;
        await this.$nextTick();
        this.computeScriptBoundaries();
        document.getElementById(this.CURRENT_SHOW_SESSION.latest_line_ref).scrollIntoView({
          behavior: 'instant',
          block: 'start',
        });
        await this.$nextTick();
        this.computeScriptBoundaries();
      } else {
        if (!loadedCompiledScript) {
          this.currentMinLoadedPage = 1;
          for (let loadIndex = 0; loadIndex < this.currentMaxPage; loadIndex++) {
            // eslint-disable-next-line no-await-in-loop
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
          // eslint-disable-next-line no-await-in-loop
          await this.loadNextPage();
        }
      }
      this.initialLoad = true;
      await this.$nextTick();
      this.computeScriptBoundaries();
    }

    this.fullLoad = true;
    this.setupNavigation();
    // Wait for initial load
    this.$nextTick(() => {
      if (this.initialLoad) {
        this.initializeNavigation();
      }
    });
  },
  destroyed() {
    clearInterval(this.elapsedTimer);
    this.removeNavigation();
    window.removeEventListener('resize', this.debounceContentSize);
  },
  methods: {
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
    navigateTo(targetPage, targetLineOnPage, preventScroll = false) {
      // Check if the page is loaded
      if (targetPage > this.currentLoadedPage) {
        return false;
      }

      // Check if the target line exists on that page
      const pageLines = this.GET_SCRIPT_PAGE(targetPage);
      if (!pageLines || targetLineOnPage >= pageLines.length) {
        return false;
      }

      // Update internal state
      this.currentPage = targetPage;
      this.currentLineOnPage = targetLineOnPage;

      // Find the element for this line
      const targetElementId = `page_${targetPage}_line_${targetLineOnPage}`;
      const targetElement = document.getElementById(targetElementId);

      if (!targetElement) {
        log.error(`Could not find element for line: ${targetElementId}`);
        return false;
      }

      // Update line highlighting
      $('.script-item').removeClass('current-line');
      $(targetElement).addClass('current-line');

      // Update line tracking for the rest of the application
      this.previousLine = this.currentLine;
      this.currentLine = targetElementId;

      // Scroll the element into view (unless prevented)
      if (!preventScroll) {
        this.isScrollingProgrammatically = true;
        // Instead of directly scrolling to the target element,
        // find the context element (N visible lines above) and scroll to it
        const contextLines = 3;
        const contextElement = this.findContextElement(targetPage, targetLineOnPage, contextLines);

        if (contextElement) {
          // Scroll to the context element instead of the target element
          contextElement.scrollIntoView({
            behavior: 'instant',
            block: 'start',
          });
        } else {
          // Fall back to standard scrolling if we can't find a context element
          targetElement.scrollIntoView({
            behavior: 'instant',
            block: 'start',
          });
        }

        // Send update to followers
        if (this.fullLoad) {
          this.$socket.sendObj({
            OP: 'SCRIPT_SCROLL',
            DATA: {
              previous_line: this.previousLine,
              current_line: this.currentLine,
            },
          });
        }

        // Reset scrolling flag after animation completes
        setTimeout(() => {
          this.isScrollingProgrammatically = false;
          this.computeScriptBoundaries();
        }, 50);
      }

      return true;
    },
    findContextElement(targetPage, targetLineOnPage, contextLines) {
      // Start from the target line and move backwards
      let currentPage = targetPage;
      let currentLine = targetLineOnPage;
      let visibleLinesFound = 0;

      while (visibleLinesFound < contextLines && currentPage >= 1) {
        // Move to the previous line
        currentLine--;

        // If we've gone before the first line on this page, move to the previous page
        if (currentLine < 0) {
          currentPage--;
          if (currentPage < 1) {
            // We've reached the beginning of the script, return the first line
            return document.getElementById('page_1_line_0');
          }

          // Get the lines on the previous page
          const prevPageLines = this.GET_SCRIPT_PAGE(currentPage);
          if (!prevPageLines || prevPageLines.length === 0) {
            // Skip empty pages
            // eslint-disable-next-line no-continue
            continue;
          }

          // Move to the last line of the previous page
          currentLine = prevPageLines.length - 1;
        }

        // Check if this line is visible (not cut)
        const pageLines = this.GET_SCRIPT_PAGE(currentPage);
        if (pageLines && currentLine < pageLines.length) {
          const line = pageLines[currentLine];
          if (!this.isWholeLineCut(line)) {
            visibleLinesFound++;

            // If we've found enough visible lines, this is our context line
            if (visibleLinesFound >= contextLines) {
              return document.getElementById(`page_${currentPage}_line_${currentLine}`);
            }
          }
        }
      }

      // If we couldn't find enough visible lines, return the earliest visible line we found
      if (visibleLinesFound > 0) {
        return document.getElementById(`page_${currentPage}_line_${currentLine}`);
      }

      // If we couldn't find any visible lines above, just return null
      // and let the main method fall back to the target line
      return null;
    },
    navigateRelative(deltaPage, deltaLine) {
      // If no navigation needed, exit early
      if (deltaLine === 0 && deltaPage === 0) return true;

      // Direction of navigation (positive for down/forward, negative for up/backward)
      const direction = deltaLine > 0 ? 1 : -1;

      // Start from current position
      let newPage = this.currentPage;
      let newLineOnPage = this.currentLineOnPage;

      // Keep track of how many visible lines we've moved
      let visibleLinesMoved = 0;

      // Continue until we've moved the requested number of visible lines
      while (visibleLinesMoved < Math.abs(deltaLine)) {
        // Move one line in the appropriate direction
        newLineOnPage += direction;

        // Handle line overflow/underflow
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

        // Check if this line is visible (not cut)
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

      // Navigate to the calculated position
      return this.navigateTo(newPage, newLineOnPage);
    },
    handleKeyPress(event) {
      // Process arrow keys
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
      // Only handle if we're the leader and not currently scrolling or starting an interval
      if (!this.isScriptLeader || !this.initialLoad || this.isScrollingProgrammatically
        || this.intervalTimerContext != null || this.CURRENT_SHOW_INTERVAL != null) return;

      event.preventDefault();

      // Always move by 1 visible line in the appropriate direction
      const delta = event.key === 'ArrowDown' ? 1 : -1;
      this.navigateRelative(0, delta);
    },
    handlePageNavigation(event) {
      // Only handle if we're the leader and not currently scrolling or starting an interval
      if (!this.isScriptLeader || !this.initialLoad || this.isScrollingProgrammatically
        || this.intervalTimerContext != null || this.CURRENT_SHOW_INTERVAL != null) return;

      event.preventDefault();

      // Navigate by page increments
      const isPageDown = event.key === 'PageDown';
      let targetPage = this.currentPage + (isPageDown ? 1 : -1);

      // Ensure we stay within valid page bounds
      if (targetPage < 1) {
        targetPage = 1;
      } else if (targetPage > this.currentLoadedPage) {
        // Don't navigate beyond loaded pages
        return;
      }

      // Navigate to the first line of the target page
      this.navigateTo(targetPage, 0);
    },
    handleWheelNavigation(event) {
      // Only handle if we're the leader and not currently scrolling or starting an interval
      if (!this.isScriptLeader || !this.initialLoad || this.isScrollingProgrammatically
        || this.intervalTimerContext != null || this.CURRENT_SHOW_INTERVAL != null) return;

      // Don't take over all scrolling, just script navigation
      // We need to check if we're at the top or bottom of the container
      const scriptContainer = document.getElementById('script-container');
      const isAtTop = scriptContainer.scrollTop === 0;
      const isAtBottom = (
        scriptContainer.scrollHeight - scriptContainer.scrollTop === scriptContainer.clientHeight
      );

      // Only prevent default if we're not at the limits of the container
      if ((event.deltaY > 0 && !isAtBottom) || (event.deltaY < 0 && !isAtTop)) {
        event.preventDefault();

        // Always move by 1 visible line in the appropriate direction
        const delta = event.deltaY > 0 ? 1 : -1;
        this.navigateRelative(0, delta);
      }
    },
    initializeNavigation() {
      // If we have a CURRENT_SHOW_SESSION.latest_line_ref, use that
      if (this.CURRENT_SHOW_SESSION.latest_line_ref) {
        const parts = this.CURRENT_SHOW_SESSION.latest_line_ref.split('_');
        if (parts.length >= 4) {
          const page = parseInt(parts[1], 10);
          const line = parseInt(parts[3], 10);

          // Only set position after initial load is complete
          if (this.initialLoad) {
            this.navigateTo(page, line);
          } else {
            // Remember position for later
            this.currentPage = page;
            this.currentLineOnPage = line;
          }
        }
      } else {
        // Default to first line if no previous position
        this.navigateTo(1, 0);
      }
    },
    resumeNavigation() {
      if (this.SESSION_FOLLOW_DATA.current_line) {
        const parts = this.SESSION_FOLLOW_DATA.current_line.split('_');
        if (parts.length >= 4) {
          const page = parseInt(parts[1], 10);
          const line = parseInt(parts[3], 10);

          // Only set position after initial load is complete
          if (this.initialLoad) {
            this.navigateTo(page, line);
          } else {
            // Remember position for later
            this.currentPage = page;
            this.currentLineOnPage = line;
          }
        }
      }
    },
    msToTimerString,
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
      // Skip if we're programmatically scrolling
      if (this.isScrollingProgrammatically) return;

      // Original boundary computation for first/last elements only
      const scriptContainer = $('#script-container');
      const cutoffTop = scriptContainer.offset().top;
      const cutoffBottom = scriptContainer.offset().top + scriptContainer.outerHeight();
      const scriptSelector = $('.script-item');

      // Update first element class
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

      // Update last element class
      let assignedLastScript = false;
      let lastObject = null;
      scriptSelector.each(function filterLast() {
        if ($(this).offset()) {
          if (lastObject == null) {
            lastObject = this;
          } else if ($(lastObject).offset()
               && $(this).offset().top > $(lastObject).offset().top
               && $(this).offset().top < cutoffBottom) {
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
          const pageNumber = value[0];
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
      return line.line_parts.every((linePart) => (this.SCRIPT_CUTS.includes(linePart.id)
          || linePart.line_text == null || linePart.line_text.trim().length === 0), this);
    },
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
    stopInterval() {
      this.$socket.sendObj({
        OP: 'END_INTERVAL',
        DATA: {},
      });
      this.$toast.success('Interval stopped!');
    },
    onOverlayShown() {
      this.$refs['interval-overlay'].focus();
    },
    onOverlayHidden() {
      this.$refs['script-container'].focus();
    },
    setupIntervalTimer() {
      clearInterval(this.intervalTimer);
      this.intervalTimer = null;
      this.intervalTimerValues = [0, 0, 0];
      this.isIntervalLong = false;
      this.intervalRemainingTime = 0;
      if (this.CURRENT_SHOW_INTERVAL != null) {
        this.intervalStartDate = this.createDateAsUTC(new Date(this.CURRENT_SHOW_INTERVAL.start_datetime.replace(' ', 'T')));
        this.updateIntervalTimer();
        this.intervalTimer = setInterval(this.updateIntervalTimer, 500);
      }
    },
    updateIntervalTimer() {
      if (this.intervalStartDate != null) {
        const intervalElapsedTime = Date.now() - this.intervalStartDate;
        this.intervalRemainingTime = (
          this.CURRENT_SHOW_INTERVAL.initial_length * 1000
        ) - intervalElapsedTime;
        if (this.intervalRemainingTime < 0) {
          this.isIntervalLong = true;
        }
        this.intervalTimerValues = formatTimerParts(
          ...msToTimerParts(Math.abs(this.intervalRemainingTime)),
        );
      }
    },
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
    ...mapActions(['GET_SHOW_SESSION_DATA', 'LOAD_SCRIPT_PAGE', 'GET_ACT_LIST', 'GET_SCENE_LIST',
      'GET_CHARACTER_LIST', 'GET_CHARACTER_GROUP_LIST', 'LOAD_CUES', 'GET_CUE_TYPES',
      'GET_CUTS', 'GET_STAGE_DIRECTION_STYLES', 'GET_CURRENT_USER', 'GET_STAGE_DIRECTION_STYLE_OVERRIDES',
      'GET_CUE_COLOUR_OVERRIDES', 'ADD_NEW_CUE']),
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

  .script-container::-webkit-scrollbar{
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
</style>
