<template>
  <b-container
    v-show="loaded"
    class="mx-0 px-0"
    fluid
  >
    <b-row class="script-row">
      <b-col cols="2">
        <b-button
          v-b-modal.go-to-page
          variant="success"
        >
          Go to Page
        </b-button>
      </b-col>
      <b-col
        cols="2"
        style="text-align: right"
      >
        <b-button
          variant="success"
          :disabled="currentEditPage === 1"
          @click="decrPage"
        >
          Prev Page
        </b-button>
      </b-col>
      <b-col cols="4">
        <p>Current Page: {{ currentEditPage }}</p>
      </b-col>
      <b-col
        cols="2"
        style="text-align: left"
      >
        <b-button
          variant="success"
          @click="incrPage"
        >
          Next Page
        </b-button>
      </b-col>
      <b-col cols="2">
        <b-button-group>
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
            @click="stopEditing"
          >
            Stop Editing
          </b-button>
          <b-button
            v-if="INTERNAL_UUID === CURRENT_EDITOR"
            variant="success"
            :disabled="!canSave"
            @click="saveScript"
          >
            Save
          </b-button>
        </b-button-group>
      </b-col>
    </b-row>
    <b-row class="script-row">
      <b-col cols="1">
        Act
      </b-col>
      <b-col cols="1">
        Scene
      </b-col>
      <b-col>Line</b-col>
      <b-col cols="1" />
    </b-row>
    <hr>
    <b-row class="script-row">
      <b-col cols="12">
        <template v-for="(line, index) in TMP_SCRIPT[currentEditPage]">
          <template v-if="!DELETED_LINES(currentEditPage).includes(index)">
            <script-line-editor
              v-if="editPages.includes(`page_${currentEditPage}_line_${index}`)"
              :key="`page_${currentEditPage}_line_${index}`"
              :line-index="index"
              :acts="ACT_LIST"
              :scenes="SCENE_LIST"
              :characters="CHARACTER_LIST"
              :character-groups="CHARACTER_GROUP_LIST"
              :value="TMP_SCRIPT[currentEditPage][index]"
              :previous-line-fn="getPreviousLineForIndex"
              :next-line-fn="getNextLineForIndex"
              :is-stage-direction="line.stage_direction"
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
              :insert-mode="insertMode"
              @editLine="beginEditingLine(currentEditPage, index)"
              @cutLinePart="cutLinePart"
              @insertLine="insertLineAt(currentEditPage, index)"
            />
          </template>
        </template>
      </b-col>
    </b-row>
    <b-row class="script-row pt-1">
      <b-col
        cols="10"
        class="ml-auto"
      >
        <b-button-group
          v-show="canEdit && !IS_CUT_MODE"
          style="float: right"
        >
          <b-button
            v-if="canGenerateDebugScript"
            v-b-modal.debug-generate
            variant="warning"
          >
            Debug Script
          </b-button>
          <b-button @click="addNewLine">
            Add line
          </b-button>
          <b-button @click="addStageDirection">
            Add Stage Direction
          </b-button>
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
      id="go-to-page"
      ref="go-to-page"
      title="Go to Page"
      size="sm"
      :hide-header-close="changingPage"
      :hide-footer="changingPage"
      :no-close-on-backdrop="changingPage"
      :no-close-on-esc="changingPage"
      @ok="goToPage"
    >
      <b-form @submit.stop.prevent="">
        <b-form-group
          id="page-input-group"
          label="Page"
          label-for="page-input"
          label-cols="auto"
        >
          <b-form-input
            id="page-input"
            v-model="$v.pageInputFormState.pageNo.$model"
            name="page-input"
            type="number"
            :state="validatePageState('pageNo')"
            aria-describedby="page-feedback"
          />
          <b-form-invalid-feedback
            id="page-feedback"
          >
            This is a required field, and must be greater than 0.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="debug-generate"
      ref="debug-generate"
      title="Generate Debug Script"
      size="md"
      :hide-header-close="savingInProgress"
      :hide-footer="savingInProgress"
      :no-close-on-backdrop="savingInProgress"
      :no-close-on-esc="savingInProgress"
      @ok="generateDebugScript"
    >
      <b-form
        ref="debug-script-form"
        @submit.stop.prevent="generateDebugScript"
      >
        <b-form-group
          id="pages-input-group"
          label="Pages per Scene"
          label-for="pages-input"
          label-cols="auto"
        >
          <b-form-input
            id="pages-input"
            v-model="$v.debugFormState.pages.$model"
            name="pages-input"
            type="number"
            :state="validateDebugState('pages')"
            aria-describedby="pages-feedback"
          />
          <b-form-invalid-feedback
            id="pages-feedback"
          >
            This is a required field, and must be greater than 0.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="lines-input-group"
          label="Lines per Page"
          label-for="lines-input"
          label-cols="auto"
        >
          <b-form-input
            id="lines-input"
            v-model="$v.debugFormState.linesPerPage.$model"
            name="lines-input"
            type="number"
            :state="validateDebugState('linesPerPage')"
            aria-describedby="lines-feedback"
          />
          <b-form-invalid-feedback
            id="lines-feedback"
          >
            This is a required field, and must be greater than 0.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
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
import { makeURL, randInt } from '@/js/utils';
import { notNull, notNullAndGreaterThanZero } from '@/js/customValidators';

