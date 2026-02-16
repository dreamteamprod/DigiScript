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
            <template v-if="!IS_CURRENT_EDITOR && !IS_CURRENT_CUTTER">
              <span v-b-tooltip.hover="editDisabledReason" class="btn-group-item">
                <b-button variant="warning" :disabled="!CAN_REQUEST_EDIT" @click="requestEdit">
                  Edit
                </b-button>
              </span>
              <span v-b-tooltip.hover="cutsDisabledReason" class="btn-group-item">
                <b-button variant="warning" :disabled="!CAN_REQUEST_CUTS" @click="requestCutEdit">
                  Cuts
                </b-button>
              </span>
            </template>
            <template v-if="IS_CURRENT_EDITOR">
              <b-button
                variant="warning"
                :disabled="savingInProgress || isAutoSaving"
                @click="stopEditing"
              >
                Stop Editing
              </b-button>
              <b-button variant="success" :disabled="!canSave && !isAutoSaving" @click="saveScript">
                Save
              </b-button>
            </template>
            <template v-if="IS_CURRENT_CUTTER">
              <b-button
                variant="warning"
                :disabled="savingInProgress || isAutoSaving"
                @click="stopEditing"
              >
                Stop Cuts
              </b-button>
              <b-button variant="success" :disabled="!canSave && !isAutoSaving" @click="saveScript">
                Save
              </b-button>
            </template>
          </b-button-group>
        </b-col>
      </b-row>
      <b-row v-if="IS_DRAFT_ACTIVE" class="script-row py-1">
        <b-col>
          <collaborator-panel
            :collaborators="DRAFT_COLLABORATORS"
            :awareness-states="DRAFT_AWARENESS_STATES"
          />
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
              :y-line-map="getYLineMap(index)"
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
              :editing-users="editingUsersForLine(index)"
              @editLine="beginEditingLine(currentEditPage, index)"
              @cutLinePart="cutLinePart"
              @insertDialogue="insertDialogueAt(currentEditPage, index)"
              @insertStageDirection="insertStageDirectionAt(currentEditPage, index)"
              @insertCueLine="insertCueLineAt(currentEditPage, index)"
              @insertSpacing="insertSpacingAt(currentEditPage, index)"
              @deleteLine="deleteLine(currentEditPage, index)"
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

<script>
import { mapGetters, mapMutations, mapActions } from 'vuex';
import { required, minValue } from 'vuelidate/lib/validators';
import { diff } from 'deep-object-diff';
import log from 'loglevel';
import { sample } from 'lodash';

import ScriptLineEditor from '@/vue_components/show/config/script/ScriptLineEditor.vue';
import ScriptLineViewer from '@/vue_components/show/config/script/ScriptLineViewer.vue';
import CollaboratorPanel from '@/vue_components/show/config/script/CollaboratorPanel.vue';
import { makeURL, randInt } from '@/js/utils';
import { notNull, notNullAndGreaterThanZero } from '@/js/customValidators';
import { LINE_TYPES } from '@/constants/lineTypes';
import { syncPageFromYDoc, addYDocLine, deleteYDocLine } from '@/utils/yjs/yjsBridge';

