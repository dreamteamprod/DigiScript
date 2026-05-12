<template>
  <b-container v-if="loaded" class="mx-0 px-0 script-editor-container" fluid>
    <div class="sticky-header" :style="{ top: navbarHeight + 'px' }">
      <b-row class="script-row">
        <b-col cols="2">
          <b-button v-b-modal.go-to-page-script-editor variant="success"> Go to Page </b-button>
        </b-col>
        <b-col cols="2" style="text-align: right">
          <b-button variant="success" :disabled="currentEditPage === 1" @click="decrPage">
            Prev Page
          </b-button>
        </b-col>
        <b-col cols="4">
          <p>Current Page: {{ currentEditPage }}</p>
        </b-col>
        <b-col cols="2" style="text-align: left">
          <b-button variant="success" @click="incrPage"> Next Page </b-button>
        </b-col>
        <b-col cols="2">
          <b-button-group v-if="IS_SCRIPT_EDITOR">
            <b-button
              v-if="INTERNAL_UUID !== CURRENT_EDITOR"
              variant="warning"
              :disabled="!CAN_REQUEST_EDIT"
              @click="requestEdit"
            >
              Edit
            </b-button>
            <b-button
              v-if="INTERNAL_UUID !== CURRENT_EDITOR"
              variant="warning"
              :disabled="!CAN_REQUEST_EDIT"
              @click="requestCutEdit"
            >
              Cuts
            </b-button>
            <b-button
              v-else
              variant="warning"
              :disabled="savingInProgress || isAutoSaving"
              @click="stopEditing"
            >
              Stop Editing
            </b-button>
            <b-button
              v-if="INTERNAL_UUID === CURRENT_EDITOR"
              variant="success"
              :disabled="!canSave && !isAutoSaving"
              @click="saveScript"
            >
              Save
            </b-button>
            <b-button
              v-if="canEdit && !IS_CUT_MODE"
              :variant="bulkEditMode ? 'info' : 'outline-info'"
              @click="bulkEditMode ? exitBulkEditMode() : enterBulkEditMode()"
            >
              {{ bulkEditMode ? 'Exit Bulk Edit' : 'Bulk Edit' }}
            </b-button>
          </b-button-group>
        </b-col>
      </b-row>
      <b-row class="script-row">
        <b-col cols="1"> Act </b-col>
        <b-col cols="1"> Scene </b-col>
        <b-col>Line</b-col>
        <b-col cols="1" />
      </b-row>
    </div>
    <hr />
    <b-row class="script-row">
      <b-col cols="12">
        <template v-for="(line, index) in TMP_SCRIPT[currentEditPage]">
          <template v-if="!DELETED_LINES(currentEditPage).includes(index)">
            <script-line-editor
              v-if="editPages.includes(`page_${currentEditPage}_line_${index}`)"
              :key="`page_${currentEditPage}_line_${index}`"
              :line-index="index"
              :current-edit-page="currentEditPage"
              :acts="ACT_LIST"
              :scenes="SCENE_LIST"
              :characters="CHARACTER_LIST"
              :character-groups="CHARACTER_GROUP_LIST"
              :value="TMP_SCRIPT[currentEditPage][index]"
              :previous-line-fn="getPreviousLineForIndex"
              :next-line-fn="getNextLineForIndex"
              :line-type="line.line_type"
              :stage-direction-styles="STAGE_DIRECTION_STYLES"
              @input="lineChange(line, index)"
              @doneEditing="doneEditingLine(currentEditPage, index)"
              @deleteLine="deleteLine(currentEditPage, index)"
            />
            <script-line-viewer
              v-else
              :key="`page_${currentEditPage}_line_${index}`"
              :line-index="index"
              :line="TMP_SCRIPT[currentEditPage][index]"
              :page="TMP_SCRIPT[currentEditPage]"
              :acts="ACT_LIST"
              :scenes="SCENE_LIST"
              :characters="CHARACTER_LIST"
              :character-groups="CHARACTER_GROUP_LIST"
              :previous-line="TMP_SCRIPT[currentEditPage][index - 1]"
              :can-edit="canEdit"
              :line-part-cuts="linePartCuts"
              :stage-direction-styles="STAGE_DIRECTION_STYLES"
              :stage-direction-style-overrides="STAGE_DIRECTION_STYLE_OVERRIDES"
              :bulk-edit-mode="bulkEditMode"
              :is-bulk-start="isBulkStart(index)"
              :is-bulk-end="isBulkEnd(index)"
              @editLine="beginEditingLine(currentEditPage, index)"
              @cutLinePart="cutLinePart"
              @insertDialogue="insertDialogueAt(currentEditPage, index)"
              @insertStageDirection="insertStageDirectionAt(currentEditPage, index)"
              @insertCueLine="insertCueLineAt(currentEditPage, index)"
              @insertSpacing="insertSpacingAt(currentEditPage, index)"
              @deleteLine="deleteLine(currentEditPage, index)"
              @set-bulk-start="onSetBulkStart(index)"
              @set-bulk-end="onSetBulkEnd(index)"
            />
          </template>
        </template>
      </b-col>
    </b-row>
    <b-row class="script-row pt-1">
      <b-col cols="10" class="ml-auto">
        <b-button-group v-show="canEdit && !IS_CUT_MODE" style="float: right">
          <b-dropdown
            split
            text="Add Dialogue"
            variant="primary"
            right
            boundary="window"
            @click="addNewLine"
          >
            <b-dropdown-item @click="addStageDirection"> Add Stage Direction </b-dropdown-item>
            <b-dropdown-item @click="addCueLine"> Add Cue Line </b-dropdown-item>
            <b-dropdown-item @click="addSpacing"> Add Spacing </b-dropdown-item>
          </b-dropdown>
        </b-button-group>
      </b-col>
    </b-row>
    <b-modal
      id="save-script"
      ref="save-script"
      title="Saving Script"
      size="md"
      :hide-header-close="savingInProgress"
      :hide-footer="savingInProgress"
      :no-close-on-backdrop="savingInProgress"
      :no-close-on-esc="savingInProgress"
    >
      <div>
        <b v-if="savingInProgress">Saving page {{ curSavePage }} of {{ totalSavePages }}</b>
        <template v-else>
          <b v-if="saveError">Could not save script changes.</b>
          <b v-else>Finished saving script.</b>
        </template>
      </div>
      <div>
        <b-progress
          :value="curSavePage"
          :max="totalSavePages"
          :variant="saveProgressVariant"
          show-value
          animated
        />
      </div>
    </b-modal>
    <bulk-act-scene-modal
      :previous-line-of-start="previousLineOfStart"
      :next-line-of-end="nextLineOfEnd"
      :acts="ACT_LIST"
      :scenes="SCENE_LIST"
      @apply="onBulkApply"
    />
    <b-modal
      id="go-to-page-script-editor"
      ref="go-to-page-script-editor"
      title="Go to Page"
      size="sm"
      :hide-header-close="changingPage"
      :hide-footer="changingPage"
      :no-close-on-backdrop="changingPage"
      :no-close-on-esc="changingPage"
      @ok="goToPage"
    >
      <b-form @submit.stop.prevent="">
        <b-form-group id="page-input-group" label="Page" label-for="page-input" label-cols="auto">
          <b-form-input
            id="page-input"
            v-model="$v.pageInputFormState.pageNo.$model"
            name="page-input"
            type="number"
            :state="validatePageState('pageNo')"
            aria-describedby="page-feedback"
          />
          <b-form-invalid-feedback id="page-feedback">
            This is a required field, and must be greater than 0.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
  <b-container v-else class="mx-0 px-0 script-editor-container" fluid>
    <b-row>
      <b-col>
        <div class="text-center py-5">
          <b-spinner label="Loading" />
        </div>
      </b-col>
    </b-row>
  </b-container>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters, mapMutations, mapActions } from 'vuex';
