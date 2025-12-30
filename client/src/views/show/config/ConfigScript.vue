<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab
            title="Revisions"
            active
          >
            <!-- Revision Graph Card -->
            <b-card
              class="mb-3"
              :class="{ 'collapsed-card': !graphCollapsed }"
              header-tag="header"
            >
              <template #header>
                <div class="d-flex justify-content-between align-items-center">
                  <h6 class="mb-0">
                    Revision Branch Graph
                  </h6>
                  <b-button
                    size="sm"
                    variant="secondary"
                    @click="graphCollapsed = !graphCollapsed"
                  >
                    <b-icon-chevron-up v-if="!graphCollapsed" />
                    <b-icon-chevron-down v-else />
                  </b-button>
                </div>
              </template>
              <b-collapse
                v-model="graphCollapsed"
                visible
              >
                <revision-graph
                  :revisions="SCRIPT_REVISIONS"
                  :current-revision-id="CURRENT_REVISION"
                  :selected-revision-id="selectedRevisionId"
                  :loading="false"
                  @node-click="handleNodeClick"
                />
              </b-collapse>
            </b-card>

            <b-table
              id="revisions-table"
              :items="SCRIPT_REVISIONS"
              :fields="revisionColumns"
              show-empty
            >
              <template #cell(current)="data">
                <b-icon-check-square-fill
                  v-if="data.item.id === $store.state.script.currentRevision"
                  variant="success"
                />
                <b-button-group v-else>
                  <b-button
                    v-if="IS_SCRIPT_EDITOR"
                    variant="warning"
                    :disabled="!canChangeRevisions ||
                      data.item.id === $store.state.script.currentRevision ||
                      submittingLoadRevision || submittingNewRevision || deletingRevision"
                    @click="loadRevision(data)"
                  >
                    Load
                  </b-button>
                </b-button-group>
              </template>
              <template #cell(previous_revision_id)="data">
                <p v-if="data.item.previous_revision_id != null">
                  {{
                    SCRIPT_REVISIONS.find((rev) => (
                      rev.id === data.item.previous_revision_id)).revision
                  }}
                </p>
                <p v-else>
                  N/A
                </p>
              </template>
              <template #cell(btn)="data">
                <b-button-group v-if="IS_SCRIPT_EDITOR && data.item.revision !== 1">
                  <b-button
                    variant="warning"
                    :disabled="!canChangeRevisions || submittingLoadRevision || submittingNewRevision || deletingRevision"
                    @click="openEditRevForm(data)"
                  >
                    Edit
                  </b-button>
                  <b-button
                    variant="danger"
                    :disabled="!canChangeRevisions || submittingLoadRevision || submittingNewRevision || deletingRevision"
                    @click="deleteRev(data)"
                  >
                    Delete
                  </b-button>
                </b-button-group>
              </template>
              <template #custom-foot="data">
                <b-tr>
                  <b-td>
                    <b-button
                      v-if="IS_SCRIPT_EDITOR"
                      v-b-modal.new-revision
                      variant="outline-success"
                      :disabled="!canChangeRevisions || submittingLoadRevision || submittingNewRevision || deletingRevision"
                    >
                      New Revision
                    </b-button>
                  </b-td>
                  <b-td />
                  <b-td />
                  <b-td />
                  <b-td />
                  <b-td />
                  <b-td />
                </b-tr>
              </template>
            </b-table>
          </b-tab>
          <b-tab title="Stage Direction Styles">
            <stage-direction-configs />
          </b-tab>
          <b-tab title="Script">
            <script-config />
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
    <b-modal
      id="new-revision"
      ref="new-revision"
      title="Add New Revision"
      size="md"
      :ok-disabled="$v.newRevFormState.$invalid || submittingNewRevision"
      @show="resetNewRevForm"
      @hidden="resetNewRevForm"
      @ok="onSubmitNewRev"
    >
      <b-alert show>
        <p>
          This will create a new revision of the script based on the current revision, and set it
          as the new current revision.
        </p>
      </b-alert>
      <b-form
        ref="new-act-form"
        @submit.stop.prevent="onSubmitNewRev"
      >
        <b-form-group
          id="description-input-group"
          label="Description"
          label-for="description-input"
        >
          <b-form-input
            id="description-input"
            v-model="$v.newRevFormState.description.$model"
            name="description-input"
            :state="validateNewRevState('description')"
            aria-describedby="description-feedback"
          />
          <b-form-invalid-feedback
            id="description-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>

    <!-- Revision Detail Modal -->
    <revision-detail-modal
      modal-id="revision-detail"
      :revision="selectedRevision"
      :revisions="SCRIPT_REVISIONS"
      :current-revision-id="CURRENT_REVISION"
      :can-edit="IS_SCRIPT_EDITOR && canChangeRevisions"
      :submitting="modalSubmitting"
      @load-revision="handleModalLoadRevision"
      @create-from="handleModalCreateFrom"
      @close="handleModalClose"
      @hidden="handleModalHidden"
    />

    <!-- Create Branch Modal -->
    <b-modal
      id="create-branch-modal"
      ref="create-branch-modal"
      title="Create Revision Branch"
      size="md"
      :ok-disabled="$v.branchFormState.$invalid || submittingBranch"
      @show="setupBranchForm"
      @hidden="resetBranchForm"
      @ok="onSubmitBranch"
    >
      <b-alert
        show
        :variant="branchFormState.isCurrentRevision ? 'info' : 'warning'"
      >
        <p v-if="branchFormState.isCurrentRevision">
          This will create a new revision based on revision {{ branchFormState.sourceRevision }}
          (current revision) and set it as the new current revision.
        </p>
        <p v-else>
          This will create a new branch from revision {{ branchFormState.sourceRevision }}.
          The new revision will NOT be set as current.
        </p>
      </b-alert>
      <b-form
        ref="branch-form"
        @submit.stop.prevent="onSubmitBranch"
      >
        <b-form-group
          id="branch-description-input-group"
          label="Description"
          label-for="branch-description-input"
        >
          <b-form-input
            id="branch-description-input"
            v-model="$v.branchFormState.description.$model"
            name="branch-description-input"
            :state="validateBranchState('description')"
            aria-describedby="branch-description-feedback"
          />
          <b-form-invalid-feedback
            id="branch-description-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import { required } from 'vuelidate/lib/validators';
