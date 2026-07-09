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
    <!-- Add Cue Modal (tabs: Individual Cue / Cue Group) -->
    <b-modal
      id="new-cue-modal"
      title="Add Cue"
      size="lg"
      scrollable
      hide-footer
      @hidden="resetNewCueForm"
    >
      <b-tabs v-model="activeTab" class="mt-1">
        <b-tab title="Individual Cue">
          <b-form class="mt-3" @submit.stop.prevent="onSubmitNewCue">
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
          <div class="d-flex justify-content-end mt-3" style="gap: 0.5rem">
            <b-button variant="secondary" @click="$bvModal.hide('new-cue-modal')">Cancel</b-button>
            <b-button
              variant="primary"
              :disabled="$v.newCueFormState.$invalid || submittingNewCue"
              @click="onSubmitNewCue"
            >
              {{ submittingNewCue ? 'Adding…' : 'Add Cue' }}
            </b-button>
          </div>
        </b-tab>
        <b-tab title="Cue Group">
          <CueGroupForm
            ref="newGroupForm"
            :cue-type-options="cueTypeOptions"
            :cue-types="CUE_TYPES"
            class="mt-3"
            @validity-change="newGroupFormValid = $event"
          />
          <div class="d-flex justify-content-end mt-3" style="gap: 0.5rem">
            <b-button variant="secondary" @click="$bvModal.hide('new-cue-modal')">Cancel</b-button>
            <b-button
              variant="primary"
              :disabled="!newGroupFormValid || submittingNewCueGroup"
              @click="onSubmitNewCueGroup"
            >
              {{ submittingNewCueGroup ? 'Saving…' : 'Save Group' }}
            </b-button>
          </div>
        </b-tab>
      </b-tabs>
    </b-modal>
  </b-row>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { required } from 'vuelidate/lib/validators';
import { mapGetters, mapActions, mapMutations } from 'vuex';
import $ from 'jquery';
import { debounce } from 'lodash';
import log from 'loglevel';

import { makeURL } from '@/js/utils';
import ScriptLineViewer from '@/vue_components/show/live/ScriptLineViewer.vue';
import ScriptLineViewerCompact from '@/vue_components/show/live/ScriptLineViewerCompact.vue';
import CueGroupForm from '@/vue_components/show/config/cues/CueGroupForm.vue';
import { LINE_TYPES } from '@/constants/lineTypes';
import { isWholeLineCut as isWholeLineCutUtil } from '@/js/scriptUtils';

