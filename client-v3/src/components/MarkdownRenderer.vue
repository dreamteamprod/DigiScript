<template>
  <!-- eslint-disable vue/no-v-html -->
  <div class="markdown-content" v-html="renderedHtml" />
  <!-- eslint-enable vue/no-v-html -->
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import log from 'loglevel';

const props = defineProps<{ content: string }>();

const renderedHtml = ref('');

watch(
  () => props.content,
  async (content) => {
    if (!content) {
      renderedHtml.value = '';
      return;
    }
    try {
      const raw = await marked.parse(content);
      let html = transformImagePaths(raw);
      html = transformMarkdownLinks(html);
      renderedHtml.value = DOMPurify.sanitize(html, {
        ALLOWED_TAGS: [
          'h1',
          'h2',
          'h3',
          'h4',
          'h5',
          'h6',
          'p',
          'a',
          'ul',
          'ol',
          'li',
          'img',
          'code',
          'pre',
          'strong',
          'em',
          'blockquote',
          'table',
          'thead',
          'tbody',
          'tr',
          'th',
          'td',
          'br',
          'hr',
        ],
        ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class'],
      });
    } catch (error) {
      log.error('Error rendering markdown:', error);
      renderedHtml.value = '<p class="text-danger">Error rendering documentation</p>';
    }
  },
  { immediate: true }
);

function transformImagePaths(html: string): string {
  return html
    .replace(/src="\.\.\/\.\.\/images\//g, 'src="/docs/images/')
    .replace(/src="\.\.\/images\//g, 'src="/docs/images/');
}

function transformMarkdownLinks(html: string): string {
  const base = import.meta.env.BASE_URL;
  return html
    .replace(
      /href="(\.\.\/)*(pages\/[^"]+)\.md"/g,
      (_match: string, _dots: string, path: string) => {
        const slug = path.replace(/^pages\//, '').replace(/_/g, '-');
        return `href="${base}help/${slug}"`;
      }
    )
    .replace(/href="\.\/([^"]+)\.md"/g, (_match: string, path: string) => {
      const slug = path.replace(/_/g, '-');
      return `href="${base}help/${slug}"`;
    });
}
</script>

<style scoped>
.markdown-content {
  text-align: left;
  color: #ebebeb;
  line-height: 1.6;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  color: #00bc8c;
  margin-top: 1.5rem;
  margin-bottom: 1rem;
  font-weight: 500;
}

.markdown-content :deep(h1) {
  font-size: 2.5rem;
  border-bottom: 1px solid #375a7f;
  padding-bottom: 0.5rem;
}

.markdown-content :deep(h2) {
  font-size: 2rem;
  border-bottom: 1px solid #375a7f;
  padding-bottom: 0.3rem;
}

.markdown-content :deep(h3) {
  font-size: 1.75rem;
}

.markdown-content :deep(h4) {
  font-size: 1.5rem;
}

.markdown-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 0.25rem;
  margin: 1rem 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.markdown-content :deep(a) {
  color: #00bc8c;
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  color: #00efb2;
  text-decoration: underline;
}

.markdown-content :deep(code) {
  background-color: #375a7f;
  color: #ebebeb;
  padding: 0.2rem 0.4rem;
  border-radius: 0.25rem;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 0.875rem;
}

.markdown-content :deep(pre) {
  background-color: #375a7f;
  color: #ebebeb;
  padding: 1rem;
  border-radius: 0.25rem;
  overflow-x: auto;
  margin: 1rem 0;
}

.markdown-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
  font-size: 0.875rem;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid #00bc8c;
  padding-left: 1rem;
  margin: 1rem 0;
  color: #b8b8b8;
  font-style: italic;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 0.5rem 0;
  padding-left: 2rem;
}

.markdown-content :deep(li) {
  margin: 0.25rem 0;
}

.markdown-content :deep(table) {
  width: 100%;
  margin: 1rem 0;
  border-collapse: collapse;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  padding: 0.75rem;
  border: 1px solid #375a7f;
}

.markdown-content :deep(th) {
  background-color: #375a7f;
  color: #00bc8c;
  font-weight: 600;
}

.markdown-content :deep(tr:nth-child(even)) {
  background-color: rgba(55, 90, 127, 0.3);
}

.markdown-content :deep(hr) {
  border: none;
  border-top: 1px solid #375a7f;
  margin: 2rem 0;
}

.markdown-content :deep(p) {
  margin: 0.75rem 0;
}
</style>
