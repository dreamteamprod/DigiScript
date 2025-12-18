import log from 'loglevel';
import Fuse from 'fuse.js';

export default {
  state: {
    manifest: [], // Array of { title, slug, path, category }
    documents: {}, // Cache: { slug: markdownContent }
    currentDocument: null, // Currently viewed doc slug
    loading: false,
    error: null,
    searchIndex: null, // Fuse.js instance
    searchResults: [],
  },
  mutations: {
    SET_MANIFEST(state, manifest) {
      state.manifest = manifest;
    },
    SET_DOCUMENT(state, { slug, content }) {
      state.documents[slug] = content;
    },
    SET_LOADING(state, loading) {
      state.loading = loading;
    },
    SET_ERROR(state, error) {
      state.error = error;
    },
    SET_CURRENT_DOCUMENT(state, slug) {
      state.currentDocument = slug;
    },
    SET_SEARCH_INDEX(state, fuseInstance) {
      state.searchIndex = fuseInstance;
    },
    SET_SEARCH_RESULTS(state, results) {
      state.searchResults = results;
    },
  },
  actions: {
    async LOAD_MANIFEST(context) {
      try {
        const response = await fetch('/docs/manifest.json');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const manifest = await response.json();
        context.commit('SET_MANIFEST', manifest);

        // Initialize Fuse.js search
        const fuse = new Fuse(manifest, {
          keys: ['title', 'path'],
          threshold: 0.3,
          includeScore: true,
        });
        context.commit('SET_SEARCH_INDEX', fuse);

        log.info(`Loaded documentation manifest with ${manifest.length} documents`);
      } catch (error) {
        log.error('Failed to load documentation manifest:', error);
        context.commit('SET_ERROR', 'Failed to load documentation manifest');
      }
    },

    async LOAD_DOCUMENT(context, slug) {
      // Check cache first
      if (context.state.documents[slug]) {
        context.commit('SET_CURRENT_DOCUMENT', slug);
        context.commit('SET_ERROR', null);
        return;
      }

      context.commit('SET_LOADING', true);
      const doc = context.state.manifest.find((d) => d.slug === slug);

      if (!doc) {
        context.commit('SET_ERROR', 'Document not found');
        context.commit('SET_LOADING', false);
        return;
      }

      try {
        const response = await fetch(`/docs/${doc.path}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const content = await response.text();
        context.commit('SET_DOCUMENT', { slug, content });
        context.commit('SET_CURRENT_DOCUMENT', slug);
        context.commit('SET_ERROR', null);
      } catch (error) {
        log.error('Failed to load documentation:', error);
        context.commit('SET_ERROR', 'Failed to load documentation');
      } finally {
        context.commit('SET_LOADING', false);
      }
    },

    SEARCH_DOCUMENTS(context, query) {
      if (!context.state.searchIndex) {
        log.warn('Search index not initialized');
        return;
      }

      if (!query || query.trim() === '') {
        context.commit('SET_SEARCH_RESULTS', []);
        return;
      }

      const results = context.state.searchIndex.search(query);
      context.commit('SET_SEARCH_RESULTS', results.map((r) => r.item));
    },

    CLEAR_SEARCH(context) {
      context.commit('SET_SEARCH_RESULTS', []);
    },
  },
  getters: {
    DOCUMENTATION_MANIFEST: (state) => state.manifest,
    CURRENT_DOCUMENT_CONTENT: (state) => (state.currentDocument
      ? state.documents[state.currentDocument]
      : null),
    IS_LOADING: (state) => state.loading,
    ERROR: (state) => state.error,
    SEARCH_RESULTS: (state) => state.searchResults,
  },
};
