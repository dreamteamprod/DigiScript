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
                    variant="warning"
                    :disabled="!canChangeRevisions ||
                      data.item.id === $store.state.script.currentRevision"
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
                <b-button-group v-if="data.item.revision !== 1">
                  <b-button
                    variant="warning"
                    :disabled="!canChangeRevisions"
                    @click="openEditRevForm(data)"
                  >
                    Edit
                  </b-button>
                  <b-button
                    variant="danger"
                    :disabled="!canChangeRevisions"
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
                      v-b-modal.new-revision
                      variant="outline-success"
                      :disabled="!canChangeRevisions"
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
import ScriptConfig from '@/vue_components/show/config/script/ScriptEditor.vue';

export default {
  name: 'ConfigScript',
  components: { ScriptConfig },
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
    };
  },
  validations: {
    newRevFormState: {
      description: {
        required,
      },
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
      if (this.$v.newRevFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.ADD_SCRIPT_REVISION(this.newRevFormState);
        this.resetNewRevForm();
      }
    },
    async loadRevision(revision) {
      const msg = `Are you sure you want to load revision ${revision.item.revision}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.LOAD_SCRIPT_REVISION(revision.item.id);
      }
    },
    openEditRevForm(revision) {

    },
    async deleteRev(revision) {
      let msg = `Are you sure you want to delete revision ${revision.item.revision}?`;
      if (this.CURRENT_REVISION === revision.item.id) {
        msg = `${msg}  This will load the previous revision, or first revision if this is not available.`;
      }
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_SCRIPT_REVISION(revision.item.id);
      }
    },
    ...mapActions(['GET_SCRIPT_REVISIONS', 'ADD_SCRIPT_REVISION', 'LOAD_SCRIPT_REVISION',
      'DELETE_SCRIPT_REVISION', 'GET_SCRIPT_CONFIG_STATUS']),
  },
  computed: {
    ...mapGetters(['SCRIPT_REVISIONS', 'CURRENT_REVISION', 'CURRENT_EDITOR', 'INTERNAL_UUID']),
    canChangeRevisions() {
      return this.CURRENT_EDITOR == null || this.CURRENT_EDITOR === this.INTERNAL_UUID;
    },
  },
};
</script>
