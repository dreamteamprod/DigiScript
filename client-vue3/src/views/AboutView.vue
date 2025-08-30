<template>
  <div class="about">
    <div class="about-header">
      <h1>About DigiScript Vue 3 Migration</h1>
      <p class="subtitle">Technical Implementation Details</p>
    </div>

    <div class="content-sections">
      <section class="section">
        <h2>Migration Strategy</h2>
        <p>
          We're implementing a side-by-side migration approach that allows both Vue 2 and Vue 3
          applications to coexist during the transition period. This ensures zero downtime and
          allows for gradual feature migration.
        </p>
        <ul>
          <li><strong>Phase 1:</strong> Foundation & Infrastructure (Current)</li>
          <li><strong>Phase 2:</strong> Core Components Migration</li>
          <li><strong>Phase 3:</strong> Feature-by-Feature Migration</li>
          <li><strong>Phase 4:</strong> Final Cutover & Cleanup</li>
        </ul>
      </section>

      <section class="section">
        <h2>Technical Architecture</h2>
        <div class="tech-grid">
          <div class="tech-item">
            <h4>Vue 3.4+</h4>
            <p>Composition API, improved TypeScript support, better performance</p>
          </div>
          <div class="tech-item">
            <h4>Vite 5+</h4>
            <p>Fast build tool with HMR, ESM-based development</p>
          </div>
          <div class="tech-item">
            <h4>Pinia</h4>
            <p>Modern state management, replacing Vuex</p>
          </div>
          <div class="tech-item">
            <h4>Vue Router 4</h4>
            <p>Updated routing with composition API support</p>
          </div>
          <div class="tech-item">
            <h4>TypeScript</h4>
            <p>Full TypeScript integration for better DX</p>
          </div>
          <div class="tech-item">
            <h4>ESLint</h4>
            <p>Code quality with Vue 3 + TypeScript rules</p>
          </div>
        </div>
      </section>

      <section class="section">
        <h2>Current Status</h2>
        <div class="status-list">
          <div class="status-item completed">
            <span class="status-icon">✅</span>
            <span>Project structure and build system</span>
          </div>
          <div class="status-item completed">
            <span class="status-icon">✅</span>
            <span>TypeScript configuration</span>
          </div>
          <div class="status-item completed">
            <span class="status-icon">✅</span>
            <span>Vue Router 4 setup</span>
          </div>
          <div class="status-item completed">
            <span class="status-icon">✅</span>
            <span>Pinia state management</span>
          </div>
          <div class="status-item completed">
            <span class="status-icon">✅</span>
            <span>Development server with API proxy</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
// Static content - no reactive data needed yet
</script>

<style scoped>
.about {
  max-width: 800px;
  margin: 0 auto;
}

.about-header {
  text-align: center;
  margin-bottom: 3rem;
}

.about-header h1 {
  font-size: 2.5rem;
  color: #1a202c;
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 1.125rem;
  color: #718096;
}

.content-sections {
  display: flex;
  flex-direction: column;
  gap: 3rem;
}

.section {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.section h2 {
  color: #2d3748;
  margin-bottom: 1rem;
  font-size: 1.5rem;
}

.section h4 {
  color: #4a5568;
  margin-bottom: 0.5rem;
}

.section p {
  color: #718096;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.section ul {
  color: #718096;
  line-height: 1.6;
}

.section ul li {
  margin-bottom: 0.5rem;
}

.tech-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-top: 1rem;
}

.tech-item {
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #007bff;
}

.tech-item h4 {
  color: #007bff;
  margin-bottom: 0.5rem;
}

.tech-item p {
  margin-bottom: 0;
  font-size: 0.9rem;
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 6px;
}

.status-item.completed {
  background: #d4edda;
}

.status-icon {
  font-size: 1.125rem;
}
</style>
