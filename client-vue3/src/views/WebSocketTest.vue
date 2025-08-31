<template>
  <div class="websocket-test">
    <h1>WebSocket Connection Test</h1>

    <div class="status-section">
      <h2>Connection Status</h2>
      <div class="status-grid">
        <div class="status-item">
          <label>Connected:</label>
          <span
            :class="{
              'text-success': websocketStore.isConnected,
              'text-danger': !websocketStore.isConnected
            }"
          >
            {{ websocketStore.isConnected ? 'Yes' : 'No' }}
          </span>
        </div>

        <div class="status-item">
          <label>Authenticated:</label>
          <span
            :class="{
              'text-success': websocketStore.authenticated,
              'text-danger': !websocketStore.authenticated
            }"
          >
            {{ websocketStore.authenticated ? 'Yes' : 'No' }}
          </span>
        </div>

        <div class="status-item">
          <label>Internal UUID:</label>
          <span>{{ websocketStore.internalUUID || 'None' }}</span>
        </div>

        <div class="status-item">
          <label>Error Count:</label>
          <span :class="{ 'text-danger': websocketStore.errorCount > 0 }">
            {{ websocketStore.errorCount }}
          </span>
        </div>

        <div class="status-item">
          <label>Healthy:</label>
          <span
            :class="{
              'text-success': websocketStore.websocketHealthy,
              'text-danger': !websocketStore.websocketHealthy
            }"
          >
            {{ websocketStore.websocketHealthy ? 'Yes' : 'No' }}
          </span>
        </div>

        <div class="status-item">
          <label>Pending Operations:</label>
          <span :class="{ 'text-warning': websocketStore.websocketHasPendingOperations }">
            {{ websocketStore.websocketHasPendingOperations ? 'Yes' : 'No' }}
          </span>
        </div>
      </div>
    </div>

    <div class="auth-section">
      <h2>Authentication Status</h2>
      <div class="status-grid">
        <div class="status-item">
          <label>Has Auth Token:</label>
          <span
            :class="{
              'text-success': authStore.isAuthenticated,
              'text-danger': !authStore.isAuthenticated
            }"
          >
            {{ authStore.isAuthenticated ? 'Yes' : 'No' }}
          </span>
        </div>

        <div class="status-item">
          <label>Current User:</label>
          <span>{{ authStore.currentUser?.username || 'None' }}</span>
        </div>

        <div class="status-item">
          <label>Is Admin:</label>
          <span>{{ authStore.isAdmin ? 'Yes' : 'No' }}</span>
        </div>
      </div>
    </div>

    <div class="actions-section">
      <h2>Actions</h2>
      <div class="action-buttons">
        <button @click="connectWebSocket" :disabled="isConnected" class="btn btn-primary">
          Connect WebSocket
        </button>

        <button @click="disconnectWebSocket" :disabled="!isConnected" class="btn btn-secondary">
          Disconnect WebSocket
        </button>

        <button @click="sendTestMessage" :disabled="!isConnected" class="btn btn-info">
          Send Test Message
        </button>

        <button
          @click="authenticateWS"
          :disabled="!isConnected || !authStore.isAuthenticated"
          class="btn btn-success"
        >
          Authenticate WebSocket
        </button>
      </div>
    </div>

    <div class="messages-section">
      <h2>Recent Messages</h2>
      <div class="message-log">
        <div v-if="lastMessage" class="message-item">
          <strong>Last Message:</strong>
          <pre>{{ JSON.stringify(lastMessage, null, 2) }}</pre>
        </div>
        <div v-else class="no-messages">
          No messages received yet
        </div>
      </div>
    </div>

    <div class="login-section" v-if="!authStore.isAuthenticated">
      <h2>Test Login</h2>
      <div class="login-form">
        <div class="form-group">
          <label for="username">Username:</label>
          <input v-model="loginForm.username" type="text" id="username" class="form-control">
        </div>

        <div class="form-group">
          <label for="password">Password:</label>
          <input v-model="loginForm.password" type="password" id="password" class="form-control">
        </div>

        <button @click="testLogin" class="btn btn-primary">Test Login</button>
      </div>
    </div>

    <div class="logout-section" v-if="authStore.isAuthenticated">
      <h2>Logout</h2>
      <button @click="testLogout" class="btn btn-warning">Logout</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useWebSocketStore } from '../stores/websocket';