export default defineComponent({
  name: 'ScriptViewPane',
  components: {
    ScriptLineViewer,
    ScriptLineViewerCompact,
    CueGroupForm,
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
    showCurrentCueFooter: {
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
      currentLine: null as string | null,
      previousLine: null as string | null,
      isScrollingProgrammatically: false,

      // UI state
      cueAddMode: false,
      debounceContentSize: debounce((this as any).computeContentSize, 100) as any,

      // Cue modal state
      newCueFormState: {
        cueType: null as any,
        ident: null as string | null,
        lineId: null as number | null,
      },
      submittingNewCue: false,
      activeTab: 0,
      newGroupFormValid: false,
      submittingNewCueGroup: false,

      // Interval modal state
      intervalActId: null as number | null,
      intervalTimerValue: '00:00:00',
      intervalTimerContext: null as any,

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
    pageIter(): number[] {
      return [...Array(this.currentMaxPage).keys()].map((i) => i + 1);
    },
    intervalTimerLength(): number {
      if (this.intervalTimerContext == null) {
        return 0;
      }
      return (
        this.intervalTimerContext.hours * 60 * 60 +
        this.intervalTimerContext.minutes * 60 +
        this.intervalTimerContext.seconds
      );
    },
    cueTypeOptions(): any[] {
      return [
        { value: null, text: 'N/A' },
        ...(this as any).CUE_TYPES.map((cueType: any) => ({
          value: cueType.id,
          text: `${cueType.prefix}: ${cueType.description}`,
        })),
      ];
    },
    totalCueCount(): number {
      let count = 0;
      const scriptCues = (this as any).SCRIPT_CUES as Record<string, any[]>;
      Object.keys(scriptCues).forEach((line) => {
        count += scriptCues[line].length;
      });
      return count;
    },
    flatScriptCues(): any[] {
      const scriptCues = (this as any).SCRIPT_CUES as Record<string, any[]>;
      return Object.keys(scriptCues)
        .map((key) => scriptCues[key])
        .flat();
    },
    isDuplicateCue(): boolean {
      if (!this.newCueFormState.ident || !this.newCueFormState.cueType) {
        return false;
      }
      return this.flatScriptCues.some(
        (cue: any) =>
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
    sessionFollowData(): void {
      const followData = this.sessionFollowData as any;
      if (this.isScriptFollowing && followData.current_line) {
        const currentLineElement = document.getElementById(followData.current_line);
        if (currentLineElement != null) {
          const idParts = followData.current_line.split('_');
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
          this.currentLineOnPage = line;
          this.$emit('page-change', page);
          this.$emit('current-line-change', line);
          this.computeScriptBoundaries();
        }
      }
    },
    totalCueCount(): void {
      this.$nextTick(() => {
        if (this.initialLoad) {
          this.resumeNavigation();
        }
      });
    },
    showCurrentCueFooter(): void {
      this.$nextTick(() => {
        this.computeContentSize();
        this.observeFooterResize();
      });
    },
  },
  async mounted(): Promise<void> {
    // Load all independent data in parallel
    await Promise.all([
      // User data (style overrides loaded after user resolves)
      (this as any).GET_CURRENT_USER().then(() => {
        if ((this as any).CURRENT_USER != null) {
          return Promise.all([
            (this as any).GET_STAGE_DIRECTION_STYLE_OVERRIDES(),
            (this as any).GET_CUE_COLOUR_OVERRIDES(),
          ]);
        }
        return Promise.resolve();
      }),
      // Show metadata
      (this as any).GET_SCENE_LIST(),
      (this as any).GET_CHARACTER_LIST(),
      (this as any).GET_CHARACTER_GROUP_LIST(),
      (this as any).GET_CUE_TYPES(),
      (this as any).LOAD_CUES(),
      (this as any).GET_CUTS(),
      (this as any).GET_STAGE_DIRECTION_STYLES(),
      // Script page count
      this.getMaxScriptPage(),
    ]);

    this.computeContentSize();
    this.observeFooterResize();

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
  destroyed(): void {
    (this as any).footerResizeObserver?.disconnect();
    this.removeNavigation();
    window.removeEventListener('resize', this.debounceContentSize);
  },
  methods: {
    // Navigation setup/teardown
    setupNavigation(): void {
      window.addEventListener('keydown', this.handleKeyPress);
      const scriptContainer = document.getElementById('script-container');
      if (scriptContainer) {
        scriptContainer.addEventListener('wheel', this.handleWheelNavigation, { passive: false });
      }
    },
    removeNavigation(): void {
      window.removeEventListener('keydown', this.handleKeyPress);
      const scriptContainer = document.getElementById('script-container');
      if (scriptContainer) {
        scriptContainer.removeEventListener('wheel', this.handleWheelNavigation);
      }
    },

    // Navigation execution
    navigateTo(targetPage: number, targetLineOnPage: number, preventScroll = false): boolean {
      if (targetPage > Number(this.currentLoadedPage)) {
        return false;
      }

      const pageLines = (this as any).GET_SCRIPT_PAGE(targetPage);
      if (!pageLines || targetLineOnPage >= pageLines.length) {
        return false;
      }

      this.currentPage = targetPage;
      this.currentLineOnPage = targetLineOnPage;
      this.$emit('page-change', targetPage);
      this.$emit('current-line-change', targetLineOnPage);

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
          (this as any).$socket.sendObj({
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
    findContextElement(
      targetPage: number,
      targetLineOnPage: number,
      contextLines: number
    ): Element | null {
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

          const prevPageLines = (this as any).GET_SCRIPT_PAGE(currentPage);
          if (!prevPageLines || prevPageLines.length === 0) {
            continue;
          }

          currentLine = prevPageLines.length - 1;
        }

        const pageLines = (this as any).GET_SCRIPT_PAGE(currentPage);
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
    navigateRelative(deltaPage: number, deltaLine: number): boolean {
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
            const prevPageLines = (this as any).GET_SCRIPT_PAGE(newPage);
            if (!prevPageLines) break;
            newLineOnPage = prevPageLines.length - 1;
            if (newLineOnPage < 0) newLineOnPage = 0;
          }
        } else {
          const currentPageLines = (this as any).GET_SCRIPT_PAGE(newPage);
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

        const pageLines = (this as any).GET_SCRIPT_PAGE(newPage);
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
    handleKeyPress(event: KeyboardEvent): void {
      if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
        this.handleKeyNavigation(event);
      } else if (event.key === 'PageUp' || event.key === 'PageDown') {
        this.handlePageNavigation(event);
      } else if (event.key === 'C') {
        this.handleCueEditToggle(event);
      }
    },
    handleCueEditToggle(event: KeyboardEvent): void {
      event.preventDefault();
      if ((this as any).IS_SHOW_EDITOR) {
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
    handleKeyNavigation(event: KeyboardEvent): void {
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
    handlePageNavigation(event: KeyboardEvent): void {
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
    handleWheelNavigation(event: WheelEvent): void {
      if (
        !this.isScriptLeader ||
        !this.initialLoad ||
        this.isScrollingProgrammatically ||
        this.intervalTimerContext != null ||
        this.intervalActive
      )
        return;

      const scriptContainer = document.getElementById('script-container');
      const isAtTop = scriptContainer!.scrollTop === 0;
      const isAtBottom =
        scriptContainer!.scrollHeight - scriptContainer!.scrollTop ===
        scriptContainer!.clientHeight;

      if ((event.deltaY > 0 && !isAtBottom) || (event.deltaY < 0 && !isAtTop)) {
        event.preventDefault();

        const delta = event.deltaY > 0 ? 1 : -1;
        this.navigateRelative(0, delta);
      }
    },

    // Navigation initialization
    initializeNavigation(): void {
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
    resumeNavigation(): void {
      if ((this.sessionFollowData as any).current_line) {
        const parts = (this.sessionFollowData as any).current_line.split('_');
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
    async loadCompiledScript(): Promise<boolean> {
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
          (this as any).SET_SCRIPT_PAGE({
            pageNumber,
            page: pageContents,
          });
        });
        this.currentLoadedPage = maxLoadedPage;
        this.currentMinLoadedPage = minLoadedPage;
        return true;
      }
      return false;
    },
    async loadNextPage(): Promise<void> {
      if (this.currentLoadedPage < this.currentMaxPage) {
        this.currentLoadedPage += 1;
        await (this as any).LOAD_SCRIPT_PAGE(this.currentLoadedPage);
      }
    },
    async getMaxScriptPage(): Promise<void> {
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
      const footer = $('#current-cue-footer');
      const footerHeight = footer.length > 0 ? (footer.outerHeight() ?? 0) : 0;
      const startPos = scriptContainer.offset().top;
      const boxHeight = document.documentElement.clientHeight - startPos - footerHeight;
      scriptContainer.height(boxHeight - 10);
      this.computeScriptBoundaries();
    },
    observeFooterResize() {
      (this as any).footerResizeObserver?.disconnect();
      (this as any).footerResizeObserver = null;
      const footer = document.getElementById('current-cue-footer');
      if (footer) {
        (this as any).footerResizeObserver = new ResizeObserver(() => this.debounceContentSize());
        (this as any).footerResizeObserver.observe(footer);
      }
    },

    // Line/cue helpers
    getPreviousLineForIndex(pageIndex: number, lineIndex: number): any {
      if (lineIndex > 0) {
        return (this as any).GET_SCRIPT_PAGE(pageIndex)[lineIndex - 1];
      }
      let loopPageNo = pageIndex - 1;
      while (loopPageNo >= 1) {
        const loopPage = (this as any).GET_SCRIPT_PAGE(loopPageNo);
        if (loopPage.length > 0) {
          return loopPage[loopPage.length - 1];
        }
        loopPageNo -= 1;
      }
      return null;
    },
    getPreviousLineIndex(pageIndex: number, lineIndex: number): number | null {
      if (lineIndex > 0) {
        return lineIndex - 1;
      }
      let loopPageNo = pageIndex - 1;
      while (loopPageNo >= 1) {
        const loopPage = (this as any).GET_SCRIPT_PAGE(loopPageNo);
        if (loopPage.length > 0) {
          return loopPage.length - 1;
        }
        loopPageNo -= 1;
      }
      return null;
    },
    getCuesForLine(line: any): any[] {
      const scriptCues = (this as any).SCRIPT_CUES as Record<string, any[]>;
      if (Object.keys(scriptCues).includes(line.id.toString())) {
        return scriptCues[line.id.toString()];
      }
      return [];
    },
    isWholeLineCut(line: any): boolean {
      return isWholeLineCutUtil(line, (this as any).SCRIPT_CUTS);
    },
    getSpacingBefore(page: number, index: number): number {
      let spacingCount = 0;
      let currentPage = page;
      let currentIndex = index - 1;

      while (currentPage >= 1) {
        const pageLines = (this as any).GET_SCRIPT_PAGE(currentPage);

        if (currentIndex < 0) {
          currentPage--;
          if (currentPage < 1) break;

          const prevPageLines = (this as any).GET_SCRIPT_PAGE(currentPage);
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
    async handleLastLineChange(lastPage: number, lineIndex: number): Promise<void> {
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
    async handleFirstLineChange(
      firstPage: number,
      lineIndex: number,
      previousLine: string
    ): Promise<void> {
      this.previousFirstPage = this.currentFirstPage;
      this.currentFirstPage = firstPage;
      this.previousLine = previousLine;
      this.currentLine = `page_${firstPage}_line_${lineIndex}`;

      const cutoffPage = firstPage - this.pageBatchSize;
      if ((this.currentMinLoadedPage ?? 0) > cutoffPage) {
        for (let pageLoop = 0; pageLoop < this.pageBatchSize; pageLoop++) {
          if ((this.currentMinLoadedPage ?? 0) > 1) {
            this.currentMinLoadedPage = (this.currentMinLoadedPage ?? 1) - 1;

            await (this as any).LOAD_SCRIPT_PAGE(this.currentMinLoadedPage);
          }
        }
      }
    },

    // Interval modal methods
    configureInterval(actId: number): void {
      this.intervalActId = actId;
      (this as any).$bvModal.show('start-interval-modal');
    },
    resetIntervalState(): void {
      this.intervalTimerContext = null;
      this.intervalTimerValue = '00:00:00';
    },
    onIntervalTimerContext(ctx: any): void {
      this.intervalTimerContext = ctx;
    },
    startInterval(): void {
      (this as any).$socket.sendObj({
        OP: 'BEGIN_INTERVAL',
        DATA: {
          actId: this.intervalActId,
          length: this.intervalTimerLength,
        },
      });
      (this as any).$toast.success('Interval started!');
    },

    // Cue modal methods
    openNewCueModal(lineId: number): void {
      this.activeTab = 0;
      this.newGroupFormValid = false;
      this.newCueFormState = { cueType: null, ident: null, lineId: lineId };
      this.$nextTick(() => {
        (this as any).$v.$reset();
        (this.$refs.newGroupForm as any)?.reset();
      });
      (this as any).$bvModal.show('new-cue-modal');
    },
    resetNewCueForm(): void {
      this.newCueFormState = { cueType: null, ident: null, lineId: null };
      this.activeTab = 0;
      this.newGroupFormValid = false;
      this.submittingNewCue = false;
      this.submittingNewCueGroup = false;
      this.$nextTick(() => {
        (this as any).$v.$reset();
        (this.$refs.newGroupForm as any)?.reset();
      });
    },
    validateNewCueState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.newCueFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNewCue(): Promise<void> {
      (this as any).$v.newCueFormState.$touch();
      if ((this as any).$v.newCueFormState.$anyError || this.submittingNewCue) return;
      this.submittingNewCue = true;
      try {
        await (this as any).ADD_NEW_CUE(this.newCueFormState);
        (this as any).$bvModal.hide('new-cue-modal');
      } catch (error) {
        log.error('Error submitting new cue:', error);
      } finally {
        this.submittingNewCue = false;
      }
    },
    async onSubmitNewCueGroup(): Promise<void> {
      if (!this.newGroupFormValid || this.submittingNewCueGroup) return;
      const form = this.$refs.newGroupForm as any;
      if (!form) {
        log.error('CueGroupForm ref not available when submitting group');
        return;
      }
      this.submittingNewCueGroup = true;
      try {
        const data = form.getFormData();
        await (this as any).ADD_CUE_GROUP({
          cueTypeId: data.cueTypeId,
          labelOverride: data.labelOverride || undefined,
          lineId: this.newCueFormState.lineId,
          cues: data.cues.map((c: any, i: number) => ({ ident: c.ident, sortOrder: i })),
        });
        (this as any).$bvModal.hide('new-cue-modal');
      } catch (error) {
        log.error('Error submitting new cue group:', error);
      } finally {
        this.submittingNewCueGroup = false;
      }
    },
    // Scroll helper - scrolls element into view within the script container only
    scrollToElement(element: Element | null): void {
      const container = document.getElementById('script-container');
      if (!container || !element) return;

      const elementRect = element.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();

      const elementTopRelativeToContainer =
        elementRect.top - containerRect.top + container.scrollTop;

      container.scrollTop = elementTopRelativeToContainer;
    },

    // Exposed methods (called via ref from parent)
    focusScript(): void {
      (this.$refs['script-container'] as HTMLElement | undefined)?.focus();
    },

    // Session control
    async stopShow(): Promise<void> {
      this.stoppingSession = true;
      const response = await fetch(`${makeURL('/api/v1/show/sessions/stop')}`, {
        method: 'POST',
      });
      if (response.ok) {
        (this as any).$toast.success('Stopped show session');
      } else {
        log.error('Unable to stop show session');
        (this as any).$toast.error('Unable to stop show session');
      }
      this.stoppingSession = false;
    },

    ...mapActions([
      'LOAD_SCRIPT_PAGE',
      'ADD_NEW_CUE',
      'ADD_CUE_GROUP',
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
});
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