export default {
  name: 'ScriptConfig',
  components: { ScriptLineViewer, ScriptLineEditor, CollaboratorPanel },
  data() {
    return {
      currentEditPage: 1,
      editPages: [],
      blankLineObj: {
        id: null,
        act_id: null,
        scene_id: null,
        page: null,
        line_type: LINE_TYPES.DIALOGUE,
        line_parts: [],
        stage_direction_style_id: null,
      },
      curSavePage: null,
      totalSavePages: null,
      savingInProgress: false,
      saveError: false,
      currentMaxPage: 1,
      pageInputFormState: {
        pageNo: 1,
      },
      changingPage: false,
      loaded: false,
      latestAddedLine: null,
      linePartCuts: [],
      autoSaveInterval: null,
      isAutoSaving: false,
      navbarHeight: 0,
      /** @type {Function|null} Deep observer cleanup for Y.Doc pages */
      ydocObserverCleanup: null,
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
    currentEditPageKey() {
      return this.currentEditPage.toString();
    },
    scriptChanges() {
      if (this.IS_CUT_MODE) {
        return Object.keys(diff(this.SCRIPT_CUTS, this.linePartCuts)).length > 0;
      }
      let hasChanges = false;
      Object.keys(this.TMP_SCRIPT).forEach(function checkPageHasChanges(pageNo) {
        const lineDiff = diff(this.GET_SCRIPT_PAGE(pageNo), this.TMP_SCRIPT[pageNo]);
        if (
          Object.keys(lineDiff).length > 0 ||
          this.DELETED_LINES(pageNo).length > 0 ||
          this.INSERTED_LINES(pageNo).length > 0
        ) {
          hasChanges = true;
        }
      }, this);
      return hasChanges;
    },
    saveProgressVariant() {
      if (!this.savingInProgress) {
        return this.saveError ? 'danger' : 'success';
      }
      return 'primary';
    },
    editDisabledReason() {
      if (this.CUTTERS.length > 0) return 'Another user is currently making cuts';
      return '';
    },
    cutsDisabledReason() {
      if (this.EDITORS.length > 0) return 'Another user is currently editing';
      if (this.CUTTERS.length > 0) return 'Another user is currently making cuts';
      if (this.HAS_DRAFT) return 'An unsaved draft exists';
      return '';
    },
    canEdit() {
      return this.IS_CURRENT_EDITOR;
    },
    canSave() {
      if (this.IS_CUT_MODE) {
        return this.scriptChanges;
      }
      return this.scriptChanges && this.editPages.length === 0;
    },
    pagesWithOpenChanges() {
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
      'CAN_REQUEST_CUTS',
      'EDITORS',
      'CUTTERS',
      'HAS_DRAFT',
      'IS_CURRENT_EDITOR',
      'IS_CURRENT_CUTTER',
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
      'CURRENT_REVISION',
      'IS_DRAFT_ACTIVE',
      'IS_DRAFT_SYNCED',
      'DRAFT_YDOC',
      'DRAFT_COLLABORATORS',
      'DRAFT_PROVIDER',
      'DRAFT_LINE_EDITORS',
      'DRAFT_AWARENESS_STATES',
    ]),
  },
  watch: {
    currentEditPage(val) {
      localStorage.setItem('scriptEditPage', val);
    },
    USER_SETTINGS() {
      this.setupAutoSave();
    },
    IS_CURRENT_EDITOR(isEditor) {
      this.setupAutoSave();
      if (isEditor && this.CURRENT_REVISION && !this.IS_DRAFT_ACTIVE) {
        this.JOIN_DRAFT_ROOM({
          revisionId: this.CURRENT_REVISION,
          role: 'editor',
        });
      }
    },
    EDITORS: {
      handler(editors) {
        if (
          editors.length > 0 &&
          !this.IS_CURRENT_EDITOR &&
          !this.IS_DRAFT_ACTIVE &&
          this.CURRENT_REVISION
        ) {
          this.JOIN_DRAFT_ROOM({
            revisionId: this.CURRENT_REVISION,
            role: 'viewer',
          });
        }
      },
      immediate: true,
    },
    IS_DRAFT_ACTIVE(active) {
      if (!active) {
        this.teardownYDocBridge();
        this.RESET_TO_SAVED(this.currentEditPage);
      }
    },
    IS_DRAFT_SYNCED(synced) {
      if (synced) {
        this.setupYDocBridge();
      }
    },
  },
  async mounted() {
    await Promise.all([
      this.GET_CURRENT_USER()
        .then(() => this.GET_USER_SETTINGS())
        .then(() => {
          if (this.CURRENT_USER != null) {
            return Promise.all([
              this.GET_STAGE_DIRECTION_STYLE_OVERRIDES(),
              this.GET_CUE_COLOUR_OVERRIDES(),
            ]);
          }
          return Promise.resolve();
        }),
      this.GET_SCRIPT_REVISIONS(),
      this.GET_SCRIPT_CONFIG_STATUS(),
      this.GET_ACT_LIST(),
      this.GET_SCENE_LIST(),
      this.GET_CHARACTER_LIST(),
      this.GET_CHARACTER_GROUP_LIST(),
      this.GET_STAGE_DIRECTION_STYLES(),
      this.GET_CUTS(),
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

    // All data loaded — now safe to render
    this.loaded = true;
    this.$nextTick(() => this.calculateNavbarHeight());
  },
  created() {
    window.addEventListener('resize', this.calculateNavbarHeight);
  },
  destroyed() {
    window.removeEventListener('resize', this.calculateNavbarHeight);
    if (this.autoSaveInterval != null) {
      clearInterval(this.autoSaveInterval);
    }
    this.teardownYDocBridge();
    this.LEAVE_DRAFT_ROOM();
  },
  methods: {
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
    requestEdit() {
      this.$socket.sendObj({
        OP: 'REQUEST_SCRIPT_EDIT',
        DATA: {},
      });
    },
    requestCutEdit() {
      this.SET_CUT_MODE(true);
      this.$socket.sendObj({
        OP: 'REQUEST_SCRIPT_CUTS',
        DATA: {},
      });
    },
    resetCutsToSaved() {
      this.linePartCuts = JSON.parse(JSON.stringify(this.SCRIPT_CUTS));
    },
    async stopEditing() {
      if (this.IS_CUT_MODE) {
        // Cuts mode: local state, no room involvement
        if (this.scriptChanges) {
          const msg =
            'Are you sure you want to stop editing cuts? ' +
            'This will cause all unsaved changes to be lost';
          const action = await this.$bvModal.msgBoxConfirm(msg, {});
          if (action === false) {
            return;
          }
        }
        this.editPages = [];
        this.RESET_TO_SAVED(this.currentEditPage);
        this.resetCutsToSaved();
        this.$socket.sendObj({ OP: 'STOP_SCRIPT_EDIT', DATA: {} });
        this.SET_CUT_MODE(false);
        return;
      }

      // Collab edit mode: stay in room as viewer
      this.editPages = [];
      this._broadcastAwareness(this.currentEditPage, null);
      this.$socket.sendObj({ OP: 'STOP_SCRIPT_EDIT', DATA: {} });
      // Server downgrades role; IS_CURRENT_EDITOR goes false via GET_SCRIPT_CONFIG_STATUS
      // → canEdit becomes false → UI switches to read-only
      // Y.Doc bridge stays active, TMP_SCRIPT stays populated
    },
    async decrPage() {
      if (this.currentEditPage > 1) {
        const targetPage = this.currentEditPage - 1;
        // Load from backend if not in buffer
        if (!Object.keys(this.TMP_SCRIPT).includes(targetPage.toString())) {
          await this.LOAD_SCRIPT_PAGE(targetPage);
          this.ADD_BLANK_PAGE(targetPage);
        }
        if (this.TMP_SCRIPT[this.currentEditPageKey].length === 0) {
          this.REMOVE_PAGE(this.currentEditPage);
        }
        this.currentEditPage--;

        // Pre-load previous page
        await this.LOAD_SCRIPT_PAGE(this.currentEditPage - 1);
      }
    },
    async incrPage() {
      this.currentEditPage++;
      if (!Object.keys(this.TMP_SCRIPT).includes(this.currentEditPageKey)) {
        this.ADD_BLANK_PAGE(this.currentEditPage);
      }
      // Pre-load next page
      await this.LOAD_SCRIPT_PAGE(this.currentEditPage + 1);
    },
    /**
     * Common logic for all add-line operations.
     * Builds a complete lineObj (with act_id/scene_id inherited), then writes
     * to Y.Doc (collab mode) or TMP_SCRIPT (non-collab mode).
     * @param {number} lineType - LINE_TYPES value
     * @param {boolean} [trackAsLatest=false] - Whether to track as latestAddedLine
     */
    async addLineOfType(lineType, trackAsLatest = false) {
      const lineObj = JSON.parse(JSON.stringify(this.blankLineObj));
      lineObj.line_type = lineType;

      // Determine target index and inherit act_id/scene_id from previous line
      const currentPageLines = this.TMP_SCRIPT[this.currentEditPageKey] || [];
      const prevLine = await this.getPreviousLineForIndex(currentPageLines.length);
      if (prevLine) {
        lineObj.act_id = prevLine.act_id;
        lineObj.scene_id = prevLine.scene_id;
      }

      if (this.IS_DRAFT_ACTIVE && this.DRAFT_YDOC) {
        addYDocLine(this.DRAFT_YDOC, this.currentEditPage, lineObj);
      } else {
        this.ADD_BLANK_LINE({ pageNo: this.currentEditPage, lineObj });
      }

      const lineIndex = this.TMP_SCRIPT[this.currentEditPageKey].length - 1;
      const lineIdent = `page_${this.currentEditPage}_line_${lineIndex}`;
      this.editPages.push(lineIdent);
      this._broadcastAwareness(this.currentEditPage, lineIndex);
      if (trackAsLatest) {
        this.latestAddedLine = lineIdent;
      }
    },
    async addNewLine() {
      await this.addLineOfType(LINE_TYPES.DIALOGUE, true);
    },
    async addStageDirection() {
      await this.addLineOfType(LINE_TYPES.STAGE_DIRECTION);
    },
    async addCueLine() {
      await this.addLineOfType(LINE_TYPES.CUE_LINE);
    },
    async addSpacing() {
      await this.addLineOfType(LINE_TYPES.SPACING);
    },
    async getPreviousLineForIndex(lineIndex) {
      // Search backwards from lineIndex - 1 on the current page, skipping deleted lines
      for (let i = lineIndex - 1; i >= 0; i--) {
        if (!this.DELETED_LINES(this.currentEditPage).includes(i)) {
          return this.TMP_SCRIPT[this.currentEditPage][i];
        }
      }

      // No non-deleted lines before this index on current page, check previous pages
      if (this.currentEditPage > 1) {
        let loopPageNo = this.currentEditPage - 1;

        while (loopPageNo >= 1) {
          let loopPage = null;
          if (Object.keys(this.TMP_SCRIPT).includes(loopPageNo.toString())) {
            loopPage = this.TMP_SCRIPT[loopPageNo.toString()];
          } else {
            await this.LOAD_SCRIPT_PAGE(loopPageNo);
            loopPage = this.GET_SCRIPT_PAGE(loopPageNo);
          }
          // Find the last non-deleted line on this page
          const deletedLines = this.DELETED_LINES(loopPageNo);
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
    async getNextLineForIndex(lineIndex) {
      // Search forwards from lineIndex + 1 on the current page, skipping deleted lines
      const currentPageLines = this.TMP_SCRIPT[this.currentEditPage];
      const deletedLines = this.DELETED_LINES(this.currentEditPage);
      for (let i = lineIndex + 1; i < currentPageLines.length; i++) {
        if (!deletedLines.includes(i)) {
          return currentPageLines[i];
        }
      }

      // No non-deleted lines after this index on current page, check next pages
      // See if there are any edit pages loaded which are after this page
      const editPages = Object.keys(this.TMP_SCRIPT)
        .map((x) => parseInt(x, 10))
        .sort();
      for (let i = 0; i < editPages.length; i++) {
        const editPage = editPages[i];
        if (editPage > this.currentEditPage) {
          const pageContent = this.TMP_SCRIPT[editPage.toString()];
          const pageDeletedLines = this.DELETED_LINES(editPage);
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
        await this.LOAD_SCRIPT_PAGE(i);
        const loopPage = this.GET_SCRIPT_PAGE(i);
        const loopPageDeletedLines = this.DELETED_LINES(i);
        // Find the first non-deleted line on this page
        for (let j = 0; j < loopPage.length; j++) {
          if (!loopPageDeletedLines.includes(j)) {
            return loopPage[j];
          }
        }
      }

      return null;
    },
    lineChange(line, index) {
      if (this.IS_DRAFT_ACTIVE && this.DRAFT_YDOC) {
        // Y.Doc is source of truth — components wrote directly to Y.Map/Y.Text.
        // The deep observer handles TMP_SCRIPT updates synchronously.
        return;
      }
      // Non-collab mode: write to TMP_SCRIPT as before
      this.SET_LINE({
        pageNo: this.currentEditPage,
        lineIndex: index,
        lineObj: line,
      });
    },
    beginEditingLine(pageIndex, lineIndex) {
      const index = this.editPages.indexOf(`page_${pageIndex}_line_${lineIndex}`);
      if (index === -1) {
        this.editPages.push(`page_${pageIndex}_line_${lineIndex}`);
      }
      this._broadcastAwareness(pageIndex, lineIndex);
    },
    doneEditingLine(pageIndex, lineIndex) {
      const lineIdent = `page_${pageIndex}_line_${lineIndex}`;
      const index = this.editPages.indexOf(lineIdent);
      if (index !== -1) {
        this.editPages.splice(index, 1);
      }
      this._broadcastAwareness(pageIndex, null);
      if (this.latestAddedLine === lineIdent) {
        this.addNewLine();
      }
    },
    deleteLine(pageIndex, lineIndex) {
      if (this.latestAddedLine === `page_${pageIndex}_line_${lineIndex}`) {
        this.latestAddedLine = null;
      }
      if (this.IS_DRAFT_ACTIVE && this.DRAFT_YDOC) {
        deleteYDocLine(this.DRAFT_YDOC, pageIndex, lineIndex);
      } else {
        this.DELETE_LINE({ pageNo: pageIndex, lineIndex });
      }
      this.doneEditingLine(pageIndex, lineIndex);

      this.editPages.forEach(function updateEditPage(editPage, index) {
        const editParts = editPage.split('_');
        const editPageIndex = parseInt(editParts[1], 10);
        const editIndex = parseInt(editParts[3], 10);
        if (editPageIndex === pageIndex && editIndex >= lineIndex) {
          this.editPages[index] = `page_${editPageIndex}_line_${editIndex - 1}`;
        }
      }, this);

      if (this.latestAddedLine != null) {
        const editParts = this.latestAddedLine.split('_');
        const editPageIndex = parseInt(editParts[1], 10);
        const editIndex = parseInt(editParts[3], 10);
        if (editPageIndex === pageIndex && editIndex >= lineIndex) {
          this.latestAddedLine = `page_${pageIndex}_line_${editIndex - 1}`;
        }
      }
    },
    cutLinePart(linePartId) {
      const index = this.linePartCuts.indexOf(linePartId);
      if (index === -1) {
        this.linePartCuts.push(linePartId);
      } else {
        this.linePartCuts.splice(index, 1);
      }
    },
    async insertLineAt(pageIndex, lineIndex, lineType) {
      // Map line types to their corresponding add methods
      const addMethodMap = {
        [LINE_TYPES.DIALOGUE]: () => this.addNewLine(),
        [LINE_TYPES.STAGE_DIRECTION]: () => this.addStageDirection(),
        [LINE_TYPES.CUE_LINE]: () => this.addCueLine(),
        [LINE_TYPES.SPACING]: () => this.addSpacing(),
      };

      // If we're inserting at the end of the page, use the add method instead
      if (this.TMP_SCRIPT[pageIndex].length - 1 === lineIndex) {
        await addMethodMap[lineType]();
        return;
      }

      // Create new line object with appropriate configuration
      const newLineIndex = lineIndex + 1;
      const newLineObject = JSON.parse(JSON.stringify(this.blankLineObj));
      newLineObject.line_type = lineType;

      // Inherit act and scene from previous line before inserting
      const prevLine = await this.getPreviousLineForIndex(newLineIndex);
      if (prevLine) {
        newLineObject.act_id = prevLine.act_id;
        newLineObject.scene_id = prevLine.scene_id;
      }

      if (this.IS_DRAFT_ACTIVE && this.DRAFT_YDOC) {
        addYDocLine(this.DRAFT_YDOC, this.currentEditPage, newLineObject, newLineIndex);
      } else {
        this.INSERT_BLANK_LINE({
          pageNo: this.currentEditPage,
          lineIndex: newLineIndex,
          lineObj: newLineObject,
        });
      }

      // Update existing edit page indices
      this.editPages.forEach(function updateEditPage(editPage, index) {
        const editParts = editPage.split('_');
        const editPageIndex = parseInt(editParts[1], 10);
        const editIndex = parseInt(editParts[3], 10);
        if (editPageIndex === pageIndex && editIndex >= newLineIndex) {
          this.editPages[index] = `page_${editPageIndex}_line_${editIndex + 1}`;
        }
      }, this);

      // Add new line to edit pages
      const lineIdent = `page_${this.currentEditPage}_line_${newLineIndex}`;
      this.editPages.push(lineIdent);
      this._broadcastAwareness(this.currentEditPage, newLineIndex);
    },
    async insertDialogueAt(pageIndex, lineIndex) {
      await this.insertLineAt(pageIndex, lineIndex, LINE_TYPES.DIALOGUE);
    },
    async insertStageDirectionAt(pageIndex, lineIndex) {
      await this.insertLineAt(pageIndex, lineIndex, LINE_TYPES.STAGE_DIRECTION);
    },
    async insertCueLineAt(pageIndex, lineIndex) {
      await this.insertLineAt(pageIndex, lineIndex, LINE_TYPES.CUE_LINE);
    },
    async insertSpacingAt(pageIndex, lineIndex) {
      await this.insertLineAt(pageIndex, lineIndex, LINE_TYPES.SPACING);
    },
    async saveScript() {
      if (!this.IS_CUT_MODE) {
        if (this.scriptChanges) {
          this.savingInProgress = true;
          this.totalSavePages = Object.keys(this.TMP_SCRIPT).length;
          this.curSavePage = 0;
          this.$bvModal.show('save-script');

          const orderedPages = Object.keys(this.TMP_SCRIPT)
            .map((x) => parseInt(x, 10))
            .sort((a, b) => a - b);

          for (const pageNo of orderedPages) {
            this.curSavePage = pageNo;
            // Check whether the page actually has any lines on it, and if not then skip
            const tmpScriptPage = this.TMP_SCRIPT[pageNo.toString()];
            if (tmpScriptPage.length !== 0) {
              // Check the actual script to see if the page exists or not
              const actualScriptPage = this.GET_SCRIPT_PAGE(pageNo);
              if (actualScriptPage.length === 0) {
                // New page
                const response = await this.SAVE_NEW_PAGE(pageNo);
                if (response) {
                  await this.LOAD_SCRIPT_PAGE(pageNo);
                  this.ADD_BLANK_PAGE(pageNo);
                  this.RESET_DELETED(pageNo);
                  this.RESET_INSERTED(pageNo);
                } else {
                  this.$toast.error('Unable to save script. Please try again.');
                  this.saveError = true;
                  break;
                }
              } else {
                // Existing page, check if anything has changed before saving
                const lineDiff = diff(actualScriptPage, tmpScriptPage);
                if (
                  Object.keys(lineDiff).length > 0 ||
                  this.DELETED_LINES(pageNo).length > 0 ||
                  this.INSERTED_LINES(pageNo).length > 0
                ) {
                  const response = await this.SAVE_CHANGED_PAGE(pageNo);
                  if (response) {
                    await this.LOAD_SCRIPT_PAGE(pageNo);
                    this.ADD_BLANK_PAGE(pageNo);
                    this.RESET_DELETED(pageNo);
                    this.RESET_INSERTED(pageNo);
                  } else {
                    this.$toast.error('Unable to save script. Please try again.');
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
          this.$toast.warning('No changes to save!');
        }
        await this.getMaxScriptPage();
      } else {
        this.savingInProgress = true;
        await this.SAVE_SCRIPT_CUTS(this.linePartCuts);
        this.resetCutsToSaved();
        // Re-setup autosave (to reset the timer since we have just saved)
        this.setupAutoSave();
        this.savingInProgress = false;
      }
    },
    validatePageState(name) {
      const { $dirty, $error } = this.$v.pageInputFormState[name];
      return $dirty ? !$error : null;
    },
    async goToPage() {
      this.changingPage = true;
      await this.goToPageInner(this.pageInputFormState.pageNo);
      this.changingPage = false;
    },
    async goToPageInner(pageNo) {
      if (pageNo > 1) {
        await this.LOAD_SCRIPT_PAGE(parseInt(pageNo, 10) - 1);
      }
      await this.LOAD_SCRIPT_PAGE(pageNo);
      this.currentEditPage = pageNo;
      if (!Object.keys(this.TMP_SCRIPT).includes(this.currentEditPageKey)) {
        this.ADD_BLANK_PAGE(this.currentEditPage);
      }
      await this.LOAD_SCRIPT_PAGE(parseInt(pageNo, 10) + 1);

      // If Y.Doc is synced, overlay collaborative data onto loaded pages
      if (this.IS_DRAFT_SYNCED && this.DRAFT_YDOC) {
        this.syncCurrentPageFromYDoc();
      }
    },
    setupAutoSave() {
      const autoSaveInterval = Math.max(
        this.USER_SETTINGS.script_auto_save_interval * 1000 * 60,
        1000 * 60
      );
      if (!this.IS_CURRENT_EDITOR && this.autoSaveInterval != null) {
        clearInterval(this.autoSaveInterval);
      } else if (this.IS_CURRENT_EDITOR) {
        if (this.USER_SETTINGS.enable_script_auto_save) {
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
    async autosave() {
      if (this.isAutoSaving) {
        return;
      }
      this.isAutoSaving = true;
      const toastInstance = this.$toast.open({
        type: 'info',
        message: 'Performing autosave...',
        duration: 0,
        dismissible: false,
      });
      if (!this.IS_CUT_MODE) {
        if (this.scriptChanges) {
          let curSavePage = 0;
          const orderedPages = Object.keys(this.TMP_SCRIPT)
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
            const tmpScriptPage = this.TMP_SCRIPT[pageNo.toString()];
            if (tmpScriptPage.length !== 0) {
              // Check the actual script to see if the page exists or not
              const actualScriptPage = this.GET_SCRIPT_PAGE(pageNo);
              if (actualScriptPage.length === 0) {
                // New page
                const response = await this.SAVE_NEW_PAGE(pageNo);
                if (response) {
                  await this.LOAD_SCRIPT_PAGE(pageNo);
                  this.ADD_BLANK_PAGE(pageNo);
                  this.RESET_DELETED(pageNo);
                  this.RESET_INSERTED(pageNo);
                } else {
                  saveFailure = true;
                  break;
                }
              } else {
                // Existing page, check if anything has changed before saving
                const lineDiff = diff(actualScriptPage, tmpScriptPage);
                if (
                  Object.keys(lineDiff).length > 0 ||
                  this.DELETED_LINES(pageNo).length > 0 ||
                  this.INSERTED_LINES(pageNo).length > 0
                ) {
                  const response = await this.SAVE_CHANGED_PAGE(pageNo);
                  if (response) {
                    await this.LOAD_SCRIPT_PAGE(pageNo);
                    this.ADD_BLANK_PAGE(pageNo);
                    this.RESET_DELETED(pageNo);
                    this.RESET_INSERTED(pageNo);
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
        await this.SAVE_SCRIPT_CUTS(this.linePartCuts);
        this.resetCutsToSaved();
        toastInstance.message = 'Autosave successful';
        toastInstance.type = 'success';
        setTimeout(() => toastInstance.dismiss(), 5000);
      }
      this.isAutoSaving = false;
    },
    /**
     * Set up the Y.Doc → TMP_SCRIPT bridge after initial sync completes.
     * Installs a deep observer on the Y.Doc pages map that updates
     * TMP_SCRIPT whenever Y.Doc changes (local or remote).
     *
     * Components write directly to Y.Map/Y.Text, and this observer
     * keeps the TMP_SCRIPT view cache in sync for ScriptLineViewer rendering.
     */
    setupYDocBridge() {
      const ydoc = this.DRAFT_YDOC;
      if (!ydoc) return;

      const pages = ydoc.getMap('pages');

      // Sync the current page from Y.Doc → TMP_SCRIPT on initial connect
      this.syncCurrentPageFromYDoc();

      // Observe deep changes on the pages map — all origins flow through
      const observer = (events) => {
        // Determine which pages were affected
        const affectedPages = new Set();
        events.forEach((event) => {
          const path = event.path;
          if (path.length >= 1) {
            affectedPages.add(path[0].toString());
          } else {
            // Top-level pages map changed — sync all loaded pages
            Object.keys(this.TMP_SCRIPT).forEach((p) => affectedPages.add(p));
          }
        });

        // Sync affected pages that are currently loaded
        affectedPages.forEach((pageKey) => {
          if (Object.keys(this.TMP_SCRIPT).includes(pageKey)) {
            const lines = syncPageFromYDoc(ydoc, pageKey);
            this.$store.commit('ADD_PAGE', { pageNo: pageKey, pageContents: lines });
          }
        });
      };

      pages.observeDeep(observer);
      this.ydocObserverCleanup = () => pages.unobserveDeep(observer);

      log.info('ScriptEditor: Y.Doc bridge established');
    },
    /**
     * Remove the Y.Doc observer.
     */
    teardownYDocBridge() {
      if (this.ydocObserverCleanup) {
        this.ydocObserverCleanup();
        this.ydocObserverCleanup = null;
      }
    },
    /**
     * Sync all currently loaded TMP_SCRIPT pages from Y.Doc data.
     */
    syncCurrentPageFromYDoc() {
      const ydoc = this.DRAFT_YDOC;
      if (!ydoc) return;

      Object.keys(this.TMP_SCRIPT).forEach((pageKey) => {
        const lines = syncPageFromYDoc(ydoc, pageKey);
        if (lines.length > 0) {
          this.$store.commit('ADD_PAGE', { pageNo: pageKey, pageContents: lines });
        }
      });
    },
    /**
     * Get the Y.Map for a specific line from the Y.Doc.
     * Returns null when not in collab mode or if the line doesn't exist.
     * @param {number} index - Line index on the current page
     * @returns {import('yjs').Map|null}
     */
    getYLineMap(index) {
      if (!this.IS_DRAFT_ACTIVE || !this.DRAFT_YDOC) return null;
      const pages = this.DRAFT_YDOC.getMap('pages');
      const pageArray = pages.get(this.currentEditPageKey);
      if (!pageArray || index >= pageArray.length) {
        return null;
      }
      return pageArray.get(index);
    },
    /**
     * Broadcast awareness state (which line the user is editing).
     * @param {number} page - The page number
     * @param {number|null} lineIndex - The line index, or null if no line is expanded
     */
    _broadcastAwareness(page, lineIndex) {
      if (!this.DRAFT_PROVIDER) return;
      const user = this.CURRENT_USER;
      this.DRAFT_PROVIDER.setLocalAwareness({
        userId: user ? user.id : null,
        username: user ? user.username : 'Unknown',
        page,
        lineIndex,
      });
    },
    /**
     * Get the list of other users editing a specific line.
     * @param {number} lineIndex - The line index on the current page
     * @returns {Array<{userId: number, username: string}>}
     */
    editingUsersForLine(lineIndex) {
      const key = `${this.currentEditPage}:${lineIndex}`;
      const editors = this.DRAFT_LINE_EDITORS[key] || [];
      // Exclude current user
      const currentUserId = this.CURRENT_USER ? this.CURRENT_USER.id : null;
      return editors.filter((e) => e.userId !== currentUserId);
    },
    calculateNavbarHeight() {
      const navbar = document.querySelector('.navbar');
      if (navbar) {
        this.navbarHeight = navbar.offsetHeight;
      } else {
        this.navbarHeight = 56;
      }
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
      'GET_SCRIPT_REVISIONS',
      'JOIN_DRAFT_ROOM',
      'LEAVE_DRAFT_ROOM',
    ]),
  },
};
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

.btn-group-item {
  display: flex;
}

.btn-group-item:first-child > .btn {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.btn-group-item:last-child > .btn {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}
</style>
