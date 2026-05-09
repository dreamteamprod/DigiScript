import log from 'loglevel';
import Fuse from 'fuse.js';
import type { Module } from 'vuex';
import type { RootState } from '@/types/store';

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

const module: Module<HelpState, RootState> = {
  state: {
    manifest: [],
    documents: {},
    currentDocument: null,
    loading: false,
    error: null,
    searchIndex: null,
    searchResults: [],
  },
  mutations: {
    SET_MANIFEST(state: HelpState, manifest: HelpManifestEntry[]) {
      state.manifest = manifest;
    },
    SET_DOCUMENT(state: HelpState, { slug, content }: { slug: string; content: string }) {
      state.documents[slug] = content;
    },
    SET_LOADING(state: HelpState, loading: boolean) {
      state.loading = loading;
    },
    SET_ERROR(state: HelpState, error: string | null) {
      state.error = error;
    },
    SET_CURRENT_DOCUMENT(state: HelpState, slug: string) {
      state.currentDocument = slug;
    },
    SET_SEARCH_INDEX(state: HelpState, fuseInstance: Fuse<HelpManifestEntry>) {
      state.searchIndex = fuseInstance;
    },
    SET_SEARCH_RESULTS(state: HelpState, results: HelpManifestEntry[]) {
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

    async LOAD_DOCUMENT(context, slug: string) {
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

    SEARCH_DOCUMENTS(context, query: string) {
      if (!context.state.searchIndex) {
        log.warn('Search index not initialized');
        return;
      }

      if (!query || query.trim() === '') {
        context.commit('SET_SEARCH_RESULTS', []);
        return;
      }

      const results = context.state.searchIndex.search(query);
      context.commit(
        'SET_SEARCH_RESULTS',
        results.map((r) => r.item)
      );
    },

    CLEAR_SEARCH(context) {
      context.commit('SET_SEARCH_RESULTS', []);
    },
  },
  getters: {
    DOCUMENTATION_MANIFEST: (state: HelpState) => state.manifest,
    CURRENT_DOCUMENT_CONTENT: (state: HelpState) =>
      state.currentDocument ? state.documents[state.currentDocument] : null,
    IS_LOADING: (state: HelpState) => state.loading,
    ERROR: (state: HelpState) => state.error,
    SEARCH_RESULTS: (state: HelpState) => state.searchResults,
  },
};

export default module;