import { required, minValue } from 'vuelidate/lib/validators';
import { diff } from 'deep-object-diff';
import log from 'loglevel';
import { sample } from 'lodash';

import BulkActSceneModal from '@/vue_components/show/config/script/BulkActSceneModal.vue';
import ScriptLineEditor from '@/vue_components/show/config/script/ScriptLineEditor.vue';
import ScriptLineViewer from '@/vue_components/show/config/script/ScriptLineViewer.vue';
import { makeURL, randInt } from '@/js/utils';
import { notNull, notNullAndGreaterThanZero } from '@/js/customValidators';
import { LINE_TYPES } from '@/constants/lineTypes';

const MRU_LOOK_BACK = 4;

export default defineComponent({
  name: 'ScriptConfig',
  components: { BulkActSceneModal, ScriptLineViewer, ScriptLineEditor },
  data() {
    return {
      currentEditPage: 1,
      editPages: [] as string[],
      blankLineObj: {
        id: null,
        act_id: null,
        scene_id: null,
        page: null,
        line_type: LINE_TYPES.DIALOGUE,
        line_parts: [],
        stage_direction_style_id: null,
      },
      curSavePage: null as number | null,
      totalSavePages: null as number | null,
      savingInProgress: false,
      saveError: false,
      currentMaxPage: 1,
      pageInputFormState: {
        pageNo: 1,
      },
      changingPage: false,
      loaded: false,
      latestAddedLine: null as string | null,
      linePartCuts: [] as number[],
      autoSaveInterval: null as ReturnType<typeof setInterval> | null,
      isAutoSaving: false,
      navbarHeight: 0,
      bulkEditMode: false,
      bulkEditStart: null as { page: number; lineIndex: number } | null,
      bulkEditEnd: null as { page: number; lineIndex: number } | null,
      previousLineOfStart: null as any,
      nextLineOfEnd: null as any,
    };
  },
  validations: {
    pageInputFormState: {
      pageNo: {
        required,
        notNull,
        notNullAndGreaterThanZero,
        minValue: minValue(1),
      },
    },
  },
  computed: {
    currentEditPageKey(): string {
      return this.currentEditPage.toString();
    },
    scriptChanges(): boolean {
      if ((this as any).IS_CUT_MODE) {
        return Object.keys(diff((this as any).SCRIPT_CUTS, this.linePartCuts)).length > 0;
      }
      let hasChanges = false;
      Object.keys((this as any).TMP_SCRIPT).forEach((pageNo) => {
        const lineDiff = diff(
          (this as any).GET_SCRIPT_PAGE(pageNo),
          (this as any).TMP_SCRIPT[pageNo]
        );
        if (
          Object.keys(lineDiff).length > 0 ||
          (this as any).DELETED_LINES(pageNo).length > 0 ||
          (this as any).INSERTED_LINES(pageNo).length > 0
        ) {
          hasChanges = true;
        }
      });
      return hasChanges;
    },
    saveProgressVariant(): string {
      if (!this.savingInProgress) {
        return this.saveError ? 'danger' : 'success';
      }
      return 'primary';
    },
    canEdit(): boolean {
      return (this as any).INTERNAL_UUID === (this as any).CURRENT_EDITOR;
    },
    canSave(): boolean {
      if ((this as any).IS_CUT_MODE) {
        return this.scriptChanges;
      }
      return this.scriptChanges && this.editPages.length === 0;
    },
    pagesWithOpenChanges(): number[] {
      return [...new Set(this.editPages.map((x) => parseInt(x.split('_')[1], 10)))];
    },
    ...mapGetters([
      'CURRENT_SHOW',
      'TMP_SCRIPT',
      'ACT_LIST',
      'SCENE_LIST',
      'CHARACTER_LIST',
      'CHARACTER_GROUP_LIST',
      'CAN_REQUEST_EDIT',
      'CURRENT_EDITOR',
      'INTERNAL_UUID',
      'GET_SCRIPT_PAGE',
      'DELETED_LINES',
      'SCENE_BY_ID',
      'ACT_BY_ID',
      'IS_CUT_MODE',
      'SCRIPT_CUTS',
      'INSERTED_LINES',
      'STAGE_DIRECTION_STYLES',
      'CURRENT_USER',
      'STAGE_DIRECTION_STYLE_OVERRIDES',
      'USER_SETTINGS',
      'IS_SCRIPT_EDITOR',
    ]),
  },
  watch: {
    currentEditPage(val: number): void {
      localStorage.setItem('scriptEditPage', val.toString());
    },
    async bulkEditEnd(val: { page: number; lineIndex: number } | null): Promise<void> {
      if (val != null) {
        await this.loadBoundaryLines();
        (this as any).$bvModal.show('bulk-act-scene-modal');
      }
    },
    USER_SETTINGS(): void {
      this.setupAutoSave();
    },
    CURRENT_EDITOR(): void {
      this.setupAutoSave();
    },
  },
  async beforeMount(): Promise<void> {
    await Promise.all([
      (this as any)
        .GET_CURRENT_USER()
        .then(() => (this as any).GET_USER_SETTINGS())
        .then(() => {
          if ((this as any).CURRENT_USER != null) {
            return Promise.all([
              (this as any).GET_STAGE_DIRECTION_STYLE_OVERRIDES(),
              (this as any).GET_CUE_COLOUR_OVERRIDES(),
            ]);
          }
          return Promise.resolve();
        }),
      (this as any).GET_SCRIPT_CONFIG_STATUS(),
      (this as any).GET_ACT_LIST(),
      (this as any).GET_SCENE_LIST(),
      (this as any).GET_CHARACTER_LIST(),
      (this as any).GET_CHARACTER_GROUP_LIST(),
      (this as any).GET_STAGE_DIRECTION_STYLES(),
      (this as any).GET_CUTS(),
      this.getMaxScriptPage(),
    ]);

    // Handle script cuts (depends on GET_CUTS completing)
    this.resetCutsToSaved();

    // Initialisation of page data
    const storedPage = localStorage.getItem('scriptEditPage');
    if (storedPage != null) {
      this.currentEditPage = parseInt(storedPage, 10);
    }
    await this.goToPageInner(this.currentEditPage);
  },
  mounted(): void {
    this.loaded = true;
    this.calculateNavbarHeight();
  },
  created(): void {
    window.addEventListener('resize', this.calculateNavbarHeight);
  },
  destroyed(): void {
    window.removeEventListener('resize', this.calculateNavbarHeight);
    if (this.autoSaveInterval != null) {
      clearInterval(this.autoSaveInterval);
    }
  },
  methods: {
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
    requestEdit(): void {
      (this as any).$socket.sendObj({
        OP: 'REQUEST_SCRIPT_EDIT',
        DATA: {},
      });
    },
    requestCutEdit(): void {
      (this as any).SET_CUT_MODE(true);
      (this as any).$socket.sendObj({
        OP: 'REQUEST_SCRIPT_EDIT',
        DATA: {},
      });
    },
    resetCutsToSaved(): void {
      this.linePartCuts = JSON.parse(JSON.stringify((this as any).SCRIPT_CUTS));
    },
    async stopEditing(): Promise<void> {
      if (this.scriptChanges) {
        const msg =
          'Are you sure you want to stop editing the script? ' +
          'This will cause all unsaved changes to be lost';
        const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
        if (action === false) {
          return;
        }
      }
      this.editPages = [];
      this.exitBulkEditMode();
      (this as any).RESET_TO_SAVED(this.currentEditPage);
      this.resetCutsToSaved();
      (this as any).$socket.sendObj({
        OP: 'STOP_SCRIPT_EDIT',
        DATA: {},
      });
      (this as any).SET_CUT_MODE(false);
    },
    async decrPage(): Promise<void> {
      if (this.currentEditPage > 1) {
        const targetPage = this.currentEditPage - 1;
        // Load from backend if not in buffer
        if (!Object.keys((this as any).TMP_SCRIPT).includes(targetPage.toString())) {
          await (this as any).LOAD_SCRIPT_PAGE(targetPage);
          (this as any).ADD_BLANK_PAGE(targetPage);
        }
        if ((this as any).TMP_SCRIPT[this.currentEditPageKey].length === 0) {
          (this as any).REMOVE_PAGE(this.currentEditPage);
        }
        this.currentEditPage--;

        // Pre-load previous page
        await (this as any).LOAD_SCRIPT_PAGE(this.currentEditPage - 1);
      }
    },
    async incrPage(): Promise<void> {
      this.currentEditPage++;
      if (!Object.keys((this as any).TMP_SCRIPT).includes(this.currentEditPageKey)) {
        (this as any).ADD_BLANK_PAGE(this.currentEditPage);
      }
      // Pre-load next page
      await (this as any).LOAD_SCRIPT_PAGE(this.currentEditPage + 1);
    },
    async addNewLine(): Promise<void> {
      (this as any).ADD_BLANK_LINE({
        pageNo: this.currentEditPage,
        lineObj: this.blankLineObj,
      });
      const lineIndex = (this as any).TMP_SCRIPT[this.currentEditPageKey].length - 1;
      const lineIdent = `page_${this.currentEditPage}_line_${lineIndex}`;
      this.editPages.push(lineIdent);
      this.latestAddedLine = lineIdent;
      const prevLine = await this.getPreviousLineForIndex(lineIndex);
      if (prevLine != null) {
        (this as any).TMP_SCRIPT[this.currentEditPageKey][lineIndex].act_id = prevLine.act_id;
        (this as any).TMP_SCRIPT[this.currentEditPageKey][lineIndex].scene_id = prevLine.scene_id;
      }
    },
    async addStageDirection(): Promise<void> {
      const stageDirectionObject = JSON.parse(JSON.stringify(this.blankLineObj));
      stageDirectionObject.line_type = LINE_TYPES.STAGE_DIRECTION;
      (this as any).ADD_BLANK_LINE({
        pageNo: this.currentEditPage,
        lineObj: stageDirectionObject,
      });
      const lineIndex = (this as any).TMP_SCRIPT[this.currentEditPageKey].length - 1;
      this.editPages.push(`page_${this.currentEditPage}_line_${lineIndex}`);
      const prevLine = await this.getPreviousLineForIndex(lineIndex);
      if (prevLine != null) {
        (this as any).TMP_SCRIPT[this.currentEditPageKey][lineIndex].act_id = prevLine.act_id;
        (this as any).TMP_SCRIPT[this.currentEditPageKey][lineIndex].scene_id = prevLine.scene_id;
      }
    },
    async addCueLine(): Promise<void> {
      const cueLineObject = JSON.parse(JSON.stringify(this.blankLineObj));
      cueLineObject.line_type = LINE_TYPES.CUE_LINE;
      cueLineObject.line_parts = [];
      (this as any).ADD_BLANK_LINE({
        pageNo: this.currentEditPage,
        lineObj: cueLineObject,
      });
      const lineIndex = (this as any).TMP_SCRIPT[this.currentEditPageKey].length - 1;
      this.editPages.push(`page_${this.currentEditPage}_line_${lineIndex}`);
      const prevLine = await this.getPreviousLineForIndex(lineIndex);
      if (prevLine != null) {
        (this as any).TMP_SCRIPT[this.currentEditPageKey][lineIndex].act_id = prevLine.act_id;
        (this as any).TMP_SCRIPT[this.currentEditPageKey][lineIndex].scene_id = prevLine.scene_id;
      }
    },
    async addSpacing(): Promise<void> {
      const spacingObject = JSON.parse(JSON.stringify(this.blankLineObj));
      spacingObject.line_type = LINE_TYPES.SPACING;
      spacingObject.line_parts = [];
      (this as any).ADD_BLANK_LINE({
        pageNo: this.currentEditPage,
        lineObj: spacingObject,
      });
      const lineIndex = (this as any).TMP_SCRIPT[this.currentEditPageKey].length - 1;
      this.editPages.push(`page_${this.currentEditPage}_line_${lineIndex}`);
      const prevLine = await this.getPreviousLineForIndex(lineIndex);
      if (prevLine != null) {
        (this as any).TMP_SCRIPT[this.currentEditPageKey][lineIndex].act_id = prevLine.act_id;
        (this as any).TMP_SCRIPT[this.currentEditPageKey][lineIndex].scene_id = prevLine.scene_id;
      }
    },
    async getPreviousLineForIndex(lineIndex: number): Promise<any> {
      // Search backwards from lineIndex - 1 on the current page, skipping deleted lines
      for (let i = lineIndex - 1; i >= 0; i--) {
        if (!(this as any).DELETED_LINES(this.currentEditPage).includes(i)) {
          return (this as any).TMP_SCRIPT[this.currentEditPage][i];
        }
      }

      // No non-deleted lines before this index on current page, check previous pages
      if (this.currentEditPage > 1) {
        let loopPageNo = this.currentEditPage - 1;

        while (loopPageNo >= 1) {
          let loopPage = null;
          if (Object.keys((this as any).TMP_SCRIPT).includes(loopPageNo.toString())) {
            loopPage = (this as any).TMP_SCRIPT[loopPageNo.toString()];
          } else {
            await (this as any).LOAD_SCRIPT_PAGE(loopPageNo);
            loopPage = (this as any).GET_SCRIPT_PAGE(loopPageNo);
          }
          // Find the last non-deleted line on this page
          const deletedLines = (this as any).DELETED_LINES(loopPageNo);
          for (let i = loopPage.length - 1; i >= 0; i--) {
            if (!deletedLines.includes(i)) {
              return loopPage[i];
            }
          }
          loopPageNo -= 1;
        }
      }
      return null;
    },
    async getNextLineForIndex(lineIndex: number): Promise<any> {
      // Search forwards from lineIndex + 1 on the current page, skipping deleted lines
      const currentPageLines = (this as any).TMP_SCRIPT[this.currentEditPage];
      const deletedLines = (this as any).DELETED_LINES(this.currentEditPage);
      for (let i = lineIndex + 1; i < currentPageLines.length; i++) {
        if (!deletedLines.includes(i)) {
          return currentPageLines[i];
        }
      }

      // No non-deleted lines after this index on current page, check next pages
      // See if there are any edit pages loaded which are after this page
      const editPages = Object.keys((this as any).TMP_SCRIPT)
        .map((x) => parseInt(x, 10))
        .sort();
      for (let i = 0; i < editPages.length; i++) {
        const editPage = editPages[i];
        if (editPage > this.currentEditPage) {
          const pageContent = (this as any).TMP_SCRIPT[editPage.toString()];
          const pageDeletedLines = (this as any).DELETED_LINES(editPage);
          // Find the first non-deleted line on this page
          for (let j = 0; j < pageContent.length; j++) {
            if (!pageDeletedLines.includes(j)) {
              return pageContent[j];
            }
          }
        }
      }

      // Edit pages do not have any non-deleted lines, try loading script pages up to the max

      for (let i = this.currentEditPage + 1; i <= this.currentMaxPage; i++) {
        await (this as any).LOAD_SCRIPT_PAGE(i);
        const loopPage = (this as any).GET_SCRIPT_PAGE(i);
        const loopPageDeletedLines = (this as any).DELETED_LINES(i);
        // Find the first non-deleted line on this page
        for (let j = 0; j < loopPage.length; j++) {
          if (!loopPageDeletedLines.includes(j)) {
            return loopPage[j];
          }
        }
      }

      return null;
    },
    lineChange(line: any, index: number): void {
      (this as any).SET_LINE({
        pageNo: this.currentEditPage,
        lineIndex: index,
        lineObj: line,
      });
    },
    beginEditingLine(pageIndex: number, lineIndex: number): void {
      const index = this.editPages.indexOf(`page_${pageIndex}_line_${lineIndex}`);
      if (index === -1) {
        this.editPages.push(`page_${pageIndex}_line_${lineIndex}`);
      }
    },
    doneEditingLine(pageIndex: number, lineIndex: number): void {
      const lineIdent = `page_${pageIndex}_line_${lineIndex}`;
      const index = this.editPages.indexOf(lineIdent);
      if (index !== -1) {
        this.editPages.splice(index, 1);
      }
      if (this.latestAddedLine === lineIdent) {
        this.addNewLine();
      }
    },
    deleteLine(pageIndex: number, lineIndex: number): void {
      if (this.latestAddedLine === `page_${pageIndex}_line_${lineIndex}`) {
        this.latestAddedLine = null;
      }
      (this as any).DELETE_LINE({
        pageNo: pageIndex,
        lineIndex,
      });
      this.doneEditingLine(pageIndex, lineIndex);

      this.editPages.forEach((editPage, index) => {
        const editParts = editPage.split('_');
        const editPageIndex = parseInt(editParts[1], 10);
        const editIndex = parseInt(editParts[3], 10);
        if (editPageIndex === pageIndex && editIndex >= lineIndex) {
          this.editPages[index] = `page_${editPageIndex}_line_${editIndex - 1}`;
        }
      });

      if (this.latestAddedLine != null) {
        const editParts = this.latestAddedLine.split('_');
        const editPageIndex = parseInt(editParts[1], 10);
        const editIndex = parseInt(editParts[3], 10);
        if (editPageIndex === pageIndex && editIndex >= lineIndex) {
          this.latestAddedLine = `page_${pageIndex}_line_${editIndex - 1}`;
        }
      }
    },
    cutLinePart(linePartId: number): void {
      const index = this.linePartCuts.indexOf(linePartId);
      if (index === -1) {
        this.linePartCuts.push(linePartId);
      } else {
        this.linePartCuts.splice(index, 1);
      }
    },
    async insertLineAt(pageIndex: number, lineIndex: number, lineType: number): Promise<void> {
      // Map line types to their corresponding add methods
      const addMethodMap: Record<number, () => Promise<void>> = {
        [LINE_TYPES.DIALOGUE]: () => this.addNewLine(),
        [LINE_TYPES.STAGE_DIRECTION]: () => this.addStageDirection(),
        [LINE_TYPES.CUE_LINE]: () => this.addCueLine(),
        [LINE_TYPES.SPACING]: () => this.addSpacing(),
      };

      // If we're inserting at the end of the page, use the add method instead
      if ((this as any).TMP_SCRIPT[pageIndex].length - 1 === lineIndex) {
        await addMethodMap[lineType]();
        return;
      }

      // Create new line object with appropriate configuration
      const newLineIndex = lineIndex + 1;
      const newLineObject = JSON.parse(JSON.stringify(this.blankLineObj));
      newLineObject.line_type = lineType;

      // CUE_LINE and SPACING types need empty line_parts array
      if (lineType === LINE_TYPES.CUE_LINE || lineType === LINE_TYPES.SPACING) {
        newLineObject.line_parts = [];
      }

      // Insert the blank line
      (this as any).INSERT_BLANK_LINE({
        pageNo: this.currentEditPage,
        lineIndex: newLineIndex,
        lineObj: newLineObject,
      });

      // Update existing edit page indices
      this.editPages.forEach((editPage, index) => {
        const editParts = editPage.split('_');
        const editPageIndex = parseInt(editParts[1], 10);
        const editIndex = parseInt(editParts[3], 10);
        if (editPageIndex === pageIndex && editIndex >= newLineIndex) {
          this.editPages[index] = `page_${editPageIndex}_line_${editIndex + 1}`;
        }
      });

      // Add new line to edit pages
      const lineIdent = `page_${this.currentEditPage}_line_${newLineIndex}`;
      this.editPages.push(lineIdent);

      // Inherit act and scene from previous line
      const prevLine = await this.getPreviousLineForIndex(newLineIndex);
      if (prevLine != null) {
        (this as any).TMP_SCRIPT[this.currentEditPageKey][newLineIndex].act_id = prevLine.act_id;
        (this as any).TMP_SCRIPT[this.currentEditPageKey][newLineIndex].scene_id =
          prevLine.scene_id;
      }
    },
    async insertDialogueAt(pageIndex: number, lineIndex: number): Promise<void> {
      await this.insertLineAt(pageIndex, lineIndex, LINE_TYPES.DIALOGUE);
    },
    async insertStageDirectionAt(pageIndex: number, lineIndex: number): Promise<void> {
      await this.insertLineAt(pageIndex, lineIndex, LINE_TYPES.STAGE_DIRECTION);
    },
    async insertCueLineAt(pageIndex: number, lineIndex: number): Promise<void> {
      await this.insertLineAt(pageIndex, lineIndex, LINE_TYPES.CUE_LINE);
    },
    async insertSpacingAt(pageIndex: number, lineIndex: number): Promise<void> {
      await this.insertLineAt(pageIndex, lineIndex, LINE_TYPES.SPACING);
    },
    async saveScript(): Promise<void> {
      if (!(this as any).IS_CUT_MODE) {
        if (this.scriptChanges) {
          this.savingInProgress = true;
          const tmpPageKeys = Object.keys((this as any).TMP_SCRIPT).map((x) =>
            Number.parseInt(x, 10)
          );
          const maxPage = Math.max(this.currentMaxPage, ...tmpPageKeys, 0);
          this.totalSavePages = maxPage;
          this.curSavePage = 0;
          (this as any).$bvModal.show('save-script');

          for (let pageNo = 1; pageNo <= maxPage; pageNo++) {
            this.curSavePage = pageNo;
            const tmpScriptPage = (this as any).TMP_SCRIPT[pageNo.toString()];
            if (!tmpScriptPage) continue;
            // Check whether the page actually has any lines on it, and if not then skip
            if (tmpScriptPage.length !== 0) {
              // Check the actual script to see if the page exists or not
              const actualScriptPage = (this as any).GET_SCRIPT_PAGE(pageNo);
              if (actualScriptPage.length === 0) {
                // New page
                const response = await (this as any).SAVE_NEW_PAGE(pageNo);
                if (response) {
                  await (this as any).LOAD_SCRIPT_PAGE(pageNo);
                  (this as any).ADD_BLANK_PAGE(pageNo);
                  (this as any).RESET_DELETED(pageNo);
                  (this as any).RESET_INSERTED(pageNo);
                } else {
                  (this as any).$toast.error('Unable to save script. Please try again.');
                  this.saveError = true;
                  break;
                }
              } else {
                // Existing page, check if anything has changed before saving
                const lineDiff = diff(actualScriptPage, tmpScriptPage);
                if (
                  Object.keys(lineDiff).length > 0 ||
                  (this as any).DELETED_LINES(pageNo).length > 0 ||
                  (this as any).INSERTED_LINES(pageNo).length > 0
                ) {
                  const response = await (this as any).SAVE_CHANGED_PAGE(pageNo);
                  if (response) {
                    await (this as any).LOAD_SCRIPT_PAGE(pageNo);
                    (this as any).ADD_BLANK_PAGE(pageNo);
                    (this as any).RESET_DELETED(pageNo);
                    (this as any).RESET_INSERTED(pageNo);
                  } else {
                    (this as any).$toast.error('Unable to save script. Please try again.');
                    this.saveError = true;
                    break;
                  }
                }
              }
            }
          }

          this.savingInProgress = false;
          // Re-setup autosave (to reset the timer since we have just saved)
          this.setupAutoSave();
        } else {
          (this as any).$toast.warning('No changes to save!');
        }
        await this.getMaxScriptPage();
      } else {
        this.savingInProgress = true;
        await (this as any).SAVE_SCRIPT_CUTS(this.linePartCuts);
        this.resetCutsToSaved();
        // Re-setup autosave (to reset the timer since we have just saved)
        this.setupAutoSave();
        this.savingInProgress = false;
      }
    },
    validatePageState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.pageInputFormState[name];
      return $dirty ? !$error : null;
    },
    async goToPage(): Promise<void> {
      this.changingPage = true;
      await this.goToPageInner(this.pageInputFormState.pageNo);
      this.changingPage = false;
    },
    async goToPageInner(pageNo: number): Promise<void> {
      const loadedPages = new Set(Object.keys((this as any).TMP_SCRIPT).map(Number));
      const lookBackStart = Math.max(1, pageNo - MRU_LOOK_BACK);
      for (let p = lookBackStart; p < pageNo; p++) {
        if (!loadedPages.has(p)) {
          await (this as any).LOAD_SCRIPT_PAGE(p);
          (this as any).ADD_BLANK_PAGE(p);
        }
      }
      await (this as any).LOAD_SCRIPT_PAGE(pageNo);
      this.currentEditPage = pageNo;
      if (!Object.keys((this as any).TMP_SCRIPT).includes(this.currentEditPageKey)) {
        (this as any).ADD_BLANK_PAGE(this.currentEditPage);
      }
      await (this as any).LOAD_SCRIPT_PAGE(pageNo + 1);
    },
    setupAutoSave(): void {
      const autoSaveInterval = Math.max(
        (this as any).USER_SETTINGS.script_auto_save_interval * 1000 * 60,
        1000 * 60
      );
      if (
        (this as any).INTERNAL_UUID !== (this as any).CURRENT_EDITOR &&
        this.autoSaveInterval != null
      ) {
        clearInterval(this.autoSaveInterval);
      } else if ((this as any).INTERNAL_UUID === (this as any).CURRENT_EDITOR) {
        if ((this as any).USER_SETTINGS.enable_script_auto_save) {
          if (this.autoSaveInterval == null) {
            this.autoSaveInterval = setInterval(this.autosave, autoSaveInterval);
          } else {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = setInterval(this.autosave, autoSaveInterval);
          }
        } else if (this.autoSaveInterval != null) {
          clearInterval(this.autoSaveInterval);
        }
      }
    },
    async autosave(): Promise<void> {
      if (this.isAutoSaving) {
        return;
      }
      this.isAutoSaving = true;
      const toastInstance = (this as any).$toast.open({
        type: 'info',
        message: 'Performing autosave...',
        duration: 0,
        dismissible: false,
      });
      if (!(this as any).IS_CUT_MODE) {
        if (this.scriptChanges) {
          let curSavePage = 0;
          const orderedPages = Object.keys((this as any).TMP_SCRIPT)
            .map((x) => parseInt(x, 10))
            .sort((a, b) => a - b);
          let saveFailure = false;

          for (const pageNo of orderedPages) {
            curSavePage = pageNo;
            // If the page we are trying to save currently has edits, then stop
            // here as we cannot save further changes (ordering is important, so if we have open
            // edits on line X, then pages Y > X depend on the changes from X being saved
            if (this.pagesWithOpenChanges.includes(pageNo)) {
              break;
            }
            toastInstance.message = `Performing autosave...<br>Saving page ${curSavePage}`;
            // Check whether the page actually has any lines on it, and if not then skip
            const tmpScriptPage = (this as any).TMP_SCRIPT[pageNo.toString()];
            if (tmpScriptPage.length !== 0) {
              // Check the actual script to see if the page exists or not
              const actualScriptPage = (this as any).GET_SCRIPT_PAGE(pageNo);
              if (actualScriptPage.length === 0) {
                // New page
                const response = await (this as any).SAVE_NEW_PAGE(pageNo);
                if (response) {
                  await (this as any).LOAD_SCRIPT_PAGE(pageNo);
                  (this as any).ADD_BLANK_PAGE(pageNo);
                  (this as any).RESET_DELETED(pageNo);
                  (this as any).RESET_INSERTED(pageNo);
                } else {
                  saveFailure = true;
                  break;
                }
              } else {
                // Existing page, check if anything has changed before saving
                const lineDiff = diff(actualScriptPage, tmpScriptPage);
                if (
                  Object.keys(lineDiff).length > 0 ||
                  (this as any).DELETED_LINES(pageNo).length > 0 ||
                  (this as any).INSERTED_LINES(pageNo).length > 0
                ) {
                  const response = await (this as any).SAVE_CHANGED_PAGE(pageNo);
                  if (response) {
                    await (this as any).LOAD_SCRIPT_PAGE(pageNo);
                    (this as any).ADD_BLANK_PAGE(pageNo);
                    (this as any).RESET_DELETED(pageNo);
                    (this as any).RESET_INSERTED(pageNo);
                  } else {
                    saveFailure = true;
                    break;
                  }
                }
              }
            }
          }

          if (saveFailure) {
            toastInstance.message = 'Autosave failed.';
            toastInstance.type = 'danger';
          } else {
            toastInstance.message = `Autosave successful<br>Saved up to page ${curSavePage}`;
            toastInstance.type = 'success';
          }
          setTimeout(() => toastInstance.dismiss(), 5000);
        } else {
          toastInstance.message = 'Autosave successful<br>No changes to save';
          toastInstance.type = 'success';
          setTimeout(() => toastInstance.dismiss(), 5000);
        }
        await this.getMaxScriptPage();
      } else {
        await (this as any).SAVE_SCRIPT_CUTS(this.linePartCuts);
        this.resetCutsToSaved();
        toastInstance.message = 'Autosave successful';
        toastInstance.type = 'success';
        setTimeout(() => toastInstance.dismiss(), 5000);
      }
      this.isAutoSaving = false;
    },
    calculateNavbarHeight(): void {
      const navbar = document.querySelector('.navbar');
      if (navbar) {
        this.navbarHeight = (navbar as HTMLElement).offsetHeight;
      } else {
        this.navbarHeight = 56;
      }
    },
    enterBulkEditMode(): void {
      this.bulkEditMode = true;
      this.bulkEditStart = null;
      this.bulkEditEnd = null;
    },
    exitBulkEditMode(): void {
      this.bulkEditMode = false;
      this.bulkEditStart = null;
      this.bulkEditEnd = null;
      this.previousLineOfStart = null;
      this.nextLineOfEnd = null;
    },
    onSetBulkStart(index: number): void {
      this.bulkEditStart = {
        page: this.currentEditPage,
        lineIndex: index,
      };
      this.bulkEditEnd = null;
    },
    onSetBulkEnd(index: number): void {
      if (this.bulkEditStart != null) {
        const { page: startPage, lineIndex: startIndex } = this.bulkEditStart;
        if (startPage === this.currentEditPage && index <= startIndex) {
          (this as any).$toast.error('End line must come after start line');
          return;
        }
        if (this.currentEditPage < startPage) {
          (this as any).$toast.error('End line must come after start line');
          return;
        }
      }
      this.bulkEditEnd = { page: this.currentEditPage, lineIndex: index };
    },
    isBulkStart(index: number): boolean {
      return (
        this.bulkEditStart != null &&
        this.bulkEditStart.page === this.currentEditPage &&
        this.bulkEditStart.lineIndex === index
      );
    },
    isBulkEnd(index: number): boolean {
      return (
        this.bulkEditEnd != null &&
        this.bulkEditEnd.page === this.currentEditPage &&
        this.bulkEditEnd.lineIndex === index
      );
    },
    async loadBoundaryLines(): Promise<void> {
      const { page: startPage, lineIndex: startIndex } = this.bulkEditStart!;
      const { page: endPage, lineIndex: endIndex } = this.bulkEditEnd!;

      if (startIndex === 0 && startPage > 1) {
        await (this as any).LOAD_SCRIPT_PAGE(startPage - 1);
      }
      const endPageLines = (this as any).TMP_SCRIPT[endPage.toString()];
      if (endPageLines && endIndex === endPageLines.length - 1) {
        await (this as any).LOAD_SCRIPT_PAGE(endPage + 1);
      }

      const startPageLines = (this as any).TMP_SCRIPT[startPage.toString()];
      if (startIndex > 0 && startPageLines) {
        this.previousLineOfStart = startPageLines[startIndex - 1] || null;
      } else if (startPage > 1) {
        const prevPage = (this as any).TMP_SCRIPT[(startPage - 1).toString()];
        this.previousLineOfStart = prevPage ? prevPage[prevPage.length - 1] : null;
      } else {
        this.previousLineOfStart = null;
      }

      const endLines = (this as any).TMP_SCRIPT[endPage.toString()];
      if (endLines && endIndex < endLines.length - 1) {
        this.nextLineOfEnd = endLines[endIndex + 1] || null;
      } else {
        const nextPage = (this as any).TMP_SCRIPT[(endPage + 1).toString()];
        this.nextLineOfEnd = nextPage ? nextPage[0] : null;
      }
    },
    async onBulkApply({ actId, sceneId }: { actId: number; sceneId: number }): Promise<void> {
      const { page: startPage, lineIndex: startIndex } = this.bulkEditStart!;
      const { page: endPage, lineIndex: endIndex } = this.bulkEditEnd!;

      for (let p = startPage; p <= endPage; p++) {
        await (this as any).LOAD_SCRIPT_PAGE(p);
      }

      for (let p = startPage; p <= endPage; p++) {
        const pageLines = (this as any).TMP_SCRIPT[p.toString()];
        if (!pageLines) continue;
        const fromIndex = p === startPage ? startIndex : 0;
        const toIndex = p === endPage ? endIndex : pageLines.length - 1;
        for (let i = fromIndex; i <= toIndex; i++) {
          if ((this as any).DELETED_LINES(p).includes(i)) continue;
          (this as any).SET_LINE({
            pageNo: p,
            lineIndex: i,
            lineObj: { ...pageLines[i], act_id: actId, scene_id: sceneId },
          });
        }
      }

      (this as any).$bvModal.hide('bulk-act-scene-modal');
      this.exitBulkEditMode();
    },
    ...mapMutations([
      'REMOVE_PAGE',
      'ADD_BLANK_LINE',
      'SET_LINE',
      'DELETE_LINE',
      'RESET_DELETED',
      'SET_CUT_MODE',
      'INSERT_BLANK_LINE',
      'RESET_INSERTED',
    ]),
    ...mapActions([
      'GET_SCENE_LIST',
      'GET_ACT_LIST',
      'GET_CHARACTER_LIST',
      'GET_CHARACTER_GROUP_LIST',
      'LOAD_SCRIPT_PAGE',
      'ADD_BLANK_PAGE',
      'GET_SCRIPT_CONFIG_STATUS',
      'RESET_TO_SAVED',
      'SAVE_NEW_PAGE',
      'SAVE_CHANGED_PAGE',
      'GET_CUTS',
      'SAVE_SCRIPT_CUTS',
      'GET_STAGE_DIRECTION_STYLES',
      'GET_CURRENT_USER',
      'GET_STAGE_DIRECTION_STYLE_OVERRIDES',
      'GET_CUE_COLOUR_OVERRIDES',
      'GET_USER_SETTINGS',
    ]),
  },
});
</script>

<style scoped>
.script-editor-container {
  position: relative;
}

.sticky-header {
  position: sticky;
  z-index: 100;
  padding: 10px 0;
  border-bottom: 1px solid #dee2e6;
  background: var(--body-background);
}
</style>
