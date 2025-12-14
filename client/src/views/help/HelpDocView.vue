<template>
  <div class="help-doc">
    <b-spinner
      v-if="loading"
      variant="info"
      style="width: 3rem; height: 3rem;"
    />
    <b-alert
      v-else-if="error"
      variant="danger"
      show
    >
      <strong>Error:</strong> {{ error }}
      <br>
      <b-button
        variant="outline-danger"
        size="sm"
        class="mt-2"
        @click="retry"
      >
        Retry
      </b-button>
    </b-alert>
    <MarkdownRenderer
      v-else-if="documentContent"
      :content="documentContent"
    />
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import MarkdownRenderer from '@/vue_components/MarkdownRenderer.vue';

export default {
  name: 'HelpDocView',
  components: {
    MarkdownRenderer,
  },
  computed: {
    ...mapGetters([
      'CURRENT_DOCUMENT_CONTENT',
      'IS_LOADING',
      'ERROR',
      'DOCUMENTATION_MANIFEST',
    ]),
    documentContent() {
      return this.CURRENT_DOCUMENT_CONTENT;
    },
    loading() {
      return this.IS_LOADING;
    },
    error() {
      return this.ERROR;
    },
  },
  watch: {
    '$route.params.slug': {
      handler(newSlug) {
        if (newSlug) {
          this.loadDocument(newSlug);
        }
      },
      immediate: true,
    },
  },
  methods: {
    ...mapActions([
      'LOAD_DOCUMENT',
      'LOAD_MANIFEST',
    ]),
    async loadDocument(slug) {
      // Wait for manifest to load if it hasn't been loaded yet
      if (!this.DOCUMENTATION_MANIFEST || this.DOCUMENTATION_MANIFEST.length === 0) {
        await this.LOAD_MANIFEST();
      }
      await this.LOAD_DOCUMENT(slug);
    },
    async retry() {
      const { slug } = this.$route.params;
      if (slug) {
        await this.loadDocument(slug);
      }
    },
  },
};
</script>
