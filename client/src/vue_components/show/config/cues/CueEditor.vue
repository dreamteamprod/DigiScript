<template>
  <b-container
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
      <b-col cols="2" />
    </b-row>
    <b-row class="script-row">
      <b-col cols="3">
        Cues
      </b-col>
      <b-col>Script</b-col>
    </b-row>
    <hr>
    <b-row class="script-row">
      <b-col cols="12">
        <template v-for="(line, index) in GET_SCRIPT_PAGE(currentEditPage)">
          <script-line-cue-editor
            :key="`page_${currentEditPage}_line_${index}`"
            :line-index="index"
            :line="line"
            :acts="ACT_LIST"
            :scenes="SCENE_LIST"
            :characters="CHARACTER_LIST"
            :character-groups="CHARACTER_GROUP_LIST"
            :previous-line="GET_SCRIPT_PAGE(currentEditPage)[index - 1]"
            :cue-types="CUE_TYPES"
            :cues="getCuesForLine(line)"
            :line-part-cuts="SCRIPT_CUTS"
          />
        </template>
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
  </b-container>
</template>

<script>
import { mapGetters, mapMutations, mapActions } from 'vuex';
import log from 'loglevel';

import { makeURL } from '@/js/utils';
import ScriptLineCueEditor from '@/vue_components/show/config/cues/ScriptLineCueEditor.vue';
import { minValue, required } from 'vuelidate/lib/validators';
import { notNull, notNullAndGreaterThanZero } from '@/js/customValidators';

export default {
  name: 'CueEditor',
  components: { ScriptLineCueEditor },
  data() {
    return {
      currentEditPage: 1,
      editPages: [],
      blankLineObj: {
        id: null,
        act_id: null,
        scene_id: null,
        page: null,
        line_parts: [],
      },
      curSavePage: null,
      totalSavePages: null,
      savingInProgress: false,
      saveError: false,
      currentMaxPage: 1,
      changingPage: false,
      pageInputFormState: {
        pageNo: 1,
      },
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
  async beforeMount() {
    // Config status
    await this.GET_SCRIPT_CONFIG_STATUS();
    // Show details
    await this.GET_ACT_LIST();
    await this.GET_SCENE_LIST();
    await this.GET_CHARACTER_LIST();
    await this.GET_CHARACTER_GROUP_LIST();
    await this.GET_CUE_TYPES();
    await this.LOAD_CUES();
    await this.GET_CUTS();

    // Get the max page of the saved version of the script
    await this.getMaxScriptPage();

    // Initialisation of page data
    // Initialisation of page data
    const storedPage = localStorage.getItem('cueEditPage');
    if (storedPage != null) {
      this.currentEditPage = parseInt(storedPage, 10);
    }
    await this.goToPageInner(this.currentEditPage);
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
    async stopEditing() {
      this.$socket.sendObj({
        OP: 'STOP_SCRIPT_EDIT',
        DATA: {},
      });
    },
    decrPage() {
      if (this.currentEditPage > 1) {
        this.currentEditPage--;
      }
    },
    async incrPage() {
      this.currentEditPage++;
      // Pre-load next page
      await this.LOAD_SCRIPT_PAGE(this.currentEditPage + 1);
    },
    getCuesForLine(line) {
      if (Object.keys(this.SCRIPT_CUES).includes(line.id.toString())) {
        return this.SCRIPT_CUES[line.id.toString()];
      }
      return [];
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
      await this.LOAD_SCRIPT_PAGE(parseInt(pageNo, 10) + 1);
    },
    ...mapMutations(['REMOVE_PAGE', 'ADD_BLANK_LINE', 'SET_LINE']),
    ...mapActions(['GET_SCENE_LIST', 'GET_ACT_LIST', 'GET_CHARACTER_LIST',
      'GET_CHARACTER_GROUP_LIST', 'LOAD_SCRIPT_PAGE', 'ADD_BLANK_PAGE', 'GET_SCRIPT_CONFIG_STATUS',
      'RESET_TO_SAVED', 'SAVE_NEW_PAGE', 'SAVE_CHANGED_PAGE', 'GET_CUE_TYPES', 'LOAD_CUES',
      'GET_CUTS']),
  },
  computed: {
    currentEditPageKey() {
      return this.currentEditPage.toString();
    },
    saveProgressVariant() {
      if (!this.savingInProgress) {
        return this.saveError ? 'danger' : 'success';
      }
      return 'primary';
    },
    ...mapGetters(['CURRENT_SHOW', 'ACT_LIST', 'SCENE_LIST', 'CHARACTER_LIST',
      'CHARACTER_GROUP_LIST', 'CAN_REQUEST_EDIT', 'CURRENT_EDITOR', 'INTERNAL_UUID',
      'GET_SCRIPT_PAGE', 'DEBUG_MODE_ENABLED', 'CUE_TYPES', 'SCRIPT_CUES', 'SCRIPT_CUTS']),
  },
  watch: {
    currentEditPage(val) {
      localStorage.setItem('cueEditPage', val);
    },
  },
};
</script>
