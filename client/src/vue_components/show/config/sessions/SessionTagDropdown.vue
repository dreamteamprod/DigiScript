<template>
  <b-dropdown
    ref="dropdown"
    variant="link"
    size="sm"
    no-caret
    boundary="viewport"
    right
    toggle-class="p-0 ml-2 edit-tags-btn"
  >
    <template #button-content>
      <b-icon-pencil-fill />
    </template>

    <b-dropdown-form class="tag-dropdown-form" @click.stop>
      <!-- Search/Filter Input -->
      <b-form-input
        v-model="searchQuery"
        placeholder="Filter tags..."
        size="sm"
        class="mb-2"
        autofocus
      />

      <!-- Checkbox List -->
      <div class="tag-list">
        <b-form-checkbox
          v-for="tag in filteredTags"
          :key="tag.id"
          :checked="isTagSelected(tag.id)"
          :disabled="saving"
          class="mb-2"
          @change="toggleTag(tag.id)"
        >
          <span
            class="tag-pill-small"
            :style="{
              backgroundColor: tag.colour,
              color: contrastColor({ bgColor: tag.colour }),
            }"
          >
            {{ tag.tag }}
          </span>
        </b-form-checkbox>

        <div v-if="filteredTags.length === 0" class="text-muted small p-2">
          No tags match your search
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="saving" class="text-center p-2 border-top mt-2">
        <b-spinner small variant="primary" />
        <span class="ml-2 small">Saving...</span>
      </div>
    </b-dropdown-form>
  </b-dropdown>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import log from 'loglevel';
import { contrastColor } from 'contrast-color';

export default {
  name: 'SessionTagDropdown',
  props: {
    sessionId: {
      type: Number,
      required: true,
    },
    currentTagIds: {
      type: Array,
      required: true,
    },
  },
  data() {
    return {
      searchQuery: '',
      selectedTagIds: [...this.currentTagIds],
      saving: false,
    };
  },
  computed: {
    ...mapGetters(['SESSION_TAGS']),
    filteredTags() {
      if (!this.searchQuery) {
        return this.SESSION_TAGS || [];
      }
      const query = this.searchQuery.toLowerCase();
      return (this.SESSION_TAGS || []).filter((tag) => tag.tag.toLowerCase().includes(query));
    },
  },
  methods: {
    ...mapActions(['UPDATE_SESSION_TAGS']),
    contrastColor,
    isTagSelected(tagId) {
      return this.selectedTagIds.includes(tagId);
    },
    async toggleTag(tagId) {
      // Optimistic update
      if (this.selectedTagIds.includes(tagId)) {
        this.selectedTagIds = this.selectedTagIds.filter((id) => id !== tagId);
      } else {
        this.selectedTagIds.push(tagId);
      }

      // Save immediately
      await this.saveTagAssignment();
    },
    async saveTagAssignment() {
      if (this.saving) return;
      this.saving = true;

      try {
        await this.UPDATE_SESSION_TAGS({
          sessionId: this.sessionId,
          tagIds: this.selectedTagIds,
        });
      } catch (error) {
        log.error('Error updating session tags:', error);
        // Revert optimistic update on error
        this.selectedTagIds = [...this.currentTagIds];
      } finally {
        this.saving = false;
      }
    },
  },
};
</script>

<style scoped>
.tag-dropdown-form {
  min-width: 250px;
  max-width: 350px;
}

.tag-list {
  max-height: 300px;
  overflow-y: auto;
}

.tag-pill-small {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 11px;
  white-space: nowrap;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

/* Custom scrollbar for tag list */
.tag-list::-webkit-scrollbar {
  width: 8px;
}

.tag-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.tag-list::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.tag-list::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>

<style>
/* Non-scoped styles for b-dropdown toggle button */
.edit-tags-btn {
  color: #6c757d;
  opacity: 0.7;
}

.edit-tags-btn:hover {
  opacity: 1;
}
</style>
