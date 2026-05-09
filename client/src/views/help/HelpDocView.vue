<template>
  <div class="help-doc">
    <b-spinner v-if="loading" variant="info" style="width: 3rem; height: 3rem" />
    <b-alert v-else-if="error" variant="danger" show>
      <strong>Error:</strong> {{ error }}
      <br />
      <b-button variant="outline-danger" size="sm" class="mt-2" @click="retry"> Retry </b-button>
    </b-alert>
    <MarkdownRenderer v-else-if="documentContent" :content="documentContent" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters, mapActions } from 'vuex';
import MarkdownRenderer from '@/vue_components/MarkdownRenderer.vue';

export default defineComponent({
  name: 'HelpDocView',
  components: {
    MarkdownRenderer,
  },
  computed: {
    ...mapGetters(['CURRENT_DOCUMENT_CONTENT', 'IS_LOADING', 'ERROR', 'DOCUMENTATION_MANIFEST']),
    documentContent(): string | null {
      return this.CURRENT_DOCUMENT_CONTENT;
    },
    loading(): boolean {
      return this.IS_LOADING;
    },
    error(): string | null {
      return this.ERROR;
    },
  },
  watch: {
    '$route.params.slug': {
      handler(newSlug: string) {
        if (newSlug) {
          this.loadDocument(newSlug);
        }
      },
      immediate: true,
    },
  },
  methods: {
    ...mapActions(['LOAD_DOCUMENT', 'LOAD_MANIFEST']),
    async loadDocument(slug: string): Promise<void> {
      if (!this.DOCUMENTATION_MANIFEST || this.DOCUMENTATION_MANIFEST.length === 0) {
        await (this as any).LOAD_MANIFEST();
      }
      await (this as any).LOAD_DOCUMENT(slug);
    },
    async retry(): Promise<void> {
      const { slug } = this.$route.params;
      if (slug) {
        await this.loadDocument(slug);
      }
    },
  },
});
</script>
