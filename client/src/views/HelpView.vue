<template>
  <div class="help">
    <h1>DigiScript Documentation</h1>
    <b-container class="mx-0 help-container" fluid>
      <b-row>
        <b-col cols="2">
          <div class="sticky-nav" :style="{ top: navbarHeight + 'px' }">
            <!-- Search Input -->
            <b-form-input
              v-model="searchQuery"
              placeholder="Search docs..."
              class="mb-3"
              @input="handleSearch"
            />

            <!-- Navigation Buttons -->
            <b-button-group vertical class="w-100">
              <b-button
                v-for="doc in displayedDocs"
                :key="doc.slug"
                :to="{ name: 'help-doc', params: { slug: doc.slug } }"
                variant="outline-info"
                active-class="active"
              >
                {{ doc.title }}
              </b-button>
            </b-button-group>
          </div>
        </b-col>
        <b-col cols="10">
          <router-view />
        </b-col>
      </b-row>
    </b-container>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters, mapActions } from 'vuex';
import { debounce } from 'lodash';

export default defineComponent({
  name: 'HelpView',
  data() {
    return {
      navbarHeight: 0,
      searchQuery: '',
    };
  },
  computed: {
    ...mapGetters(['DOCUMENTATION_MANIFEST', 'SEARCH_RESULTS']),
    displayedDocs(): unknown[] {
      if (this.searchQuery && (this as any).SEARCH_RESULTS.length > 0) {
        return (this as any).SEARCH_RESULTS;
      }
      return (this as any).DOCUMENTATION_MANIFEST;
    },
  },
  watch: {
    searchQuery(): void {
      if (!this.searchQuery || this.searchQuery.trim() === '') {
        (this as any).CLEAR_SEARCH();
      }
    },
  },
  async mounted(): Promise<void> {
    await (this as any).LOAD_MANIFEST();
    this.calculateNavbarHeight();
    window.addEventListener('resize', this.calculateNavbarHeight);
  },
  beforeDestroy(): void {
    window.removeEventListener('resize', this.calculateNavbarHeight);
  },
  methods: {
    ...mapActions(['LOAD_MANIFEST', 'SEARCH_DOCUMENTS', 'CLEAR_SEARCH']),
    calculateNavbarHeight(): void {
      const navbar = document.querySelector('.navbar');
      if (navbar) {
        this.navbarHeight = (navbar as HTMLElement).offsetHeight;
      } else {
        this.navbarHeight = 56;
      }
    },
    handleSearch: debounce(function handleSearchDebounced(this: any) {
      this.SEARCH_DOCUMENTS(this.searchQuery);
    }, 300),
  },
});
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
