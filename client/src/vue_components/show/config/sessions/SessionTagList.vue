<template>
  <span>
    <b-table
      id="session-tags-table"
      :items="SESSION_TAGS"
      :fields="tagFields"
      :per-page="rowsPerPage"
      :current-page="currentPage"
      show-empty
    >
      <template #head(btn)="data">
        <b-button v-if="IS_SHOW_EDITOR" v-b-modal.new-tag variant="outline-success">
          New Tag
        </b-button>
        <b-button
          v-if="IS_SHOW_EDITOR"
          variant="outline-info"
          class="ml-2"
          @click="openImportModal"
        >
          Import Tag
        </b-button>
      </template>
      <template #cell(tag)="data">
        <span
          class="tag-pill"
          :style="{
            backgroundColor: data.item.colour,
            color: contrastColor({ bgColor: data.item.colour }),
          }"
        >
          {{ data.item.tag }}
        </span>
      </template>
      <template #cell(session_count)="data">
        {{ getSessionCountForTag(data.item.id) }}
      </template>
      <template #cell(btn)="data">
        <b-button-group v-if="IS_SHOW_EDITOR">
          <b-button variant="warning" @click="openEditTagForm(data)"> Edit </b-button>
          <b-button variant="danger" :disabled="isSubmittingDeleteTag" @click="deleteTag(data)">
            Delete
          </b-button>
        </b-button-group>
      </template>
    </b-table>
    <pagination-controls
      :per-page.sync="rowsPerPage"
      :current-page.sync="currentPage"
      :total-rows="SESSION_TAGS.length"
      aria-controls="session-tags-table"
    />
    <b-modal
      id="new-tag"
      ref="new-tag"
      title="Add Session Tag"
      size="md"
      :ok-disabled="isSubmittingNewTag"
      @show="resetNewTagForm"
      @hidden="resetNewTagForm"
      @ok="onSubmitNewTag"
    >
      <b-form ref="new-tag-form" @submit.stop.prevent="onSubmitNewTag">
        <b-form-group id="new-tag-name-group" label="Tag Name" label-for="new-tag-name">
          <b-form-input
            id="new-tag-name"
            v-model="$v.newTagForm.tag.$model"
            name="new-tag-name"
            :state="validateNewTag('tag')"
            aria-describedby="new-tag-name-feedback"
          />
          <b-form-invalid-feedback id="new-tag-name-feedback">
            This is a required field and must be unique (case-insensitive).
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="new-tag-colour-group" label="Colour" label-for="new-tag-colour">
          <b-form-input
            id="new-tag-colour"
            v-model="$v.newTagForm.colour.$model"
            type="color"
            name="new-tag-colour"
            :state="validateNewTag('colour')"
            aria-describedby="new-tag-colour-feedback"
          />
          <b-form-invalid-feedback id="new-tag-colour-feedback">
            This is a required field and must be a valid hex color.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group label="Preview">
          <span
            class="tag-pill"
            :style="{
              backgroundColor: newTagForm.colour,
              color: contrastColor({ bgColor: newTagForm.colour }),
            }"
          >
            {{ newTagForm.tag || 'Tag Name' }}
          </span>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-tag"
      ref="edit-tag"
      title="Edit Session Tag"
      size="md"
      :ok-disabled="isSubmittingEditTag"
      @hidden="resetEditTagForm"
      @ok="onSubmitEditTag"
    >
      <b-form ref="edit-tag-form" @submit.stop.prevent="onSubmitEditTag">
        <b-form-group id="edit-tag-name-group" label="Tag Name" label-for="edit-tag-name">
          <b-form-input
            id="edit-tag-name"
            v-model="$v.editTagForm.tag.$model"
            name="edit-tag-name"
            :state="validateEditTag('tag')"
            aria-describedby="edit-tag-name-feedback"
          />
          <b-form-invalid-feedback id="edit-tag-name-feedback">
            This is a required field and must be unique (case-insensitive).
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="edit-tag-colour-group" label="Colour" label-for="edit-tag-colour">
          <b-form-input
            id="edit-tag-colour"
            v-model="$v.editTagForm.colour.$model"
            type="color"
            name="edit-tag-colour"
            :state="validateEditTag('colour')"
            aria-describedby="edit-tag-colour-feedback"
          />
          <b-form-invalid-feedback id="edit-tag-colour-feedback">
            This is a required field and must be a valid hex color.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group label="Preview">
          <span
            class="tag-pill"
            :style="{
              backgroundColor: editTagForm.colour,
              color: contrastColor({ bgColor: editTagForm.colour }),
            }"
          >
            {{ editTagForm.tag || 'Tag Name' }}
          </span>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="import-tag-modal"
      ref="import-tag-modal"
      title="Import Session Tag"
      size="xl"
      hide-footer
      @hidden="resetImportState"
    >
      <div v-if="isLoadingImport" class="text-center">
        <b-spinner />
      </div>
      <div v-else-if="importTagGroups.length === 0">
        <p class="text-muted">No session tags available to import from other shows.</p>
      </div>
      <div v-else>
        <b-card v-for="show in importTagGroups" :key="show.id" no-body class="mb-2">
          <b-card-header style="cursor: pointer" @click="toggleImportShow(show.id)">
            <div class="d-flex justify-content-between align-items-center">
              <span>{{ show.name }}</span>
              <b-icon-chevron-down v-if="tagGroupExpanded[show.id]" font-scale="0.8" />
              <b-icon-chevron-up v-else font-scale="0.8" />
            </div>
          </b-card-header>
          <b-collapse :visible="tagGroupExpanded[show.id]">
            <b-table :items="show.tags" :fields="importTagFields" small>
              <template #cell(tag)="data">
                <span
                  class="tag-pill"
                  :style="{
                    backgroundColor: data.item.colour,
                    color: contrastColor({ bgColor: data.item.colour }),
                  }"
                >
                  {{ data.item.tag }}
                </span>
              </template>
              <template #cell(action)="data">
                <span
                  v-b-tooltip.hover
                  :title="tagAlreadyExists(data.item) ? 'Already exists in this show' : ''"
                >
                  <b-button
                    variant="outline-success"
                    size="sm"
                    :disabled="!!isImporting[data.item.id] || tagAlreadyExists(data.item)"
                    @click="importTag(data.item)"
                  >
                    <b-spinner v-if="isImporting[data.item.id]" small />
                    <span v-else>Import</span>
                  </b-button>
                </span>
              </template>
            </b-table>
          </b-collapse>
        </b-card>
      </div>
    </b-modal>
  </span>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapActions, mapGetters } from 'vuex';
