<template>
  <b-container class="mx-0 px-0" fluid>
    <b-row class="script-row">
      <b-col cols="2">
        <b-button-group>
          <b-button v-b-modal.go-to-page-cue-editor variant="success"> Go to Page </b-button>
          <b-button v-b-modal.jump-to-cue variant="success"> Go to Cue </b-button>
          <b-button variant="outline-warning" @click="$bvModal.show('cue-renumber-modal')">
            Renumber Cues
          </b-button>
        </b-button-group>
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
      <b-col cols="2" />
    </b-row>
    <b-row class="script-row">
      <b-col cols="3"> Cues </b-col>
      <b-col>Script</b-col>
    </b-row>
    <hr />
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
            :stage-direction-styles="STAGE_DIRECTION_STYLES"
            :stage-direction-style-overrides="STAGE_DIRECTION_STYLE_OVERRIDES"
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
    <jump-to-cue-modal @navigate="handleJumpToCue" />
    <cue-renumber-modal />
    <b-modal
      id="go-to-page-cue-editor"
      ref="go-to-page-cue-editor"
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
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters, mapMutations, mapActions } from 'vuex';
import log from 'loglevel';

import { makeURL } from '@/js/utils';
import ScriptLineCueEditor from '@/vue_components/show/config/cues/ScriptLineCueEditor.vue';
import JumpToCueModal from '@/vue_components/show/config/cues/JumpToCueModal.vue';
import CueRenumberModal from '@/vue_components/show/config/cues/CueRenumberModal.vue';
import { minValue, required } from 'vuelidate/lib/validators';
import { notNull, notNullAndGreaterThanZero } from '@/js/customValidators';

export default defineComponent({
  name: 'CueEditor',
  components: { ScriptLineCueEditor, JumpToCueModal, CueRenumberModal },
  data() {
    return {
      currentEditPage: 1,
      editPages: [] as any[],
      blankLineObj: {
        id: null,
        act_id: null,
        scene_id: null,
        page: null,
        line_parts: [],
      },
      curSavePage: null as number | null,
      totalSavePages: null as number | null,
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
  computed: {
    currentEditPageKey(): string {
      return this.currentEditPage.toString();
    },
    saveProgressVariant(): string {
      if (!this.savingInProgress) {
        return this.saveError ? 'danger' : 'success';
      }
      return 'primary';
    },
    ...mapGetters([
      'CURRENT_SHOW',
      'ACT_LIST',
      'SCENE_LIST',
      'CHARACTER_LIST',
      'CHARACTER_GROUP_LIST',
      'CAN_REQUEST_EDIT',
      'CURRENT_EDITOR',
      'INTERNAL_UUID',
      'GET_SCRIPT_PAGE',
      'CUE_TYPES',
      'SCRIPT_CUES',
      'SCRIPT_CUTS',
      'STAGE_DIRECTION_STYLES',
      'STAGE_DIRECTION_STYLE_OVERRIDES',
      'CURRENT_USER',
    ]),
  },
  watch: {
    currentEditPage(val: number): void {
      localStorage.setItem('cueEditPage', val.toString());
    },
  },
  async beforeMount(): Promise<void> {
    await Promise.all([
      (this as any).GET_CURRENT_USER().then(() => {
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
      (this as any).GET_CUE_TYPES(),
      (this as any).LOAD_CUES(),
      (this as any).GET_CUTS(),
      (this as any).GET_STAGE_DIRECTION_STYLES(),
      this.getMaxScriptPage(),
    ]);

    const storedPage = localStorage.getItem('cueEditPage');
    if (storedPage != null) {
      this.currentEditPage = parseInt(storedPage, 10);
    }
    await this.goToPageInner(this.currentEditPage);
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
    async stopEditing(): Promise<void> {
      (this as any).$socket.sendObj({
        OP: 'STOP_SCRIPT_EDIT',
        DATA: {},
      });
    },
    async decrPage(): Promise<void> {
      if (this.currentEditPage > 1) {
        const targetPage = this.currentEditPage - 1;
        await (this as any).LOAD_SCRIPT_PAGE(targetPage);
        this.currentEditPage--;
        await (this as any).LOAD_SCRIPT_PAGE(this.currentEditPage - 1);
      }
    },
    async incrPage(): Promise<void> {
      this.currentEditPage++;
      await (this as any).LOAD_SCRIPT_PAGE(this.currentEditPage + 1);
    },
    getCuesForLine(line: any): any[] {
      if (Object.keys((this as any).SCRIPT_CUES).includes(line.id.toString())) {
        return (this as any).SCRIPT_CUES[line.id.toString()];
      }
      return [];
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
      if (pageNo > 1) {
        await (this as any).LOAD_SCRIPT_PAGE(parseInt(pageNo.toString(), 10) - 1);
      }
      await (this as any).LOAD_SCRIPT_PAGE(pageNo);
      this.currentEditPage = pageNo;
      await (this as any).LOAD_SCRIPT_PAGE(parseInt(pageNo.toString(), 10) + 1);
    },
    async handleJumpToCue(pageNumber: number): Promise<void> {
      await this.goToPageInner(pageNumber);
      (this as any).$bvModal.hide('jump-to-cue');
    },
    ...mapMutations(['REMOVE_PAGE', 'ADD_BLANK_LINE', 'SET_LINE']),
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
      'GET_CUE_TYPES',
      'LOAD_CUES',
      'GET_CUTS',
      'GET_STAGE_DIRECTION_STYLES',
      'GET_STAGE_DIRECTION_STYLE_OVERRIDES',
      'GET_CUE_COLOUR_OVERRIDES',
      'GET_CURRENT_USER',
    ]),
  },
});
</script>
