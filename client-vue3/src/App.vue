<template>
  <div id="app">
    <header class="app-header">
      <nav class="navbar">
        <div class="navbar-brand">
          <h1>DigiScript v3</h1>
        </div>
        <div class="navbar-nav">
          <router-link to="/" class="nav-link">Home</router-link>
          <router-link to="/about" class="nav-link">About</router-link>
        </div>
      </nav>
    </header>

    <main class="main-content">
      <router-view />
    </main>

    <footer class="app-footer">
      <p>&copy; 2024 DigiScript - Vue 3 Migration (Phase 1)</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
// Vue 3 Composition API setup
// Future phases will add more functionality here
</script>

<style scoped>
.app-header {
  background: #1a202c;
  color: white;
  padding: 1rem 0;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
}

.navbar-brand h1 {
  margin: 0;
  font-size: 1.5rem;
}

.navbar-nav {
  display: flex;
  gap: 2rem;
}

.nav-link {
  color: white;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.nav-link:hover,
.nav-link.router-link-active {
  background-color: #2d3748;
  color: white;
  text-decoration: none;
}

.main-content {
  min-height: calc(100vh - 140px);
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.app-footer {
  background: #f8f9fa;
  text-align: center;
  padding: 1rem;
  margin-top: 2rem;
}

.app-footer p {
  margin: 0;
  color: #6c757d;
}
</style>
