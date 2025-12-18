<template>
  <!-- eslint-disable vue/no-v-html -->
  <div
    class="markdown-content"
    v-html="renderedHtml"
  />
  <!-- eslint-enable vue/no-v-html -->
</template>

<script>
import { marked } from 'marked';
import DOMPurify from 'dompurify';

export default {
  name: 'MarkdownRenderer',
  props: {
    content: {
      type: String,
      required: true,
    },
  },
  computed: {
    renderedHtml() {
      if (!this.content) return '';

      try {
        const rawHtml = marked.parse(this.content);
        let transformedHtml = this.transformImagePaths(rawHtml);
        transformedHtml = this.transformMarkdownLinks(transformedHtml);
        return DOMPurify.sanitize(transformedHtml, {
          ALLOWED_TAGS: [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'a', 'ul', 'ol', 'li',
            'img', 'code', 'pre',
            'strong', 'em', 'blockquote',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'br', 'hr',
          ],
          ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class'],
        });
      } catch (error) {
        this.$log.error('Error rendering markdown:', error);
        return '<p class="text-danger">Error rendering documentation</p>';
      }
    },
  },
  methods: {
    transformImagePaths(html) {
      // Transform: ../images/topic/file.png → /docs/images/topic/file.png
      // Also handles: ../../images/topic/file.png for nested docs
      return html.replace(
        /src="\.\.\/\.\.\/images\//g,
        'src="/docs/images/',
      ).replace(
        /src="\.\.\/images\//g,
        'src="/docs/images/',
      );
    },
    transformMarkdownLinks(html) {
      // Transform internal .md links to /help routes
      // Examples:
      // href="./pages/getting_started.md" → href="/help/getting-started"
      // href="../pages/show_config.md" → href="/help/show-config"
      return html.replace(
        /href="(\.\.\/)*(pages\/[^"]+)\.md"/g,
        (match, dots, path) => {
          // Remove 'pages/' prefix and convert underscores to dashes
          const withoutPages = path.replace(/^pages\//, '');
          const slug = withoutPages.replace(/_/g, '-');
          return `href="/help/${slug}"`;
        },
      ).replace(
        /href="\.\/([^"]+)\.md"/g,
        (match, path) => {
          // Handle same-directory links
          const slug = path.replace(/_/g, '-');
          return `href="/help/${slug}"`;
        },
      );
    },
  },
};
</script>

<style scoped>
.markdown-content {
  text-align: left;
  color: #ebebeb;
  line-height: 1.6;
}

.markdown-content >>> h1,
.markdown-content >>> h2,
.markdown-content >>> h3,
.markdown-content >>> h4,
.markdown-content >>> h5,
.markdown-content >>> h6 {
  color: #00bc8c;
  margin-top: 1.5rem;
  margin-bottom: 1rem;
  font-weight: 500;
}

.markdown-content >>> h1 {
  font-size: 2.5rem;
  border-bottom: 1px solid #375a7f;
  padding-bottom: 0.5rem;
}

.markdown-content >>> h2 {
  font-size: 2rem;
  border-bottom: 1px solid #375a7f;
  padding-bottom: 0.3rem;
}

.markdown-content >>> h3 {
  font-size: 1.75rem;
}

.markdown-content >>> h4 {
  font-size: 1.5rem;
}

.markdown-content >>> img {
  max-width: 100%;
  height: auto;
  border-radius: 0.25rem;
  margin: 1rem 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.markdown-content >>> a {
  color: #00bc8c;
  text-decoration: none;
}

.markdown-content >>> a:hover {
  color: #00efb2;
  text-decoration: underline;
}

.markdown-content >>> code {
  background-color: #375a7f;
  color: #ebebeb;
  padding: 0.2rem 0.4rem;
  border-radius: 0.25rem;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 0.875rem;
}

.markdown-content >>> pre {
  background-color: #375a7f;
  color: #ebebeb;
  padding: 1rem;
  border-radius: 0.25rem;
  overflow-x: auto;
  margin: 1rem 0;
}

.markdown-content >>> pre code {
  background-color: transparent;
  padding: 0;
  font-size: 0.875rem;
}

.markdown-content >>> blockquote {
  border-left: 4px solid #00bc8c;
  padding-left: 1rem;
  margin: 1rem 0;
  color: #b8b8b8;
  font-style: italic;
}

.markdown-content >>> ul,
.markdown-content >>> ol {
  margin: 0.5rem 0;
  padding-left: 2rem;
}

.markdown-content >>> li {
  margin: 0.25rem 0;
}

.markdown-content >>> table {
  width: 100%;
  margin: 1rem 0;
  border-collapse: collapse;
}

.markdown-content >>> th,
.markdown-content >>> td {
  padding: 0.75rem;
  border: 1px solid #375a7f;
}

.markdown-content >>> th {
  background-color: #375a7f;
  color: #00bc8c;
  font-weight: 600;
}

.markdown-content >>> tr:nth-child(even) {
  background-color: rgba(55, 90, 127, 0.3);
}

.markdown-content >>> hr {
  border: none;
  border-top: 1px solid #375a7f;
  margin: 2rem 0;
}

.markdown-content >>> p {
  margin: 0.75rem 0;
}
</style>
