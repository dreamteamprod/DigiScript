<template>
  <div class="home">
    <div class="welcome-section">
      <h1>Welcome to DigiScript Vue 3</h1>
      <p class="lead">Phase 1 Migration Foundation</p>
    </div>

    <div class="status-grid">
      <div class="status-card">
        <h3>Framework Status</h3>
        <ul>
          <li>✅ Vue 3.4+ - Composition API</li>
          <li>✅ TypeScript Support</li>
          <li>✅ Vite 5+ Build System</li>
          <li>✅ Vue Router 4</li>
          <li>✅ Pinia State Management</li>
        </ul>
      </div>

      <div class="status-card">
        <h3>Development Environment</h3>
        <ul>
          <li>✅ Hot Module Replacement</li>
          <li>✅ Development Server (Port 3000)</li>
          <li>✅ API Proxy to Backend</li>
          <li>✅ TypeScript Type Checking</li>
          <li>✅ ESLint Configuration</li>
        </ul>
      </div>

      <div class="status-card">
        <h3>Next Phases</h3>
        <ul>
          <li>⏳ Bootstrap Vue 3 Integration</li>
          <li>⏳ WebSocket Communication</li>
          <li>⏳ Authentication System</li>
          <li>⏳ Component Migration</li>
          <li>⏳ Store Migration</li>
        </ul>
      </div>
    </div>

    <div class="info-section">
      <h2>Phase 1 Complete</h2>
      <p>
        This Vue 3 application runs alongside the existing Vue 2 application without interference.
        The Vue 2 app continues to serve at <code>/</code> while this Vue 3 app serves at
        <code>/v3/</code>.
      </p>
      <p>
        Future phases will gradually migrate functionality from Vue 2 to Vue 3,
        maintaining full backward compatibility until the migration is complete.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
// Vue 3 Composition API
// No reactive data needed for this static view yet
</script>

<style scoped>
.home {
  padding: 2rem 0;
}

.welcome-section {
  text-align: center;
  margin-bottom: 3rem;
}

.welcome-section h1 {
  font-size: 3rem;
  color: #1a202c;
  margin-bottom: 0.5rem;
}

.lead {
  font-size: 1.25rem;
  color: #718096;
  margin-bottom: 0;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin-bottom: 3rem;
}

.status-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.status-card h3 {
  color: #2d3748;
  margin-bottom: 1rem;
  font-size: 1.25rem;
}

.status-card ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.status-card li {
  padding: 0.5rem 0;
  border-bottom: 1px solid #f7fafc;
}

.status-card li:last-child {
  border-bottom: none;
}

.info-section {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
}

.info-section h2 {
  color: #28a745;
  margin-bottom: 1rem;
}

.info-section code {
  background: #e9ecef;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}
</style>