import { useAuthStore } from '../stores/auth';
import { useWebSocket } from '../composables/useWebSocket';

const websocketStore = useWebSocketStore();
const authStore = useAuthStore();

// Initialize WebSocket connection
const {
  isConnected, sendObj, connect, disconnect, authenticateWebSocket,
} = useWebSocket();

const lastMessage = computed(() => websocketStore.message);

const loginForm = ref({
  username: '',
  password: '',
});

// Actions
const connectWebSocket = () => {
  connect();
};

const disconnectWebSocket = () => {
  disconnect();
};

const sendTestMessage = () => {
  sendObj({
    OP: 'TEST',
    DATA: { message: 'Hello from Vue 3!', timestamp: new Date().toISOString() },
  });
};

const authenticateWS = async () => {
  await authenticateWebSocket();
};

const testLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    console.warn('Please enter both username and password');
    return;
  }

  try {
    const loginUrl = `${window.location.protocol}//${window.location.hostname}:${window.location.port}/api/v1/auth/login`;
    const response = await fetch(loginUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: loginForm.value.username,
        password: loginForm.value.password,
        session_id: websocketStore.internalUUID,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      if (data.access_token) {
        authStore.setAuthToken(data.access_token);
        await authStore.getCurrentUser();
        await authStore.getCurrentRbac();
        await authStore.getUserSettings();
        await authStore.setupTokenRefresh();
        console.log('Login successful!');
      }
    } else {
      const errorData = await response.json();
      console.error(`Login failed: ${errorData.message}`);
    }
  } catch (error) {
    console.error('Login error:', error);
    console.error('Login failed due to network error');
  }
};

const testLogout = async () => {
  try {
    if (authStore.authToken) {
      const logoutUrl = `${window.location.protocol}//${window.location.hostname}:${window.location.port}/api/v1/auth/logout`;
      const response = await fetch(logoutUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authStore.authToken}`,
        },
        body: JSON.stringify({
          session_id: websocketStore.internalUUID,
        }),
      });

      if (response.ok) {
        console.log('Server logout successful');
      } else {
        console.warn('Server logout failed, but clearing local state');
      }
    }

    authStore.clearAuthData();
    websocketStore.clearWsAuthentication();
    console.log('Logged out successfully!');
  } catch (error) {
    console.error('Logout error:', error);
    authStore.clearAuthData();
    websocketStore.clearWsAuthentication();
    console.warn('Logged out (with some errors)');
  }
};

// Watch for WebSocket state changes and log them
watch(() => websocketStore.isConnected, (connected) => {
  console.log(`WebSocket connection state changed: ${connected ? 'connected' : 'disconnected'}`);
});

watch(() => websocketStore.authenticated, (authenticated) => {
  const status = authenticated ? 'authenticated' : 'not authenticated';
  console.log(`WebSocket authentication state changed: ${status}`);
});

watch(lastMessage, (message) => {
  if (message) {
    console.log('New WebSocket message received:', message);
  }
});
</script>

<style scoped>
.websocket-test {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.status-section,
.auth-section,
.actions-section,
.messages-section,
.login-section,
.logout-section {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  padding: 8px;
  background: white;
  border-radius: 4px;
  border: 1px solid #eee;
}

.status-item label {
  font-weight: bold;
  margin-right: 10px;
}

.text-success {
  color: #28a745;
  font-weight: bold;
}

.text-danger {
  color: #dc3545;
  font-weight: bold;
}

.text-warning {
  color: #ffc107;
  font-weight: bold;
}

.action-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-info {
  background-color: #17a2b8;
  color: white;
}

.btn-success {
  background-color: #28a745;
  color: white;
}

.btn-warning {
  background-color: #ffc107;
  color: #212529;
}

.message-log {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 10px;
  background: white;
}

.message-item pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 12px;
  margin: 0;
}

.no-messages {
  text-align: center;
  color: #666;
  font-style: italic;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
  max-width: 300px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-control {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

h1, h2 {
  margin-top: 0;
  color: #333;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
}

h2 {
  margin-bottom: 15px;
  font-size: 18px;
  border-bottom: 2px solid #007bff;
  padding-bottom: 5px;
}
</style>
