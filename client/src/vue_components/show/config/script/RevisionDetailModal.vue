<template>
  <b-modal
    :id="modalId"
    :title="`Revision ${revision ? revision.revision : ''}`"
    size="lg"
    @hidden="handleHidden"
  >
    <div v-if="revision">
      <b-row>
        <b-col cols="12">
          <b-alert
            v-if="isCurrentRevision"
            show
            variant="success"
          >
            <b-icon-check-circle-fill />
            This is the current active revision
          </b-alert>
        </b-col>
      </b-row>

      <b-row>
        <b-col
          cols="12"
          md="6"
        >
          <dl>
            <dt>Revision Number</dt>
            <dd>{{ revision.revision }}</dd>

            <dt>Description</dt>
            <dd>{{ revision.description || 'No description' }}</dd>

            <dt>Created At</dt>
            <dd>{{ formatDate(revision.created_at) }}</dd>

            <dt>Last Edited</dt>
            <dd>{{ formatDate(revision.edited_at) }}</dd>
          </dl>
        </b-col>

        <b-col
          cols="12"
          md="6"
        >
          <dl>
            <dt>Previous Revision</dt>
            <dd v-if="previousRevision">
              Revision {{ previousRevision.revision }}
              <br>
              <small class="text-muted">{{ previousRevision.description }}</small>
            </dd>
            <dd v-else>
              <em class="text-muted">None (root revision)</em>
            </dd>

            <dt>Child Revisions</dt>
            <dd v-if="childRevisions.length > 0">
              <ul class="list-unstyled">
                <li
                  v-for="child in childRevisions"
                  :key="child.id"
                >
                  Revision {{ child.revision }}: {{ child.description }}
                </li>
              </ul>
            </dd>
            <dd v-else>
              <em class="text-muted">None</em>
            </dd>
          </dl>
        </b-col>
      </b-row>
    </div>

    <template #modal-footer>
      <div class="w-100 d-flex justify-content-between">
        <div>
          <b-button
            v-if="!isCurrentRevision && canEdit"
            variant="warning"
            :disabled="submitting"
            @click="handleLoadRevision"
          >
            <b-spinner
              v-if="submitting === 'load'"
              small
            />
            Load This Revision
          </b-button>
        </div>
        <div>
          <b-button
            v-if="canEdit"
            variant="success"
            :disabled="submitting"
            @click="handleCreateFrom"
          >
            <b-spinner
              v-if="submitting === 'create'"
              small
            />
            Create Branch From Here
          </b-button>
          <b-button
            variant="secondary"
            class="ml-2"
            @click="handleClose"
          >
            Close
          </b-button>
        </div>
      </div>
    </template>
  </b-modal>
</template>

<script>
export default {
  name: 'RevisionDetailModal',
  props: {
    modalId: {
      type: String,
      default: 'revision-detail-modal',
    },
    revision: {
      type: Object,
      default: null,
    },
    revisions: {
      type: Array,
      required: true,
    },
    currentRevisionId: {
      type: Number,
      default: null,
    },
    canEdit: {
      type: Boolean,
      default: false,
    },
    submitting: {
      type: [String, Boolean],
      default: false,
    },
  },
  computed: {
    isCurrentRevision() {
      return this.revision && this.revision.id === this.currentRevisionId;
    },
    previousRevision() {
      if (!this.revision || !this.revision.previous_revision_id) {
        return null;
      }
      return this.revisions.find((r) => r.id === this.revision.previous_revision_id);
    },
    childRevisions() {
      if (!this.revision) {
        return [];
      }
      return this.revisions.filter((r) => r.previous_revision_id === this.revision.id);
    },
  },
  methods: {
    formatDate(dateString) {
      if (!dateString) return 'N/A';
      const date = new Date(dateString);
      return date.toLocaleString();
    },
    handleLoadRevision() {
      this.$emit('load-revision', this.revision);
    },
    handleCreateFrom() {
      this.$emit('create-from', this.revision);
    },
    handleClose() {
      this.$emit('close');
    },
    handleHidden() {
      this.$emit('hidden');
    },
  },
};
</script>

<style scoped>
dl {
  margin-bottom: 0;
}

dt {
  font-weight: 600;
  margin-top: 0.5rem;
  color: #dee2e6;
}

dd {
  margin-bottom: 0.5rem;
  color: #adb5bd;
}
</style>
