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
  </b-container>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import { required } from 'vuelidate/lib/validators';
import log from 'loglevel';
import ScriptConfig from '@/vue_components/show/config/script/ScriptEditor.vue';
import StageDirectionStyles from '@/vue_components/show/config/script/StageDirectionStyles.vue';

export default {
  name: 'ConfigScript',
  components: { ScriptConfig, StageDirectionConfigs: StageDirectionStyles },
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
      submittingNewRevision: false,
      submittingLoadRevision: false,
      deletingRevision: false,
    };
  },
  validations: {
    newRevFormState: {
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
    ...mapActions(['GET_SCRIPT_REVISIONS', 'ADD_SCRIPT_REVISION', 'LOAD_SCRIPT_REVISION',
      'DELETE_SCRIPT_REVISION', 'GET_SCRIPT_CONFIG_STATUS']),
  },
};
</script>
