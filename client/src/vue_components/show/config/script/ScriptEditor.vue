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
                <b-button variant="warning" :disabled="!CAN_REQUEST_EDIT" @click="onEditClick">
                  Edit
                </b-button>
              </span>
              <span v-b-tooltip.hover="cutsDisabledReason" class="btn-group-item">
                <b-button variant="warning" :disabled="!CAN_REQUEST_CUTS" @click="requestCutEdit">
                  Cuts
                </b-button>
              </span>
              <span
                v-if="HAS_DRAFT && EDITORS.length === 0"
                v-b-tooltip.hover="'Discard the unsaved draft permanently'"
                class="btn-group-item"
              >
                <b-button variant="outline-danger" size="sm" @click="confirmDiscardDraft">
                  Discard Draft
                </b-button>
              </span>
            </template>
            <template v-if="IS_CURRENT_EDITOR">
              <b-button
                variant="warning"
                :disabled="savingInProgress || IS_DRAFT_SAVING"
                @click="stopEditing"
              >
                Stop Editing
              </b-button>
              <b-button
                variant="success"
                :disabled="!canSave || IS_DRAFT_SAVING"
                @click="saveScript"
              >
                {{ IS_DRAFT_SAVING ? 'Saving...' : 'Save' }}
              </b-button>
              <span v-if="IS_DRAFT_ACTIVE" class="ml-2 align-self-center small text-muted">
                <template v-if="IS_DRAFT_SAVING">
                  Saving{{ DRAFT_SAVE_PHASE ? ` (${DRAFT_SAVE_PHASE})` : '' }}...
                </template>
                <template v-else> Draft &mdash; unsaved changes </template>
              </span>
            </template>
            <template v-if="IS_CURRENT_CUTTER">
              <b-button variant="warning" :disabled="savingInProgress" @click="stopEditing">
                Stop Cuts
              </b-button>
              <b-button variant="success" :disabled="!canSave" @click="saveScript"> Save </b-button>
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
        <template v-if="IS_DRAFT_ACTIVE">
          <template v-for="(line, index) in localPageScript">
            <script-line-editor
              v-if="editPages.includes(`page_${currentEditPage}_line_${index}`)"
              :key="`page_${currentEditPage}_line_${index}`"
              :line-index="index"
              :current-edit-page="currentEditPage"
              :acts="ACT_LIST"
              :scenes="SCENE_LIST"
              :characters="CHARACTER_LIST"
              :character-groups="CHARACTER_GROUP_LIST"
              :value="line"
              :y-line-map="getYLineMap(index)"
              :previous-line="localPageScript[index - 1] || null"
              :next-line="localPageScript[index + 1] || null"
              :line-type="line.line_type"
              :stage-direction-styles="STAGE_DIRECTION_STYLES"
              @doneEditing="doneEditingLine(currentEditPage, index)"
              @deleteLine="deleteLine(currentEditPage, index)"
            />
            <script-line-viewer
              v-else
              :key="`page_${currentEditPage}_line_${index}`"
              :line-index="index"
              :line="line"
              :page="localPageScript"
              :acts="ACT_LIST"
              :scenes="SCENE_LIST"
              :characters="CHARACTER_LIST"
              :character-groups="CHARACTER_GROUP_LIST"
              :previous-line="localPageScript[index - 1] || null"
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
        <template v-else>
          <template v-for="(line, index) in GET_SCRIPT_PAGE(currentEditPage)">
            <script-line-viewer
              :key="`page_${currentEditPage}_line_${index}`"
              :line-index="index"
              :line="line"
              :page="GET_SCRIPT_PAGE(currentEditPage)"
              :acts="ACT_LIST"
              :scenes="SCENE_LIST"
              :characters="CHARACTER_LIST"
              :character-groups="CHARACTER_GROUP_LIST"
              :previous-line="GET_SCRIPT_PAGE(currentEditPage)[index - 1] || null"
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
    <b-modal
      id="draft-resume-modal"
      ref="draft-resume-modal"
      title="Unsaved Draft Found"
      size="md"
      no-close-on-backdrop
      hide-footer
    >
      <p>An unsaved draft exists for this script. What would you like to do?</p>
      <div class="d-flex justify-content-between mt-3">
        <b-button variant="primary" @click="resumeDraft"> Resume Draft </b-button>
        <b-button variant="danger" @click="discardAndStartFresh">
          Discard &amp; Start Fresh
        </b-button>
        <b-button variant="secondary" @click="$bvModal.hide('draft-resume-modal')">
          Cancel
        </b-button>
      </div>
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
import { zeroToNull, addYDocLine, deleteYDocLine } from '@/utils/yjs/yjsBridge';

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
      dataLoaded: false,
      latestAddedLine: null,
      linePartCuts: [],
      navbarHeight: 0,
      ydocObserverCleanup: null,
      localPageScript: [],
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
    loaded() {
      if (!this.dataLoaded) return false;
      // Show spinner while editor is joining the room (server confirmed, room not yet active)
      if (this.IS_CURRENT_EDITOR && !this.IS_DRAFT_ACTIVE) return false;
      // Show spinner while the Y.Doc is syncing
      if (this.IS_DRAFT_ACTIVE && !this.IS_DRAFT_SYNCED) return false;
      return true;
    },
    currentEditPageKey() {
      return this.currentEditPage.toString();
    },
    scriptChanges() {
      if (this.IS_CUT_MODE) {
        return Object.keys(diff(this.SCRIPT_CUTS, this.linePartCuts)).length > 0;
      }
      return false;
    },
    saveProgressVariant() {
      if (!this.savingInProgress) {
        return this.saveError ? 'danger' : 'success';
      }
      return 'primary';
    },
    editDisabledReason() {
      if (this.CURRENT_SHOW_SESSION) return 'Cannot edit script during a live session';
      if (this.CUTTERS.length > 0) return 'Another user is currently making cuts';
      return '';
    },
    cutsDisabledReason() {
      if (this.CURRENT_SHOW_SESSION) return 'Cannot make cuts during a live session';
      if (this.EDITORS.length > 0) return 'Another user is currently editing';
      if (this.CUTTERS.length > 0) return 'Another user is currently making cuts';
      if (this.HAS_DRAFT) return 'An unsaved draft exists';
      return '';
    },
    canEdit() {
      return this.IS_CURRENT_EDITOR || this.IS_CURRENT_CUTTER;
    },
    canSave() {
      if (this.IS_CUT_MODE) return this.scriptChanges;
      if (this.IS_DRAFT_ACTIVE) return this.IS_DRAFT_DIRTY && this.editPages.length === 0;
      return false;
    },
    pagesWithOpenChanges() {
      return [...new Set(this.editPages.map((x) => parseInt(x.split('_')[1], 10)))];
    },
    ...mapGetters([
      'CURRENT_SHOW',
      'CURRENT_SHOW_SESSION',
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
      'SCENE_BY_ID',
      'ACT_BY_ID',
      'IS_CUT_MODE',
      'SCRIPT_CUTS',
      'STAGE_DIRECTION_STYLES',
      'CURRENT_USER',
      'STAGE_DIRECTION_STYLE_OVERRIDES',
      'IS_SCRIPT_EDITOR',
      'CURRENT_REVISION',
      'IS_DRAFT_ACTIVE',
      'IS_DRAFT_DIRTY',
      'IS_DRAFT_SYNCED',
      'DRAFT_YDOC',
      'DRAFT_COLLABORATORS',
      'DRAFT_PROVIDER',
      'DRAFT_LINE_EDITORS',
      'DRAFT_AWARENESS_STATES',
      'IS_DRAFT_SAVING',
      'IS_DRAFT_LAST_SAVED',
      'DRAFT_SAVE_ERROR',
      'DRAFT_SAVE_PHASE',
      'DRAFT_SAVE_PROGRESS',
    ]),
  },
  watch: {
    currentEditPage(val) {
      localStorage.setItem('scriptEditPage', val);
    },
    IS_CURRENT_EDITOR(isEditor) {
      if (isEditor && this.CURRENT_REVISION && !this.IS_DRAFT_ACTIVE) {
        this.JOIN_DRAFT_ROOM({ role: 'editor' });
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
          this.JOIN_DRAFT_ROOM({ role: 'viewer' });
        }
      },
      immediate: true,
    },
    IS_DRAFT_ACTIVE(active) {
      if (!active) {
        this.teardownYDocBridge();
        // Reload the current page into the Vuex script store so the non-draft
        // template branch has data immediately after leaving the room.
        this.LOAD_SCRIPT_PAGE(this.currentEditPage);
      }
    },
    IS_DRAFT_SYNCED(synced) {
      if (synced) {
        this.setupYDocBridge();
      }
    },
    DRAFT_SAVE_PROGRESS({ page, total }) {
      if (!this._collabSaveToast || !total) return;
      const percent = Math.round((page / total) * 100);
      this._collabSaveToast.message =
        page === 0 ? 'Saving script...' : `Saving page ${page} of ${total} (${percent}%)`;
    },
    IS_DRAFT_SAVING: function onSavingChanged(saving) {
      if (!this.IS_CURRENT_EDITOR) return;
      if (saving && !this._collabSaveToast) {
        this._collabSaveToast = this.$toast.open({
          type: 'info',
          message: 'Saving script...',
          duration: 0,
          dismissible: false,
        });
      } else if (!saving && this._collabSaveToast) {
        this._collabSaveToast.dismiss();
        this._collabSaveToast = null;

        const error = this.DRAFT_SAVE_ERROR;
        if (error) {
          if (Array.isArray(error)) {
            const messages = error.map(
              (e) => `Page ${e.page}, line ${e.lineIndex + 1}: ${e.message}`
            );
            this.$toast.error(`Save failed:\n${messages.join('\n')}`);
          } else {
            this.$toast.error(`Save failed: ${error}`);
          }
        } else if (this.IS_DRAFT_LAST_SAVED) {
          this.$toast.success('Script saved successfully');
          this.LOAD_SCRIPT_PAGE(this.currentEditPage);
          this.GET_SCRIPT_CONFIG_STATUS();
          this.getMaxScriptPage();
        }
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
    this.dataLoaded = true;
    this.$nextTick(() => this.calculateNavbarHeight());
  },
  created() {
    window.addEventListener('resize', this.calculateNavbarHeight);
  },
  destroyed() {
    window.removeEventListener('resize', this.calculateNavbarHeight);
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
    onEditClick() {
      if (this.HAS_DRAFT && this.EDITORS.length === 0) {
        this.$bvModal.show('draft-resume-modal');
      } else {
        this.requestEdit();
      }
    },
    requestEdit() {
      this.$socket.sendObj({
        OP: 'REQUEST_SCRIPT_EDIT',
        DATA: {},
      });
    },
    resumeDraft() {
      this.$bvModal.hide('draft-resume-modal');
      this.requestEdit();
    },
    async discardAndStartFresh() {
      this.$bvModal.hide('draft-resume-modal');
      const response = await fetch(makeURL('/api/v1/show/script/draft'), { method: 'DELETE' });
      if (response.ok) {
        await this.GET_SCRIPT_CONFIG_STATUS();
        this.requestEdit();
      } else {
        log.error('Failed to discard draft');
      }
    },
    async confirmDiscardDraft() {
      const confirmed = await this.$bvModal.msgBoxConfirm(
        'Are you sure you want to discard the unsaved draft? This cannot be undone.',
        { okVariant: 'danger', okTitle: 'Discard Draft' }
      );
      if (confirmed) {
        const response = await fetch(makeURL('/api/v1/show/script/draft'), { method: 'DELETE' });
        if (response.ok) {
          await this.GET_SCRIPT_CONFIG_STATUS();
        }
      }
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
        this.resetCutsToSaved();
        this.$socket.sendObj({ OP: 'STOP_SCRIPT_EDIT', DATA: {} });
        this.SET_CUT_MODE(false);
        return;
      }

      // Collab edit mode: stay in room as viewer
      this.editPages = [];
      this._broadcastAwareness(this.currentEditPage, null);
      this.$socket.sendObj({ OP: 'STOP_SCRIPT_EDIT', DATA: {} });
    },
    async decrPage() {
      if (this.currentEditPage <= 1) return;
      if (this.IS_DRAFT_ACTIVE) {
        this.currentEditPage--;
        this._syncLocalPageScript();
        return;
      }
      const targetPage = this.currentEditPage - 1;
      await this.LOAD_SCRIPT_PAGE(targetPage);
      this.currentEditPage--;
      await this.LOAD_SCRIPT_PAGE(this.currentEditPage - 1);
    },
    async incrPage() {
      if (this.IS_DRAFT_ACTIVE) {
        this.currentEditPage++;
        this._syncLocalPageScript();
        return;
      }
      this.currentEditPage++;
      await this.LOAD_SCRIPT_PAGE(this.currentEditPage);
      await this.LOAD_SCRIPT_PAGE(this.currentEditPage + 1);
    },
    addLineOfType(lineType, trackAsLatest = false) {
      const lineObj = JSON.parse(JSON.stringify(this.blankLineObj));
      lineObj.line_type = lineType;

      // Inherit act_id/scene_id from the last line on this page
      const prevLine =
        this.localPageScript.length > 0
          ? this.localPageScript[this.localPageScript.length - 1]
          : null;
      if (prevLine) {
        lineObj.act_id = prevLine.act_id;
        lineObj.scene_id = prevLine.scene_id;
      }

      // addYDocLine transacts synchronously; observer fires and updates localPageScript
      addYDocLine(this.DRAFT_YDOC, this.currentEditPage, lineObj);

      const lineIndex = this.localPageScript.length - 1;
      const lineIdent = `page_${this.currentEditPage}_line_${lineIndex}`;
      this.editPages.push(lineIdent);
      this._broadcastAwareness(this.currentEditPage, lineIndex);
      if (trackAsLatest) {
        this.latestAddedLine = lineIdent;
      }
    },
    addNewLine() {
      this.addLineOfType(LINE_TYPES.DIALOGUE, true);
    },
    addStageDirection() {
      this.addLineOfType(LINE_TYPES.STAGE_DIRECTION);
    },
    addCueLine() {
      this.addLineOfType(LINE_TYPES.CUE_LINE);
    },
    addSpacing() {
      this.addLineOfType(LINE_TYPES.SPACING);
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
      deleteYDocLine(this.DRAFT_YDOC, pageIndex, lineIndex);
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
    insertLineAt(pageIndex, lineIndex, lineType) {
      // Map line types to their corresponding add methods
      const addMethodMap = {
        [LINE_TYPES.DIALOGUE]: () => this.addNewLine(),
        [LINE_TYPES.STAGE_DIRECTION]: () => this.addStageDirection(),
        [LINE_TYPES.CUE_LINE]: () => this.addCueLine(),
        [LINE_TYPES.SPACING]: () => this.addSpacing(),
      };

      // If we're inserting at the end of the page, use the add method instead
      if (this.localPageScript.length - 1 === lineIndex) {
        addMethodMap[lineType]();
        return;
      }

      // Create new line object with appropriate configuration
      const newLineIndex = lineIndex + 1;
      const newLineObject = JSON.parse(JSON.stringify(this.blankLineObj));
      newLineObject.line_type = lineType;

      // Inherit act and scene from the line at the insert position
      const prevLine =
        lineIndex >= 0 && lineIndex < this.localPageScript.length
          ? this.localPageScript[lineIndex]
          : null;
      if (prevLine) {
        newLineObject.act_id = prevLine.act_id;
        newLineObject.scene_id = prevLine.scene_id;
      }

      addYDocLine(this.DRAFT_YDOC, this.currentEditPage, newLineObject, newLineIndex);

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
    insertDialogueAt(pageIndex, lineIndex) {
      this.insertLineAt(pageIndex, lineIndex, LINE_TYPES.DIALOGUE);
    },
    insertStageDirectionAt(pageIndex, lineIndex) {
      this.insertLineAt(pageIndex, lineIndex, LINE_TYPES.STAGE_DIRECTION);
    },
    insertCueLineAt(pageIndex, lineIndex) {
      this.insertLineAt(pageIndex, lineIndex, LINE_TYPES.CUE_LINE);
    },
    insertSpacingAt(pageIndex, lineIndex) {
      this.insertLineAt(pageIndex, lineIndex, LINE_TYPES.SPACING);
    },
    async saveScript() {
      // Collaborative save — server handles persistence via WebSocket
      if (this.IS_DRAFT_ACTIVE) {
        this.SET_DRAFT_SAVING(true);
        this.$socket.sendObj({ OP: 'SAVE_SCRIPT_DRAFT', DATA: {} });
        return;
      }

      if (this.IS_CUT_MODE) {
        this.savingInProgress = true;
        await this.SAVE_SCRIPT_CUTS(this.linePartCuts);
        this.resetCutsToSaved();
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
      if (this.IS_DRAFT_ACTIVE) {
        this.currentEditPage = pageNo;
        this._syncLocalPageScript();
        return;
      }
      if (pageNo > 1) {
        await this.LOAD_SCRIPT_PAGE(parseInt(pageNo, 10) - 1);
      }
      await this.LOAD_SCRIPT_PAGE(pageNo);
      this.currentEditPage = pageNo;
      await this.LOAD_SCRIPT_PAGE(parseInt(pageNo, 10) + 1);
    },
    /**
     * Convert a Y.Map line to a plain JS object safe for Vue 2 reactive state.
     * Y.Maps must never be stored directly in reactive data — Vue 2 walks their
     * internal properties, breaking Yjs internals.
     *
     * @param {import('yjs').Map} yMap - Y.Map for one script line
     * @returns {object|null} Plain line object, or null if yMap is falsy
     */
    _ydocLineToPlain(yMap) {
      if (!yMap) return null;
      const lineId = zeroToNull(yMap.get('_id'));
      const partsArray = yMap.get('parts');
      const lineParts = partsArray
        ? Array.from({ length: partsArray.length }, (_, i) => {
            const p = partsArray.get(i);
            return {
              id: zeroToNull(p.get('_id')),
              line_id: lineId,
              part_index: p.get('part_index'),
              character_id: zeroToNull(p.get('character_id')),
              character_group_id: zeroToNull(p.get('character_group_id')),
              line_text: p.get('line_text') ? p.get('line_text').toString() : '',
            };
          })
        : [];
      return {
        id: lineId,
        line_type: yMap.get('line_type'),
        act_id: zeroToNull(yMap.get('act_id')),
        scene_id: zeroToNull(yMap.get('scene_id')),
        stage_direction_style_id: zeroToNull(yMap.get('stage_direction_style_id')),
        line_parts: lineParts,
      };
    },
    /**
     * Rebuild localPageScript from the current page in Y.Doc.
     * Called on initial sync and on every Y.Doc change.
     */
    _syncLocalPageScript() {
      const ydoc = this.DRAFT_YDOC;
      if (!ydoc) {
        this.localPageScript = [];
        return;
      }
      const pages = ydoc.getMap('pages');
      const pageArray = pages.get(this.currentEditPageKey);
      this.localPageScript = pageArray
        ? Array.from({ length: pageArray.length }, (_, i) =>
            this._ydocLineToPlain(pageArray.get(i))
          )
        : [];
    },
    /**
     * Set up the Y.Doc → localPageScript bridge after initial sync completes.
     * Installs a deep observer on the Y.Doc pages map that rebuilds
     * localPageScript whenever Y.Doc changes (local or remote).
     */
    setupYDocBridge() {
      const ydoc = this.DRAFT_YDOC;
      if (!ydoc) return;

      const pages = ydoc.getMap('pages');

      // Populate localPageScript from current Y.Doc state
      this._syncLocalPageScript();

      if (this.HAS_DRAFT) {
        this.$store.commit('SET_DRAFT_DIRTY', true);
      }

      const observer = () => {
        this._syncLocalPageScript();
        this.$store.commit('SET_DRAFT_DIRTY', true);
      };

      pages.observeDeep(observer);
      this.ydocObserverCleanup = () => pages.unobserveDeep(observer);

      log.info('ScriptEditor: Y.Doc bridge established');
    },
    teardownYDocBridge() {
      if (this.ydocObserverCleanup) {
        this.ydocObserverCleanup();
        this.ydocObserverCleanup = null;
      }
      this.localPageScript = [];
    },
    getYLineMap(index) {
      if (!this.DRAFT_YDOC) return null;
      const pages = this.DRAFT_YDOC.getMap('pages');
      const pageArray = pages.get(this.currentEditPageKey);
      if (!pageArray || index >= pageArray.length) return null;
      return pageArray.get(index);
    },
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
    editingUsersForLine(lineIndex) {
      const key = `${this.currentEditPage}:${lineIndex}`;
      const editors = this.DRAFT_LINE_EDITORS[key] || [];
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
    ...mapMutations(['SET_CUT_MODE', 'SET_DRAFT_SAVING']),
    ...mapActions([
      'GET_SCENE_LIST',
      'GET_ACT_LIST',
      'GET_CHARACTER_LIST',
      'GET_CHARACTER_GROUP_LIST',
      'LOAD_SCRIPT_PAGE',
      'GET_SCRIPT_CONFIG_STATUS',
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
