<template>
  <div class="help">
    <h1>DigiScript Documentation</h1>
    <BContainer class="mx-0 help-container" fluid>
      <BRow>
        <BCol cols="2">
          <div class="sticky-nav" :style="{ top: navbarHeight + 'px' }">
            <BFormInput
              v-model="searchQuery"
              placeholder="Search docs..."
              class="mb-3"
              @input="handleSearch"
            />
            <BButtonGroup vertical class="w-100">
              <BButton
                v-for="doc in displayedDocs"
                :key="doc.slug"
                :to="{ name: 'help-doc', params: { slug: doc.slug } }"
                variant="outline-info"
                active-class="active"
              >
                {{ doc.title }}
              </BButton>
            </BButtonGroup>
          </div>
        </BCol>
        <BCol cols="10">
          <RouterView />
        </BCol>
      </BRow>
    </BContainer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { storeToRefs } from 'pinia';
import { debounce } from 'lodash';
import { useHelpStore } from '@/stores/help';

const helpStore = useHelpStore();
const { documentationManifest, searchResults } = storeToRefs(helpStore);

const navbarHeight = ref(0);
const searchQuery = ref('');

const displayedDocs = computed(() => {
  if (searchQuery.value && searchResults.value.length > 0) {
    return searchResults.value;
  }
  return documentationManifest.value;
});

onMounted(async () => {
  await helpStore.loadManifest();
  calculateNavbarHeight();
  window.addEventListener('resize', calculateNavbarHeight);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', calculateNavbarHeight);
});

function calculateNavbarHeight(): void {
  const navbar = document.querySelector('.navbar');
  navbarHeight.value = navbar ? (navbar as HTMLElement).offsetHeight : 56;
}

const handleSearch = debounce(function () {
  if (!searchQuery.value || searchQuery.value.trim() === '') {
    helpStore.clearSearch();
  } else {
    helpStore.searchDocuments(searchQuery.value);
  }
}, 300);
</script>

<style scoped>
.help-container {
  position: relative;
}

.sticky-nav {
  position: sticky;
  padding: 10px 0;
  background: var(--body-background);
}
</style>
