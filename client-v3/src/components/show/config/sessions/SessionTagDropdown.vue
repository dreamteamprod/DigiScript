<template>
  <BDropdown variant="link" size="sm" no-caret toggle-class="p-0 ms-2 edit-tags-btn">
    <template #button-content>
      <span>✏️</span>
    </template>

    <BDropdownForm class="tag-dropdown-form" @click.stop>
      <BFormInput
        v-model="searchQuery"
        placeholder="Filter tags..."
        size="sm"
        class="mb-2"
        autofocus
      />

      <div class="tag-list">
        <BFormCheckbox
          v-for="tag in filteredTags"
          :key="tag.id"
          :model-value="selectedTagIds.includes(tag.id)"
          :disabled="saving"
          class="mb-2"
          @update:model-value="toggleTag(tag.id)"
        >
          <span
            class="tag-pill-small"
            :style="{
              backgroundColor: tag.colour,
              color: contrastColor(tag.colour ?? '#ffffff'),
            }"
          >
            {{ tag.tag }}
          </span>
        </BFormCheckbox>

        <div v-if="filteredTags.length === 0" class="text-muted small p-2">
          No tags match your search
        </div>
      </div>

      <div v-if="saving" class="text-center p-2 border-top mt-2">
        <BSpinner small variant="primary" />
        <span class="ms-2 small">Saving...</span>
      </div>
    </BDropdownForm>
  </BDropdown>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { contrastColor } from '@/js/utils';
import log from 'loglevel';
import { useShowStore } from '@/stores/show';

const props = defineProps<{
  sessionId: number;
  currentTagIds: number[];
}>();

const showStore = useShowStore();

const searchQuery = ref('');
const selectedTagIds = ref<number[]>([...props.currentTagIds]);
const saving = ref(false);

watch(
  () => props.currentTagIds,
  (newIds) => {
    selectedTagIds.value = [...newIds];
  }
);

const filteredTags = computed(() => {
  if (!searchQuery.value) return showStore.sessionTags;
  const query = searchQuery.value.toLowerCase();
  return showStore.sessionTags.filter((tag) => tag.tag.toLowerCase().includes(query));
});

async function toggleTag(tagId: number): Promise<void> {
  if (selectedTagIds.value.includes(tagId)) {
    selectedTagIds.value = selectedTagIds.value.filter((id) => id !== tagId);
  } else {
    selectedTagIds.value.push(tagId);
  }
  if (saving.value) return;
  saving.value = true;
  try {
    await showStore.updateSessionTags({ sessionId: props.sessionId, tagIds: selectedTagIds.value });
  } catch (error) {
    log.error('Error updating session tags:', error);
    selectedTagIds.value = [...props.currentTagIds];
  } finally {
    saving.value = false;
  }
}
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
.edit-tags-btn {
  color: #6c757d;
  opacity: 0.7;
}

.edit-tags-btn:hover {
  opacity: 1;
}
</style>
