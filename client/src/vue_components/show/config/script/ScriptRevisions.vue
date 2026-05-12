<template>
  <span>
    <b-card class="mb-3" :class="{ 'collapsed-card': !graphCollapsed }" header-tag="header">
      <template #header>
        <div class="d-flex justify-content-between align-items-center">
          <h6 class="mb-0">Revision Branch Graph</h6>
          <b-button size="sm" variant="secondary" @click="graphCollapsed = !graphCollapsed">
            <b-icon-chevron-up v-if="!graphCollapsed" />
            <b-icon-chevron-down v-else />
          </b-button>
        </div>
      </template>
      <b-collapse v-model="graphCollapsed" visible>
        <revision-graph
          v-show="graphCollapsed"
          :revisions="SCRIPT_REVISIONS"
          :current-revision-id="CURRENT_REVISION"
          :selected-revision-id="selectedRevisionId"
          :loading="false"
          @node-click="handleNodeClick"
        />
      </b-collapse>
    </b-card>

    <b-table id="revisions-table" :items="SCRIPT_REVISIONS" :fields="revisionColumns" show-empty>
      <template #cell(current)="data">
        <b-icon-check-square-fill v-if="data.item.id === CURRENT_REVISION" variant="success" />
        <b-button-group v-else>
          <b-button
            v-if="IS_SCRIPT_EDITOR"
            variant="warning"
            :disabled="
              !canChangeRevisions ||
              data.item.id === CURRENT_REVISION ||
              submittingLoadRevision ||
              submittingNewRevision ||
              deletingRevision
            "
            @click="loadRevision(data)"
          >
            Load
          </b-button>
        </b-button-group>
      </template>
      <template #cell(previous_revision_id)="data">
        <p v-if="data.item.previous_revision_id != null">
          {{ SCRIPT_REVISIONS.find((rev) => rev.id === data.item.previous_revision_id).revision }}
        </p>
        <p v-else>N/A</p>
      </template>
      <template #cell(btn)="data">
        <b-button-group v-if="IS_SCRIPT_EDITOR && data.item.revision !== 1">
          <b-button
            variant="warning"
            :disabled="
              !canChangeRevisions ||
              submittingLoadRevision ||
              submittingNewRevision ||
              deletingRevision
            "
            @click="openEditRevForm(data)"
          >
            Edit
          </b-button>
          <b-button
            variant="danger"
            :disabled="
              !canChangeRevisions ||
              submittingLoadRevision ||
              submittingNewRevision ||
              deletingRevision
            "
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
              :disabled="
                !canChangeRevisions ||
                submittingLoadRevision ||
                submittingNewRevision ||
                deletingRevision
              "
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
          This will create a new revision of the script based on the current revision, and set it as
          the new current revision.
        </p>
      </b-alert>
      <b-form ref="new-revision-form" @submit.stop.prevent="onSubmitNewRev">
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
          <b-form-invalid-feedback id="description-feedback">
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
      <b-alert show :variant="branchFormState.isCurrentRevision ? 'info' : 'warning'">
        <p v-if="branchFormState.isCurrentRevision">
          This will create a new revision based on revision {{ branchFormState.sourceRevision }}
          (current revision) and set it as the new current revision.
        </p>
        <p v-else>
          This will create a new branch from revision {{ branchFormState.sourceRevision }}. The new
          revision will NOT be set as current.
        </p>
      </b-alert>
      <b-form ref="branch-form" @submit.stop.prevent="onSubmitBranch">
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
          <b-form-invalid-feedback id="branch-description-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </span>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapActions, mapGetters } from 'vuex';
import { required } from 'vuelidate/lib/validators';
import log from 'loglevel';
import RevisionGraph from '@/vue_components/show/config/script/RevisionGraph.vue';
import RevisionDetailModal from '@/vue_components/show/config/script/RevisionDetailModal.vue';

