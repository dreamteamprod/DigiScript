<template>
  <b-container class="mx-0 px-0" fluid>
    <b-row class="script-row">
      <b-col cols="2"></b-col>
      <b-col cols="2" style="text-align: right">
        <b-button variant="success" @click="decrPage"
                  :disabled="currentEditPage === 1">
          Prev Page
        </b-button>
      </b-col>
      <b-col cols="4">
        <p>Current Page: {{ currentEditPage }}</p>
      </b-col>
      <b-col cols="2" style="text-align: left" >
        <b-button variant="success" @click="incrPage">
          Next Page
        </b-button>
      </b-col>
      <b-col cols="2">
        <b-button-group>
          <b-button v-if="INTERNAL_UUID !== CURRENT_EDITOR"
                  variant="warning"
                  :disabled="!CAN_REQUEST_EDIT"
                  @click="requestEdit">
            Begin Editing
          </b-button>
          <b-button v-else
                    variant="warning"
                    @click="stopEditing">
            Stop Editing
          </b-button>
        </b-button-group>
      </b-col>
    </b-row>
    <b-row class="script-row">
      <b-col cols="1">Act</b-col>
      <b-col cols="1">Scene</b-col>
      <b-col>Line</b-col>
    </b-row>
    <hr />
    <b-row class="script-row">
      <b-col cols="12">
        <template v-for="(line, index) in TMP_SCRIPT[currentEditPage]">
          <script-line-editor
            v-if="editPages.includes(`page_${currentEditPage}_line_${index}`)"
            :key="`page_${currentEditPage}_line_${index}`"
            :line-index="index"
            :acts="ACT_LIST"
            :scenes="SCENE_LIST"
            :characters="CHARACTER_LIST"
            :character-groups="CHARACTER_GROUP_LIST"
            :value="TMP_SCRIPT[currentEditPage][index]"
            @input="lineChange(line, index)"
            @doneEditing="doneEditing(currentEditPage, index)"
          />
          <script-line-viewer
            v-else
            :key="`page_${currentEditPage}_line_${index}`"
            :line-index="index"
            :line="TMP_SCRIPT[currentEditPage][index]"
            :acts="ACT_LIST"
            :scenes="SCENE_LIST"
            :characters="CHARACTER_LIST"
            :character-groups="CHARACTER_GROUP_LIST"
            :previous-line="TMP_SCRIPT[currentEditPage][index - 1]"
            @editLine="beginEditing(currentEditPage, index)"
          />
        </template>
      </b-col>
    </b-row>
    <b-row class="script-row pt-1">
      <b-col cols="10" class="ml-auto">
        <b-button @click="addNewLine" style="float: right"
                  v-show="INTERNAL_UUID === CURRENT_EDITOR">
          Add line
        </b-button>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapGetters, mapMutations, mapActions } from 'vuex';
import { diff } from 'deep-object-diff';
import ScriptLineEditor from '@/vue_components/show/config/ScriptLineEditor.vue';
import ScriptLineViewer from '@/vue_components/show/config/ScriptLineViewer.vue';

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
        next_line_id: null,
        page: null,
        line_parts: [],
      },
    };
  },
  async beforeMount() {
    // Config status
    await this.GET_SCRIPT_CONFIG_STATUS();
    // Show details
    await this.GET_ACT_LIST();
    await this.GET_SCENE_LIST();
    await this.GET_CHARACTER_LIST();
    await this.GET_CHARACTER_GROUP_LIST();
    // Initialisation of page data
    await this.LOAD_SCRIPT_PAGE(this.currentEditPage);
    await this.LOAD_SCRIPT_PAGE(this.currentEditPage + 1);
    this.ADD_BLANK_PAGE(this.currentEditPage);
  },
  methods: {
    requestEdit() {
      this.$socket.sendObj({
        OP: 'REQUEST_SCRIPT_EDIT',
        DATA: {},
      });
    },
    async stopEditing() {
      if (this.scriptChanges) {
        const msg = 'Are you sure you want to stop editing the script? ' +
          'This will cause all unsaved changes to be lost';
        const action = await this.$bvModal.msgBoxConfirm(msg, {});
        if (action === false) {
          return;
        }
      }
      this.RESET_TO_SAVED(this.currentEditPage);
      this.$socket.sendObj({
        OP: 'STOP_SCRIPT_EDIT',
        DATA: {},
      });
    },
    decrPage() {
      if (this.currentEditPage > 1) {
        if (!Object.keys(this.TMP_SCRIPT).includes((this.currentEditPage - 1).toString())) {
          this.ADD_BLANK_PAGE(this.currentEditPage - 1);
        }
        if (this.TMP_SCRIPT[this.currentEditPageKey].length === 0) {
          this.REMOVE_PAGE(this.currentEditPage);
        }
        this.currentEditPage--;
      }
    },
    async incrPage() {
      this.currentEditPage++;
      if (!Object.keys(this.TMP_SCRIPT).includes(this.currentEditPageKey)) {
        this.ADD_BLANK_PAGE(this.currentEditPage);
      }
      await this.LOAD_SCRIPT_PAGE(this.currentEditPage + 1);
    },
    addNewLine() {
      this.ADD_BLANK_LINE({
        pageNo: this.currentEditPage,
        lineObj: this.blankLineObj,
      });
      this.editPages.push(`page_${this.currentEditPage}_line_${this.TMP_SCRIPT[this.currentEditPageKey].length - 1}`);
    },
    lineChange(line, index) {
      this.SET_LINE({
        pageNo: this.currentEditPage,
        lineIndex: index,
        lineObj: line,
      });
    },
    beginEditing(pageIndex, lineIndex) {
      const index = this.editPages.indexOf(`page_${pageIndex}_line_${lineIndex}`);
      if (index === -1) {
        this.editPages.push(`page_${pageIndex}_line_${lineIndex}`);
      }
    },
    doneEditing(pageIndex, lineIndex) {
      const index = this.editPages.indexOf(`page_${pageIndex}_line_${lineIndex}`);
      if (index !== -1) {
        this.editPages.splice(index, 1);
      }
    },
    ...mapMutations(['REMOVE_PAGE', 'ADD_BLANK_LINE', 'SET_LINE']),
    ...mapActions(['GET_SCENE_LIST', 'GET_ACT_LIST', 'GET_CHARACTER_LIST',
      'GET_CHARACTER_GROUP_LIST', 'LOAD_SCRIPT_PAGE', 'ADD_BLANK_PAGE', 'GET_SCRIPT_CONFIG_STATUS',
      'RESET_TO_SAVED']),
  },
  computed: {
    currentEditPageKey() {
      return this.currentEditPage.toString();
    },
    scriptChanges() {
      let hasChanges = false;
      Object.keys(this.TMP_SCRIPT).forEach(function (pageNo) {
        const lineDiff = diff(this.GET_SCRIPT_PAGE(pageNo), this.TMP_SCRIPT[pageNo]);
        console.log(lineDiff);
        if (Object.keys(lineDiff).length > 0) {
          hasChanges = true;
        }
      }, this);
      return hasChanges;
    },
    ...mapGetters(['TMP_SCRIPT', 'ACT_LIST', 'SCENE_LIST', 'CHARACTER_LIST', 'CHARACTER_GROUP_LIST',
      'CAN_REQUEST_EDIT', 'CURRENT_EDITOR', 'INTERNAL_UUID', 'GET_SCRIPT_PAGE']),
  },
};
</script>

<style scoped>

</style>