export default {
  name: 'ScriptConfig',
  components: { ScriptLineViewer, ScriptLineEditor },
  data() {
    return {
      currentEditPage: 1,
      editPages: [],
      blankLineObj: {
        id: null,
        act_id: null,
        scene_id: null,
        page: null,
        stage_direction: false,
        line_parts: [],
      },
      curSavePage: null,
      totalSavePages: null,
      savingInProgress: false,
      saveError: false,
      currentMaxPage: 1,
      debugFormState: {
        pages: 1,
        linesPerPage: 1,
      },
      pageInputFormState: {
        pageNo: 1,
      },
      changingPage: false,
      loaded: false,
      latestAddedLine: null,
      linePartCuts: [],
      insertMode: false,
    };
  },
  validations: {
    debugFormState: {
      pages: {
        required,
        notNull,
        notNullAndGreaterThanZero,
        minValue: minValue(1),
      },
      linesPerPage: {
        required,
        notNull,
        notNullAndGreaterThanZero,
        minValue: minValue(1),
      },
    },
    pageInputFormState: {
      pageNo: {
        required,
        notNull,
        notNullAndGreaterThanZero,
        minValue: minValue(1),
      },
    },
  },
  async beforeMount() {
    // Config status
    await this.GET_SCRIPT_CONFIG_STATUS();
    // Show details
    await this.GET_ACT_LIST();
    await this.GET_SCENE_LIST();
    await this.GET_CHARACTER_LIST();
    await this.GET_CHARACTER_GROUP_LIST();
    // Handle script cuts
    await this.GET_CUTS();
    this.resetCutsToSaved();

    // Get the max page of the saved version of the script
    await this.getMaxScriptPage();

    // Initialisation of page data
    const storedPage = localStorage.getItem('scriptEditPage');
    if (storedPage != null) {
      this.currentEditPage = parseInt(storedPage, 10);
    }
    await this.goToPageInner(this.currentEditPage);
  },
  mounted() {
    this.loaded = true;
  },
  created() {
    window.addEventListener('keydown', (e) => {
      if (e.shiftKey && this.canEdit) {
        this.insertMode = true;
      }
    });
    window.addEventListener('keyup', (e) => {
      if (e.key === 'Shift' && this.insertMode && this.canEdit) {
        this.insertMode = false;
      }
    });
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
        OP: 'REQUEST_SCRIPT_EDIT',
        DATA: {},
      });
    },
    resetCutsToSaved() {
      this.linePartCuts = JSON.parse(JSON.stringify(this.SCRIPT_CUTS));
    },
    async stopEditing() {
      if (this.scriptChanges) {
        const msg = 'Are you sure you want to stop editing the script? '
          + 'This will cause all unsaved changes to be lost';
        const action = await this.$bvModal.msgBoxConfirm(msg, {});
        if (action === false) {
          return;
        }
      }
      this.editPages = [];
      this.RESET_TO_SAVED(this.currentEditPage);
      this.resetCutsToSaved();
      this.$socket.sendObj({
        OP: 'STOP_SCRIPT_EDIT',
        DATA: {},
      });
      this.SET_CUT_MODE(false);
    },
    async decrPage() {
      if (this.currentEditPage > 1) {
        if (!Object.keys(this.TMP_SCRIPT).includes((this.currentEditPage - 1).toString())) {
          this.ADD_BLANK_PAGE(this.currentEditPage - 1);
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
    async addNewLine() {
      this.ADD_BLANK_LINE({
        pageNo: this.currentEditPage,
        lineObj: this.blankLineObj,
      });
      const lineIndex = this.TMP_SCRIPT[this.currentEditPageKey].length - 1;
      const lineIdent = `page_${this.currentEditPage}_line_${lineIndex}`;
      this.editPages.push(lineIdent);
      this.latestAddedLine = lineIdent;
      const prevLine = await this.getPreviousLineForIndex(lineIndex);
      if (prevLine != null) {
        this.TMP_SCRIPT[this.currentEditPageKey][lineIndex].act_id = prevLine.act_id;
        this.TMP_SCRIPT[this.currentEditPageKey][lineIndex].scene_id = prevLine.scene_id;
      }
    },
    async addStageDirection() {
      const stageDirectionObject = JSON.parse(JSON.stringify(this.blankLineObj));
      stageDirectionObject.stage_direction = true;
      this.ADD_BLANK_LINE({
        pageNo: this.currentEditPage,
        lineObj: stageDirectionObject,
      });
      const lineIndex = this.TMP_SCRIPT[this.currentEditPageKey].length - 1;
      this.editPages.push(`page_${this.currentEditPage}_line_${lineIndex}`);
      const prevLine = await this.getPreviousLineForIndex(lineIndex);
      if (prevLine != null) {
        this.TMP_SCRIPT[this.currentEditPageKey][lineIndex].act_id = prevLine.act_id;
        this.TMP_SCRIPT[this.currentEditPageKey][lineIndex].scene_id = prevLine.scene_id;
      }
    },
    async getPreviousLineForIndex(lineIndex) {
      if (lineIndex > 0) {
        return this.TMP_SCRIPT[this.currentEditPage][lineIndex - 1];
      }
      if (this.currentEditPage > 1) {
        let loopPageNo = this.currentEditPage - 1;
        /* eslint-disable no-await-in-loop */
        while (loopPageNo >= 1) {
          let loopPage = null;
          if (Object.keys(this.TMP_SCRIPT).includes(loopPageNo.toString())) {
            loopPage = this.TMP_SCRIPT[loopPageNo.toString()];
          } else {
            await this.LOAD_SCRIPT_PAGE(loopPageNo);
            loopPage = this.GET_SCRIPT_PAGE(loopPageNo);
          }
          if (loopPage.length > 0) {
            return loopPage[loopPage.length - 1];
          }
          loopPageNo -= 1;
        }
        /* eslint-enable no-await-in-loop */
      }
      return null;
    },
    async getNextLineForIndex(lineIndex) {
      // If there are lines after this one on the page, return the next line from the page
      if (lineIndex < this.TMP_SCRIPT[this.currentEditPage].length - 1) {
        return this.TMP_SCRIPT[this.currentEditPage][lineIndex + 1];
      }
      // See if there are any edit pages loaded which are after this page, and if so, return the
      // first line from the first page which contains lines
      const editPages = Object.keys(this.TMP_SCRIPT).map((x) => parseInt(x, 10)).sort();
      for (let i = 0; i < editPages.length; i++) {
        const editPage = editPages[i];
        if (editPage <= this.currentEditPage) {
          break;
        }
        const pageContent = this.TMP_SCRIPT[editPage.toString()];
        if (pageContent.length > 0) {
          return pageContent[0];
        }
      }
      // Edit pages do not have any lines we can use, so try loading script pages up to the max
      // page that is saved
      /* eslint-disable no-await-in-loop */
      for (let i = this.currentEditPage + 1; i <= this.currentMaxPage; i++) {
        await this.LOAD_SCRIPT_PAGE(i);
        const loopPage = this.GET_SCRIPT_PAGE(i);
        if (loopPage.length > 0) {
          return loopPage[0];
        }
      }
      /* eslint-enable no-await-in-loop */
      return null;
    },
    lineChange(line, index) {
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
    },
    doneEditingLine(pageIndex, lineIndex) {
      const lineIdent = `page_${pageIndex}_line_${lineIndex}`;
      const index = this.editPages.indexOf(lineIdent);
      if (index !== -1) {
        this.editPages.splice(index, 1);
      }
      if (this.latestAddedLine === lineIdent) {
        this.addNewLine();
      }
    },
    deleteLine(pageIndex, lineIndex) {
      if (this.latestAddedLine === `page_${pageIndex}_line_${lineIndex}`) {
        this.latestAddedLine = null;
      }
      this.DELETE_LINE({
        pageNo: pageIndex,
        lineIndex,
      });
      this.doneEditingLine(pageIndex, lineIndex);

      this.editPages.forEach(function (editPage, index) {
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
    async insertLineAt(pageIndex, lineIndex) {
      if (this.TMP_SCRIPT[pageIndex].length - 1 === lineIndex) {
        await this.addNewLine();
        return;
      }

      const newLineIndex = lineIndex + 1;
      this.INSERT_BLANK_LINE({
        pageNo: this.currentEditPage,
        lineIndex: newLineIndex,
        lineObj: this.blankLineObj,
      });
      this.editPages.forEach(function (editPage, index) {
        const editParts = editPage.split('_');
        const editPageIndex = parseInt(editParts[1], 10);
        const editIndex = parseInt(editParts[3], 10);
        if (editPageIndex === pageIndex && editIndex >= newLineIndex) {
          this.editPages[index] = `page_${editPageIndex}_line_${editIndex + 1}`;
        }
      }, this);

      const lineIdent = `page_${this.currentEditPage}_line_${newLineIndex}`;
      this.editPages.push(lineIdent);
      const prevLine = await this.getPreviousLineForIndex(newLineIndex);
      if (prevLine != null) {
        this.TMP_SCRIPT[this.currentEditPageKey][newLineIndex].act_id = prevLine.act_id;
        this.TMP_SCRIPT[this.currentEditPageKey][newLineIndex].scene_id = prevLine.scene_id;
      }
    },
    async saveScript() {
      if (!this.IS_CUT_MODE) {
        if (this.scriptChanges) {
          this.savingInProgress = true;
          this.totalSavePages = Object.keys(this.TMP_SCRIPT).length;
          this.curSavePage = 0;
          this.$bvModal.show('save-script');

          const orderedPages = Object.keys(this.TMP_SCRIPT).map((x) => parseInt(x, 10)).sort(
            (a, b) => a - b,
          );

          /* eslint-disable no-await-in-loop, no-restricted-syntax */
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
                if (Object.keys(lineDiff).length > 0 || this.DELETED_LINES(pageNo).length > 0
                    || this.INSERTED_LINES(pageNo).length > 0) {
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
          /* eslint-enable no-await-in-loop, no-restricted-syntax */
          this.savingInProgress = false;
        } else {
          this.$toast.warning('No changes to save!');
        }
        await this.getMaxScriptPage();
      } else {
        this.savingInProgress = true;
        await this.SAVE_SCRIPT_CUTS(this.linePartCuts);
        this.resetCutsToSaved();
        this.savingInProgress = false;
      }
    },
    validateDebugState(name) {
      const { $dirty, $error } = this.$v.debugFormState[name];
      return $dirty ? !$error : null;
    },
    async generateDebugScript(event) {
      this.$v.debugFormState.$touch();
      if (this.$v.debugFormState.$anyError) {
        event.preventDefault();
        return;
      }

      const firstActId = this.CURRENT_SHOW.first_act_id;
      if (firstActId == null) {
        this.$toast.error('Unable to generate script as first act has not been set!');
        return;
      }

      const firstAct = this.ACT_LIST.find((act) => (act.id === firstActId));
      if (firstAct == null) {
        log.error(`Could not find act with ID ${firstActId}`);
        this.$toast.error('Unable to generate script!');
        return;
      }

      if (this.CHARACTER_LIST.length === 0 && this.CHARACTER_GROUP_LIST.length === 0) {
        this.$toast.error('Unable to generate script as no characters or '
          + 'character groups created!');
        return;
      }

      let currentAct = firstAct;
      /* eslint-disable no-await-in-loop */
      while (currentAct != null) {
        let currentScene = this.SCENE_BY_ID(currentAct.first_scene);
        while (currentScene != null) {
          for (let pageIter = 0; pageIter < this.debugFormState.pages; pageIter++) {
            for (let linesIter = 0; linesIter < this.debugFormState.linesPerPage; linesIter++) {
              this.addNewLine();
              const scriptAtPage = this.TMP_SCRIPT[this.currentEditPageKey];
              const line = scriptAtPage[scriptAtPage.length - 1];
              line.act_id = currentAct.id;
              line.scene_id = currentScene.id;
              const totalCharacters = this.CHARACTER_GROUP_LIST.length + this.CHARACTER_LIST.length;
              const partLength = (randInt(0, 100) % Math.min(totalCharacters, 4)) + 1;
              for (let partIter = 0; partIter < partLength; partIter++) {
                const characterGroup = this.CHARACTER_GROUP_LIST.length > 0 && randInt(0, 100) > 75;
                line.line_parts.push({
                  id: null,
                  line_id: null,
                  part_index: partIter,
                  character_id: characterGroup ? null : sample(this.CHARACTER_LIST).id,
                  character_group_id: characterGroup ? sample(this.CHARACTER_GROUP_LIST).id : null,
                  line_text: `Act: ${currentAct.name}. Scene: ${currentScene.name}. Page: ${this.currentEditPage}. Line: ${linesIter + 1}. Part: ${partIter + 1}`,
                });
              }
              this.doneEditingLine(this.currentEditPage, scriptAtPage.length - 1);
            }
            await this.incrPage();
          }
          currentScene = this.SCENE_BY_ID(currentScene.next_scene);
        }
        /* eslint-enable no-await-in-loop */
        if (currentAct.next_act != null) {
          currentAct = this.ACT_BY_ID(currentAct.next_act);
        } else {
          currentAct = null;
        }
      }
      this.decrPage();
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
    },
    ...mapMutations(['REMOVE_PAGE', 'ADD_BLANK_LINE', 'SET_LINE', 'DELETE_LINE', 'RESET_DELETED',
      'SET_CUT_MODE', 'INSERT_BLANK_LINE', 'RESET_INSERTED']),
    ...mapActions(['GET_SCENE_LIST', 'GET_ACT_LIST', 'GET_CHARACTER_LIST',
      'GET_CHARACTER_GROUP_LIST', 'LOAD_SCRIPT_PAGE', 'ADD_BLANK_PAGE', 'GET_SCRIPT_CONFIG_STATUS',
      'RESET_TO_SAVED', 'SAVE_NEW_PAGE', 'SAVE_CHANGED_PAGE', 'GET_CUTS', 'SAVE_SCRIPT_CUTS']),
  },
  computed: {
    canGenerateDebugScript() {
      return this.DEBUG_MODE_ENABLED && this.currentMaxPage === 0 && !this.scriptChanges;
    },
    currentEditPageKey() {
      return this.currentEditPage.toString();
    },
    scriptChanges() {
      if (this.IS_CUT_MODE) {
        return Object.keys(diff(this.SCRIPT_CUTS, this.linePartCuts)).length > 0;
      }
      let hasChanges = false;
      Object.keys(this.TMP_SCRIPT).forEach(function (pageNo) {
        const lineDiff = diff(this.GET_SCRIPT_PAGE(pageNo), this.TMP_SCRIPT[pageNo]);
        if (Object.keys(lineDiff).length > 0 || this.DELETED_LINES(pageNo).length > 0
            || this.INSERTED_LINES(pageNo).length > 0) {
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
    canEdit() {
      return this.INTERNAL_UUID === this.CURRENT_EDITOR;
    },
    canSave() {
      if (this.IS_CUT_MODE) {
        return this.scriptChanges;
      }
      return (this.scriptChanges && this.editPages.length === 0);
    },
    ...mapGetters(['CURRENT_SHOW', 'TMP_SCRIPT', 'ACT_LIST', 'SCENE_LIST', 'CHARACTER_LIST',
      'CHARACTER_GROUP_LIST', 'CAN_REQUEST_EDIT', 'CURRENT_EDITOR', 'INTERNAL_UUID',
      'GET_SCRIPT_PAGE', 'DEBUG_MODE_ENABLED', 'DELETED_LINES', 'SCENE_BY_ID', 'ACT_BY_ID',
      'IS_CUT_MODE', 'SCRIPT_CUTS', 'INSERTED_LINES']),
  },
  watch: {
    currentEditPage(val) {
      localStorage.setItem('scriptEditPage', val);
    },
  },
};
</script>

<style scoped>

</style>
