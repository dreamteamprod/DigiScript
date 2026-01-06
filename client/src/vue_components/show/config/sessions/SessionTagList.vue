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
        <b-button
          v-if="IS_SHOW_EDITOR"
          v-b-modal.new-tag
          variant="outline-success"
        >
          New Tag
        </b-button>
      </template>
      <template #cell(tag)="data">
        <span
          class="tag-pill"
          :style="{
            backgroundColor: data.item.colour,
            color: contrastColor({bgColor: data.item.colour})
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
          <b-button
            variant="warning"
            @click="openEditTagForm(data)"
          >
            Edit
          </b-button>
          <b-button
            variant="danger"
            :disabled="isSubmittingDeleteTag"
            @click="deleteTag(data)"
          >
            Delete
          </b-button>
        </b-button-group>
      </template>
    </b-table>
    <b-pagination
      v-show="SESSION_TAGS.length > rowsPerPage"
      v-model="currentPage"
      :total-rows="SESSION_TAGS.length"
      :per-page="rowsPerPage"
      aria-controls="session-tags-table"
      class="justify-content-center"
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
      <b-form
        ref="new-tag-form"
        @submit.stop.prevent="onSubmitNewTag"
      >
        <b-form-group
          id="new-tag-name-group"
          label="Tag Name"
          label-for="new-tag-name"
        >
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
        <b-form-group
          id="new-tag-colour-group"
          label="Colour"
          label-for="new-tag-colour"
        >
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
              color: contrastColor({bgColor: newTagForm.colour})
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
      <b-form
        ref="edit-tag-form"
        @submit.stop.prevent="onSubmitEditTag"
      >
        <b-form-group
          id="edit-tag-name-group"
          label="Tag Name"
          label-for="edit-tag-name"
        >
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
        <b-form-group
          id="edit-tag-colour-group"
          label="Colour"
          label-for="edit-tag-colour"
        >
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
              color: contrastColor({bgColor: editTagForm.colour})
            }"
          >
            {{ editTagForm.tag || 'Tag Name' }}
          </span>
        </b-form-group>
      </b-form>
    </b-modal>
  </span>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import log from 'loglevel';
import { required } from 'vuelidate/lib/validators';
import { contrastColor } from 'contrast-color';

function isValidHexColor(value) {
  if (!value) return false;
  const hexColorRegex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
  return hexColorRegex.test(value);
}

function isTagNameUnique(value) {
  if (value === '') {
    return true;
  }
  const lowerValue = value.toLowerCase();
  if (this.editTagForm.id != null) {
    if (this.SESSION_TAGS != null && this.SESSION_TAGS.length > 0) {
      return !this.SESSION_TAGS.some((tag) => (
        tag.tag.toLowerCase() === lowerValue && tag.id !== this.editTagForm.id
      ));
    }
  } else if (this.SESSION_TAGS != null && this.SESSION_TAGS.length > 0) {
    return !this.SESSION_TAGS.some((tag) => (
      tag.tag.toLowerCase() === lowerValue
    ));
  }
  return true;
}

export default {
  name: 'SessionTagList',
  data() {
    return {
      tagFields: [
        { key: 'tag', label: 'Tag' },
        { key: 'session_count', label: 'Sessions' },
        { key: 'btn', label: '' },
      ],
      rowsPerPage: 15,
      currentPage: 1,
      newTagForm: {
        tag: '',
        colour: '#3498DB',
      },
      editTagForm: {
        id: null,
        tag: '',
        colour: '',
      },
      isSubmittingNewTag: false,
      isSubmittingEditTag: false,
      isSubmittingDeleteTag: false,
    };
  },
  validations: {
    newTagForm: {
      tag: {
        required,
        unique: isTagNameUnique,
      },
      colour: {
        required,
        validHex: isValidHexColor,
      },
    },
    editTagForm: {
      tag: {
        required,
        unique: isTagNameUnique,
      },
      colour: {
        required,
        validHex: isValidHexColor,
      },
    },
  },
  computed: {
    ...mapGetters(['SESSION_TAGS', 'SHOW_SESSIONS_LIST', 'IS_SHOW_EDITOR']),
  },
  methods: {
    ...mapActions(['ADD_SESSION_TAG', 'UPDATE_SESSION_TAG', 'DELETE_SESSION_TAG']),
    contrastColor,
    getSessionCountForTag(tagId) {
      if (!this.SHOW_SESSIONS_LIST || !Array.isArray(this.SHOW_SESSIONS_LIST)) {
        return 0;
      }
      return this.SHOW_SESSIONS_LIST.filter((session) => {
        if (!session.tags || !Array.isArray(session.tags)) {
          return false;
        }
        return session.tags.some((tag) => tag.id === tagId);
      }).length;
    },
    resetNewTagForm() {
      this.newTagForm = {
        tag: '',
        colour: '#3498DB',
      };
      this.isSubmittingNewTag = false;
      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitNewTag(event) {
      this.$v.newTagForm.$touch();
      if (this.$v.newTagForm.$anyError) {
        event.preventDefault();
        return;
      }
      if (this.isSubmittingNewTag) {
        event.preventDefault();
        return;
      }
      this.isSubmittingNewTag = true;
      try {
        await this.ADD_SESSION_TAG(this.newTagForm);
        this.$bvModal.hide('new-tag');
      } catch (error) {
        log.error('Error adding session tag:', error);
        event.preventDefault();
      } finally {
        this.isSubmittingNewTag = false;
      }
    },
    validateNewTag(name) {
      const { $dirty, $error } = this.$v.newTagForm[name];
      return $dirty ? !$error : null;
    },
    openEditTagForm(data) {
      if (data != null && data.item != null) {
        this.editTagForm.id = data.item.id;
        this.editTagForm.tag = data.item.tag;
        this.editTagForm.colour = data.item.colour;
        this.$bvModal.show('edit-tag');
      }
    },
    resetEditTagForm() {
      this.editTagForm = {
        id: null,
        tag: '',
        colour: '',
      };
      this.isSubmittingEditTag = false;
      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitEditTag(event) {
      this.$v.editTagForm.$touch();
      if (this.$v.editTagForm.$anyError) {
        event.preventDefault();
        return;
      }
      if (this.isSubmittingEditTag) {
        event.preventDefault();
        return;
      }
      this.isSubmittingEditTag = true;
      try {
        await this.UPDATE_SESSION_TAG(this.editTagForm);
        this.$bvModal.hide('edit-tag');
      } catch (error) {
        log.error('Error updating session tag:', error);
        event.preventDefault();
      } finally {
        this.isSubmittingEditTag = false;
      }
    },
    validateEditTag(name) {
      const { $dirty, $error } = this.$v.editTagForm[name];
      return $dirty ? !$error : null;
    },
    async deleteTag(data) {
      if (this.isSubmittingDeleteTag) {
        return;
      }
      const sessionCount = this.getSessionCountForTag(data.item.id);
      let msg = `Are you sure you want to delete the tag "${data.item.tag}"?`;
      if (sessionCount > 0) {
        msg += ` This tag is currently applied to ${sessionCount} session(s).`;
      }
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.isSubmittingDeleteTag = true;
        try {
          await this.DELETE_SESSION_TAG(data.item.id);
        } catch (error) {
          log.error('Error deleting session tag:', error);
        } finally {
          this.isSubmittingDeleteTag = false;
        }
      }
    },
  },
};
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