export default defineComponent({
  name: 'ScriptRevisions',
  components: { RevisionDetailModal, RevisionGraph },
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
        sourceRevisionId: null as number | null,
        sourceRevision: null as number | null,
        isCurrentRevision: false,
      },
      submittingNewRevision: false,
      submittingBranch: false,
      submittingLoadRevision: false,
      deletingRevision: false,
      // Graph state
      graphCollapsed: (this as any).getGraphCollapseState(),
      selectedRevisionId: null as number | null,
      selectedRevision: null as any,
      modalSubmitting: false as boolean | string,
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
    ...mapGetters([
      'SCRIPT_REVISIONS',
      'CURRENT_REVISION',
      'CURRENT_EDITOR',
      'INTERNAL_UUID',
      'IS_SCRIPT_EDITOR',
    ]),
    canChangeRevisions(): boolean {
      return (
        (this as any).CURRENT_EDITOR == null ||
        (this as any).CURRENT_EDITOR === (this as any).INTERNAL_UUID
      );
    },
  },
  watch: {
    graphCollapsed(newVal: boolean): void {
      localStorage.setItem('revisionGraphCollapsed', JSON.stringify(newVal));
    },
  },
  async beforeMount(): Promise<void> {
    await (this as any).GET_SCRIPT_CONFIG_STATUS();
  },
  methods: {
    resetNewRevForm(): void {
      this.newRevFormState = {
        description: '',
      };
      this.submittingNewRevision = false;

      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    validateNewRevState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.newRevFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNewRev(event: Event): Promise<void> {
      (this as any).$v.newRevFormState.$touch();
      if ((this as any).$v.newRevFormState.$anyError || this.submittingNewRevision) {
        event.preventDefault();
        return;
      }

      this.submittingNewRevision = true;
      try {
        await (this as any).ADD_SCRIPT_REVISION(this.newRevFormState);
        (this as any).$bvModal.hide('new-revision');
        this.resetNewRevForm();
      } catch (error) {
        log.error('Error submitting new revision:', error);
        event.preventDefault();
      } finally {
        this.submittingNewRevision = false;
      }
    },
    async loadRevision(revision: any): Promise<void> {
      if (this.submittingLoadRevision) {
        return;
      }

      const msg = `Are you sure you want to load revision ${revision.item.revision}?`;
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.submittingLoadRevision = true;
        try {
          await (this as any).LOAD_SCRIPT_REVISION(revision.item.id);
        } catch (error) {
          log.error('Error loading revision:', error);
        } finally {
          this.submittingLoadRevision = false;
        }
      }
    },
    openEditRevForm(_revision: any): void {},
    async deleteRev(revision: any): Promise<void> {
      if (this.deletingRevision) {
        return;
      }

      let msg = `Are you sure you want to delete revision ${revision.item.revision}?`;
      if ((this as any).CURRENT_REVISION === revision.item.id) {
        msg = `${msg}  This will load the previous revision, or first revision if this is not available.`;
      }
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingRevision = true;
        try {
          await (this as any).DELETE_SCRIPT_REVISION(revision.item.id);
        } catch (error) {
          log.error('Error deleting revision:', error);
        } finally {
          this.deletingRevision = false;
        }
      }
    },
    getGraphCollapseState(): boolean {
      const saved = localStorage.getItem('revisionGraphCollapsed');
      return saved !== null ? JSON.parse(saved) : false;
    },
    handleNodeClick(revision: any): void {
      this.selectedRevisionId = revision.id;
      this.selectedRevision = revision;
      (this as any).$bvModal.show('revision-detail');
    },
    async handleModalLoadRevision(revision: any): Promise<void> {
      const msg = `Are you sure you want to load revision ${revision.revision}?`;
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.modalSubmitting = 'load';
        try {
          await (this as any).LOAD_SCRIPT_REVISION(revision.id);
          (this as any).$bvModal.hide('revision-detail');
        } catch (error) {
          log.error('Error loading revision:', error);
        } finally {
          this.modalSubmitting = false;
        }
      }
    },
    handleModalCreateFrom(revision: any): void {
      this.branchFormState.sourceRevisionId = revision.id;
      this.branchFormState.sourceRevision = revision.revision;
      this.branchFormState.isCurrentRevision = revision.id === (this as any).CURRENT_REVISION;
      (this as any).$bvModal.show('create-branch-modal');
    },
    setupBranchForm(): void {
      this.branchFormState.description = '';
      this.submittingBranch = false;

      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    resetBranchForm(): void {
      this.branchFormState = {
        description: '',
        sourceRevisionId: null,
        sourceRevision: null,
        isCurrentRevision: false,
      };
      this.submittingBranch = false;

      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    validateBranchState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.branchFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitBranch(event: Event): Promise<void> {
      (this as any).$v.branchFormState.$touch();
      if ((this as any).$v.branchFormState.$anyError || this.submittingBranch) {
        event.preventDefault();
        return;
      }

      this.submittingBranch = true;
      try {
        await (this as any).ADD_SCRIPT_REVISION({
          description: this.branchFormState.description,
          parent_revision_id: this.branchFormState.sourceRevisionId,
          set_as_current: this.branchFormState.isCurrentRevision,
        });
        (this as any).$bvModal.hide('create-branch-modal');
        (this as any).$bvModal.hide('revision-detail');
        this.resetBranchForm();
      } catch (error) {
        log.error('Error creating branch:', error);
        event.preventDefault();
      } finally {
        this.submittingBranch = false;
      }
    },
    handleModalClose(): void {
      (this as any).$bvModal.hide('revision-detail');
    },
    handleModalHidden(): void {
      this.selectedRevisionId = null;
      this.selectedRevision = null;
      this.modalSubmitting = false;
    },
    ...mapActions([
      'ADD_SCRIPT_REVISION',
      'LOAD_SCRIPT_REVISION',
      'DELETE_SCRIPT_REVISION',
      'GET_SCRIPT_CONFIG_STATUS',
    ]),
  },
});
</script>

<style scoped>
/* Remove card body padding when collapsed to minimize visual footprint */
.collapsed-card >>> .card-body {
  padding: 0;
}
</style>
