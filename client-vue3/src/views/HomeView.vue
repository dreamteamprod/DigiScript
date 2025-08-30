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
        <h3>Phase 2 Progress</h3>
        <ul>
          <li>✅ Pinia State Management</li>
          <li>✅ WebSocket Communication</li>
          <li>✅ Authentication System</li>
          <li>⏳ Bootstrap Vue 3 Integration</li>
          <li>⏳ Component Migration</li>
        </ul>
      </div>
    </div>

    <div class="test-links">
      <h2>Development & Testing</h2>
      <div class="link-buttons">
        <router-link to="/websocket-test" class="test-link">
          🔌 WebSocket Connection Test
        </router-link>
        <router-link to="/about" class="test-link">
          ℹ️ About This Application
        </router-link>
      </div>
    </div>

    <div class="info-section">
      <h2>Phase 2: State Management & WebSocket</h2>
      <p>
        <strong>COMPLETED:</strong> WebSocket communication and state management have been successfully migrated to Vue 3.
        This includes Pinia stores for authentication and WebSocket state, with full OP/ACTION message routing compatibility.
      </p>
      <p>
        The WebSocket implementation maintains 100% compatibility with the existing backend API,
        preserving all message formats and authentication flows used by the Vue 2 application.
      </p>
      <p>
        <strong>Test the implementation:</strong> Use the WebSocket test page above to verify connection,
        authentication, and message handling functionality.
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

.test-links {
  margin-bottom: 3rem;
  text-align: center;
}

.test-links h2 {
  color: #2d3748;
  margin-bottom: 1.5rem;
}

.link-buttons {
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.test-link {
  display: inline-block;
  padding: 1rem 1.5rem;
  background: #007bff;
  color: white;
  text-decoration: none;
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 123, 255, 0.2);
}

.test-link:hover {
  background: #0056b3;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 123, 255, 0.3);
  color: white;
  text-decoration: none;
}
</style>