import log from 'loglevel';
import { required } from 'vuelidate/lib/validators';
import { contrastColor } from 'contrast-color';
import paginationMixin from '@/mixins/paginationMixin';

function isValidHexColor(value: string): boolean {
  if (!value) return false;
  const hexColorRegex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
  return hexColorRegex.test(value);
}

function isTagNameUnique(this: any, value: string): boolean {
  if (value === '') {
    return true;
  }
  const lowerValue = value.toLowerCase();
  if (this.editTagForm.id != null) {
    if (this.SESSION_TAGS != null && this.SESSION_TAGS.length > 0) {
      return !this.SESSION_TAGS.some(
        (tag: any) => tag.tag.toLowerCase() === lowerValue && tag.id !== this.editTagForm.id
      );
    }
  } else if (this.SESSION_TAGS != null && this.SESSION_TAGS.length > 0) {
    return !this.SESSION_TAGS.some((tag: any) => tag.tag.toLowerCase() === lowerValue);
  }
  return true;
}

export default defineComponent({
  name: 'SessionTagList',
  mixins: [paginationMixin],
  data() {
    return {
      tagFields: [
        { key: 'tag', label: 'Tag' },
        { key: 'session_count', label: 'Sessions' },
        { key: 'btn', label: '' },
      ],
      newTagForm: {
        tag: '',
        colour: '#3498DB',
      },
      editTagForm: {
        id: null as number | null,
        tag: '',
        colour: '',
      },
      isSubmittingNewTag: false,
      isSubmittingEditTag: false,
      isSubmittingDeleteTag: false,
      importTagGroups: [] as any[],
      tagGroupExpanded: {} as Record<number, boolean>,
      isLoadingImport: false,
      isImporting: {} as Record<number, boolean>,
      importTagFields: [
        { key: 'tag', label: 'Tag' },
        { key: 'action', label: '' },
      ],
    };
  },
  validations: {
    newTagForm: {
      tag: { required, unique: isTagNameUnique },
      colour: { required, validHex: isValidHexColor },
    },
    editTagForm: {
      tag: { required, unique: isTagNameUnique },
      colour: { required, validHex: isValidHexColor },
    },
  },
  computed: {
    ...mapGetters(['SESSION_TAGS', 'SHOW_SESSIONS_LIST', 'IS_SHOW_EDITOR']),
    existingTagNames(): Set<string> {
      return new Set(((this as any).SESSION_TAGS || []).map((t: any) => t.tag.toLowerCase()));
    },
  },
  methods: {
    ...mapActions([
      'ADD_SESSION_TAG',
      'UPDATE_SESSION_TAG',
      'DELETE_SESSION_TAG',
      'GET_IMPORTABLE_SESSION_TAGS',
    ]),
    contrastColor,
    getSessionCountForTag(tagId: number): number {
      if (!(this as any).SHOW_SESSIONS_LIST || !Array.isArray((this as any).SHOW_SESSIONS_LIST)) {
        return 0;
      }
      return (this as any).SHOW_SESSIONS_LIST.filter((session: any) => {
        if (!session.tags || !Array.isArray(session.tags)) {
          return false;
        }
        return session.tags.some((tag: any) => tag.id === tagId);
      }).length;
    },
    resetNewTagForm(): void {
      this.newTagForm = { tag: '', colour: '#3498DB' };
      this.isSubmittingNewTag = false;
      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    async onSubmitNewTag(event: Event): Promise<void> {
      (this as any).$v.newTagForm.$touch();
      if ((this as any).$v.newTagForm.$anyError) {
        event.preventDefault();
        return;
      }
      if (this.isSubmittingNewTag) {
        event.preventDefault();
        return;
      }
      this.isSubmittingNewTag = true;
      try {
        await (this as any).ADD_SESSION_TAG(this.newTagForm);
        (this as any).$bvModal.hide('new-tag');
      } catch (error) {
        log.error('Error adding session tag:', error);
        event.preventDefault();
      } finally {
        this.isSubmittingNewTag = false;
      }
    },
    validateNewTag(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.newTagForm[name];
      return $dirty ? !$error : null;
    },
    openEditTagForm(data: any): void {
      if (data != null && data.item != null) {
        this.editTagForm.id = data.item.id;
        this.editTagForm.tag = data.item.tag;
        this.editTagForm.colour = data.item.colour;
        (this as any).$bvModal.show('edit-tag');
      }
    },
    resetEditTagForm(): void {
      this.editTagForm = { id: null, tag: '', colour: '' };
      this.isSubmittingEditTag = false;
      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    async onSubmitEditTag(event: Event): Promise<void> {
      (this as any).$v.editTagForm.$touch();
      if ((this as any).$v.editTagForm.$anyError) {
        event.preventDefault();
        return;
      }
      if (this.isSubmittingEditTag) {
        event.preventDefault();
        return;
      }
      this.isSubmittingEditTag = true;
      try {
        await (this as any).UPDATE_SESSION_TAG(this.editTagForm);
        (this as any).$bvModal.hide('edit-tag');
      } catch (error) {
        log.error('Error updating session tag:', error);
        event.preventDefault();
      } finally {
        this.isSubmittingEditTag = false;
      }
    },
    validateEditTag(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.editTagForm[name];
      return $dirty ? !$error : null;
    },
    async openImportModal(): Promise<void> {
      (this as any).$bvModal.show('import-tag-modal');
      this.isLoadingImport = true;
      try {
        const data = await (this as any).GET_IMPORTABLE_SESSION_TAGS();
        this.importTagGroups = data.tag_groups;
        data.tag_groups.forEach((show: any) => {
          this.$set(this.tagGroupExpanded, show.id, true);
        });
      } catch (e) {
        log.error('Error loading importable session tags:', e);
      } finally {
        this.isLoadingImport = false;
      }
    },
    toggleImportShow(showId: number): void {
      this.$set(this.tagGroupExpanded, showId, !this.tagGroupExpanded[showId]);
    },
    tagAlreadyExists(tag: any): boolean {
      return this.existingTagNames.has(tag.tag.toLowerCase());
    },
    async importTag(tag: any): Promise<void> {
      this.$set(this.isImporting, tag.id, true);
      try {
        await (this as any).ADD_SESSION_TAG({ tag: tag.tag, colour: tag.colour });
      } finally {
        this.$set(this.isImporting, tag.id, false);
      }
    },
    resetImportState(): void {
      this.importTagGroups = [];
      this.tagGroupExpanded = {};
      this.isLoadingImport = false;
      this.isImporting = {};
    },
    async deleteTag(data: any): Promise<void> {
      if (this.isSubmittingDeleteTag) {
        return;
      }
      const sessionCount = this.getSessionCountForTag(data.item.id);
      let msg = `Are you sure you want to delete the tag "${data.item.tag}"?`;
      if (sessionCount > 0) {
        msg += ` This tag is currently applied to ${sessionCount} session(s).`;
      }
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.isSubmittingDeleteTag = true;
        try {
          await (this as any).DELETE_SESSION_TAG(data.item.id);
        } catch (error) {
          log.error('Error deleting session tag:', error);
        } finally {
          this.isSubmittingDeleteTag = false;
        }
      }
    },
  },
});
</script>

<style scoped>
.tag-pill {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 12px;
  white-space: nowrap;
  border: 1px solid rgba(0, 0, 0, 0.1);
}
</style>