import log from 'loglevel';
import ScriptConfig from '@/vue_components/show/config/script/ScriptEditor.vue';
import StageDirectionStyles from '@/vue_components/show/config/script/StageDirectionStyles.vue';
import RevisionGraph from '@/vue_components/show/config/script/RevisionGraph.vue';
import RevisionDetailModal from '@/vue_components/show/config/script/RevisionDetailModal.vue';

export default {
  name: 'ConfigScript',
  components: {
    ScriptConfig,
    StageDirectionConfigs: StageDirectionStyles,
    RevisionGraph,
    RevisionDetailModal,
  },
  data() {
    return {
      revisionColumns: [
        { key: 'current', label: 'Current' },
        'revision',
        'created_at',
        'edited_at',
        'description',
        { key: 'previous_revision_id', label: 'Previous Revision' },
        { key: 'btn', label: '' },
      ],
      newRevFormState: {
        description: '',
      },
      branchFormState: {
        description: '',
        sourceRevisionId: null,
        sourceRevision: null,
        isCurrentRevision: false,
      },
      submittingNewRevision: false,
      submittingBranch: false,
      submittingLoadRevision: false,
      deletingRevision: false,
      // Graph state
      graphCollapsed: this.getGraphCollapseState(),
      selectedRevisionId: null,
      selectedRevision: null,
      modalSubmitting: false,
    };
  },
  validations: {
    newRevFormState: {
      description: {
        required,
      },
    },
    branchFormState: {
      description: {
        required,
      },
    },
  },
  computed: {
    ...mapGetters(['SCRIPT_REVISIONS', 'CURRENT_REVISION', 'CURRENT_EDITOR', 'INTERNAL_UUID', 'IS_SCRIPT_EDITOR']),
    canChangeRevisions() {
      return this.CURRENT_EDITOR == null || this.CURRENT_EDITOR === this.INTERNAL_UUID;
    },
  },
  watch: {
    graphCollapsed(newVal) {
      localStorage.setItem('revisionGraphCollapsed', JSON.stringify(newVal));
    },
  },
  async beforeMount() {
    await this.GET_SCRIPT_CONFIG_STATUS();
  },
  async mounted() {
    await this.GET_SCRIPT_REVISIONS();
  },
  methods: {
    resetNewRevForm() {
      this.newRevFormState = {
        description: '',
      };
      this.submittingNewRevision = false;

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    validateNewRevState(name) {
      const { $dirty, $error } = this.$v.newRevFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNewRev(event) {
      this.$v.newRevFormState.$touch();
      if (this.$v.newRevFormState.$anyError || this.submittingNewRevision) {
        event.preventDefault();
        return;
      }

      this.submittingNewRevision = true;
      try {
        await this.ADD_SCRIPT_REVISION(this.newRevFormState);
        this.$bvModal.hide('new-revision');
        this.resetNewRevForm();
      } catch (error) {
        log.error('Error submitting new revision:', error);
        event.preventDefault();
      } finally {
        this.submittingNewRevision = false;
      }
    },
    async loadRevision(revision) {
      if (this.submittingLoadRevision) {
        return;
      }

      const msg = `Are you sure you want to load revision ${revision.item.revision}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.submittingLoadRevision = true;
        try {
          await this.LOAD_SCRIPT_REVISION(revision.item.id);
        } catch (error) {
          log.error('Error loading revision:', error);
        } finally {
          this.submittingLoadRevision = false;
        }
      }
    },
    openEditRevForm(revision) {

    },
    async deleteRev(revision) {
      if (this.deletingRevision) {
        return;
      }

      let msg = `Are you sure you want to delete revision ${revision.item.revision}?`;
      if (this.CURRENT_REVISION === revision.item.id) {
        msg = `${msg}  This will load the previous revision, or first revision if this is not available.`;
      }
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingRevision = true;
        try {
          await this.DELETE_SCRIPT_REVISION(revision.item.id);
        } catch (error) {
          log.error('Error deleting revision:', error);
        } finally {
          this.deletingRevision = false;
        }
      }
    },
    // Graph interaction handlers
    getGraphCollapseState() {
      const saved = localStorage.getItem('revisionGraphCollapsed');
      return saved !== null ? JSON.parse(saved) : false;
    },
    handleNodeClick(revision) {
      this.selectedRevisionId = revision.id;
      this.selectedRevision = revision;
      this.$bvModal.show('revision-detail');
    },
    async handleModalLoadRevision(revision) {
      const msg = `Are you sure you want to load revision ${revision.revision}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.modalSubmitting = 'load';
        try {
          await this.LOAD_SCRIPT_REVISION(revision.id);
          this.$bvModal.hide('revision-detail');
        } catch (error) {
          log.error('Error loading revision:', error);
        } finally {
          this.modalSubmitting = false;
        }
      }
    },
    handleModalCreateFrom(revision) {
      // Set up the branch form state with the source revision info
      this.branchFormState.sourceRevisionId = revision.id;
      this.branchFormState.sourceRevision = revision.revision;
      this.branchFormState.isCurrentRevision = revision.id === this.CURRENT_REVISION;

      // Show the branch creation modal
      this.$bvModal.show('create-branch-modal');
    },
    setupBranchForm() {
      // Reset only the description field, preserving the source revision info
      // that was set in handleModalCreateFrom
      this.branchFormState.description = '';
      this.submittingBranch = false;

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    resetBranchForm() {
      this.branchFormState = {
        description: '',
        sourceRevisionId: null,
        sourceRevision: null,
        isCurrentRevision: false,
      };
      this.submittingBranch = false;

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    validateBranchState(name) {
      const { $dirty, $error } = this.$v.branchFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitBranch(event) {
      this.$v.branchFormState.$touch();
      if (this.$v.branchFormState.$anyError || this.submittingBranch) {
        event.preventDefault();
        return;
      }

      this.submittingBranch = true;
      try {
        await this.ADD_SCRIPT_REVISION({
          description: this.branchFormState.description,
          parent_revision_id: this.branchFormState.sourceRevisionId,
          set_as_current: this.branchFormState.isCurrentRevision,
        });
        this.$bvModal.hide('create-branch-modal');
        this.$bvModal.hide('revision-detail');
        this.resetBranchForm();
      } catch (error) {
        log.error('Error creating branch:', error);
        event.preventDefault();
      } finally {
        this.submittingBranch = false;
      }
    },
    handleModalClose() {
      this.$bvModal.hide('revision-detail');
    },
    handleModalHidden() {
      this.selectedRevisionId = null;
      this.selectedRevision = null;
      this.modalSubmitting = false;
    },
    ...mapActions(['GET_SCRIPT_REVISIONS', 'ADD_SCRIPT_REVISION', 'LOAD_SCRIPT_REVISION',
      'DELETE_SCRIPT_REVISION', 'GET_SCRIPT_CONFIG_STATUS']),
  },
};
</script>

<style scoped>
/* Remove card body padding when collapsed to minimize visual footprint */
.collapsed-card >>> .card-body {
  padding: 0;
}
</style>
