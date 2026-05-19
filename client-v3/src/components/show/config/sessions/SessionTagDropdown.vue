<template>
  <BDropdown variant="link" size="sm" no-caret toggle-class="p-0 ms-2 edit-tags-btn">
    <template #button-content>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="1em"
        height="1em"
        fill="currentColor"
        viewBox="0 0 16 16"
      >
        <path
          d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325z"
        />
      </svg>
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
