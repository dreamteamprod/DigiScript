import log from 'loglevel';
import Fuse from 'fuse.js';
import { defineStore } from 'pinia';

interface HelpManifestEntry {
  title: string;
  slug: string;
  path: string;
  category: string;
}

interface HelpState {
  manifest: HelpManifestEntry[];
  documents: Record<string, string>;
  currentDocument: string | null;
  loading: boolean;
  error: string | null;
  searchIndex: Fuse<HelpManifestEntry> | null;
  searchResults: HelpManifestEntry[];
}

export const useHelpStore = defineStore('help', {
  state: (): HelpState => ({
    manifest: [],
    documents: {},
    currentDocument: null,
    loading: false,
    error: null,
    searchIndex: null,
    searchResults: [],
  }),

  getters: {
    documentationManifest: (state) => state.manifest,
    currentDocumentContent: (state) =>
      state.currentDocument ? state.documents[state.currentDocument] : null,
    isLoading: (state) => state.loading,
    searchResults: (state) => state.searchResults,
  },

  actions: {
    async loadManifest() {
      try {
        const response = await fetch('/docs/manifest.json');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const manifest: HelpManifestEntry[] = await response.json();
        this.manifest = manifest;
        this.searchIndex = new Fuse(manifest, {
          keys: ['title', 'path'],
          threshold: 0.3,
          includeScore: true,
        });
        log.info(`Loaded documentation manifest with ${manifest.length} documents`);
      } catch (error) {
        log.error('Failed to load documentation manifest:', error);
        this.error = 'Failed to load documentation manifest';
      }
    },

    async loadDocument(slug: string) {
      if (this.documents[slug]) {
        this.currentDocument = slug;
        this.error = null;
        return;
      }

      this.loading = true;
      const doc = this.manifest.find((d) => d.slug === slug);

      if (!doc) {
        this.error = 'Document not found';
        this.loading = false;
        return;
      }

      try {
        const response = await fetch(`/docs/${doc.path}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const content = await response.text();
        this.documents[slug] = content;
        this.currentDocument = slug;
        this.error = null;
      } catch (error) {
        log.error('Failed to load documentation:', error);
        this.error = 'Failed to load documentation';
      } finally {
        this.loading = false;
      }
    },

    searchDocuments(query: string) {
      if (!this.searchIndex) {
        log.warn('Search index not initialized');
        return;
      }
      if (!query || query.trim() === '') {
        this.searchResults = [];
        return;
      }
      this.searchResults = this.searchIndex.search(query).map((r) => r.item);
    },

    clearSearch() {
      this.searchResults = [];
    },
  },
});
