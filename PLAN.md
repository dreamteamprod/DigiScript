# Electron Standalone Frontend - Implementation Plan

**Feature**: Issue #839 - Standalone front end for DigiScript
**Branch**: `feature/electron-standalone-frontend`
**Target**: `dev` branch
**Approach**: Hybrid Build with Runtime Detection (Approach 3)

---

## Overview

Create an Electron-based standalone desktop application that can connect to remote DigiScript servers while maximizing code reuse with the existing web application.

### Key Requirements

- ✅ Electron app that connects to remote DigiScript servers
- ✅ mDNS service discovery for finding servers on local network
- ✅ Connection management (URL, optional credentials, nickname, last connected, SSL toggle)
- ✅ Version compatibility check (exact match required, block incompatible connections)
- ✅ Optional credential storage using Electron's safeStorage API
- ✅ Cross-platform support (Windows, macOS, Linux)
- ✅ Persistent WebSocket UUID across app restarts
- ✅ Optional auto-update capability via electron-updater
- ✅ Separate Vite dev server for Electron frontend

### Design Principles

1. **Maximum Code Reuse**: 95% of Vue app code shared between web and Electron
2. **Clean Separation**: Electron-specific code isolated in separate directory
3. **Minimal Changes**: Only 4 files modified in existing Vue app
4. **Great DX**: Electron dev mode loads Vite dev server (hot-reload works!)
5. **No Duplication**: Single codebase that detects runtime environment

---

## Architecture Decision: Hybrid Build with Runtime Detection

### Core Concept

A **lightweight platform abstraction layer** (3 files) that detects the runtime environment (browser vs Electron) and provides the appropriate implementation for URL resolution and storage.

### Why This Approach?

- **Best Developer Experience**: Vite dev server serves both web and Electron with hot-reload
- **Right Amount of Abstraction**: Clean platform layer without over-engineering
- **Maximum Code Reuse**: 95% shared, no duplication
- **Reasonable Complexity**: ~19 files total (15 new, 4 modified)
- **Maintainable**: Core app changes automatically apply to both targets
- **Time-Efficient**: ~3-4 weeks implementation time

### Key Innovation

The platform abstraction layer is the linchpin:
- Small (3 files, ~75 lines total)
- Highly testable
- Enables everything without polluting core Vue app
- Runtime detection via `window.electronAPI` presence

---

## Technical Decisions

### Credential Storage

**Solution**: Electron's built-in `safeStorage` API + `electron-store`

- Modern, official approach (used by VS Code)
- OS-level encryption (macOS Keychain, Windows DPAPI, Linux Secret Service)
- Zero native dependencies (replaces deprecated `keytar`)
- Simple API: `safeStorage.encryptString()` / `decryptString()`

**Sources**:
- [Electron safeStorage API](https://www.electronjs.org/docs/latest/api/safe-storage)
- [electron-store](https://www.npmjs.com/package/electron-store)

### Service Discovery

**Solution**: `bonjour-service` for mDNS/DNS-SD

- Service type: `_digiscript._tcp.local`
- Backend advertises: hostname, port, version (requires backend changes)
- Fallback: Manual entry always available (mDNS optional)

### Version Compatibility

**Policy**: Exact version match required

- Client version: `client/package.json`
- Server version: Exposed via `/api/v1/settings` endpoint
- Validation: Before connecting, fetch server settings and compare versions
- On mismatch: Block connection with clear error message

### Build Strategy

**Two Vite Configurations**:
- `vite.config.js` - Web build (unchanged) → `../server/static/`
- `vite.config.electron.js` - Electron renderer → `../electron/renderer/`

Key differences:
- `base: './'` for file:// protocol support
- Different output directory
- Same plugins, chunking strategy, optimizations

---

## Directory Structure

```
DigiScript/
├── client/                          # Vue frontend (shared)
│   ├── src/
│   │   ├── js/
│   │   │   ├── platform/           # NEW: Platform abstraction (3 files)
│   │   │   │   ├── index.js        # Environment detection + unified API
│   │   │   │   ├── browser.js      # Browser implementation
│   │   │   │   └── electron.js     # Electron renderer implementation
│   │   │   ├── utils.js            # MODIFIED: Use platform API
│   │   │   └── http-interceptor.js # UNCHANGED (works with platform)
│   │   ├── views/
│   │   │   └── electron/           # NEW: Electron-specific views (2 files)
│   │   │       ├── ServerSelector.vue
│   │   │       └── Settings.vue (optional)
│   │   ├── router/
│   │   │   └── index.js            # MODIFIED: Add electron routes
│   │   ├── store/
│   │   │   └── store.js            # MODIFIED: Conditional persistence
│   │   └── main.js                 # MODIFIED: Use platform for WebSocket URL
│   ├── vite.config.js              # EXISTING: Web build config
│   ├── vite.config.electron.js     # NEW: Electron renderer build config
│   └── package.json                # MODIFIED: Add electron build script
│
├── electron/                        # NEW: Electron-specific code
│   ├── main.js                      # Electron main process
│   ├── preload.js                   # Secure IPC bridge
│   ├── services/                    # Main process services
│   │   ├── ConnectionManager.js     # Connection CRUD + persistence
│   │   ├── VersionChecker.js        # Version compatibility check
│   │   └── MDNSDiscovery.js         # mDNS service discovery
│   ├── renderer/                    # Built Vue app (output from Vite)
│   │   └── (generated during build)
│   ├── package.json                 # Electron dependencies + scripts
│   └── forge.config.js              # Electron Forge packaging config
│
├── server/                          # UNCHANGED
│   └── static/                      # Web build output (unchanged)
│
└── PLAN.md                          # This file
```

---

## File Inventory

### New Files (15 total)

#### Platform Abstraction Layer (3 files)
1. `client/src/js/platform/index.js` - Environment detection, exports unified API
2. `client/src/js/platform/browser.js` - Browser implementation (uses window.location)
3. `client/src/js/platform/electron.js` - Electron implementation (IPC to electron-store)

#### Electron Main Process (4 files)
4. `electron/package.json` - Electron dependencies and build scripts
5. `electron/main.js` - Main process entry point, IPC handlers
6. `electron/preload.js` - Secure IPC bridge via contextBridge
7. `electron/forge.config.js` - Packaging configuration

#### Electron Services (3 files)
8. `electron/services/ConnectionManager.js` - Connection CRUD, persistence
9. `electron/services/VersionChecker.js` - Server version validation
10. `electron/services/MDNSDiscovery.js` - mDNS network scanning

#### Vue Components (2 files)
11. `client/src/views/electron/ServerSelector.vue` - Connection manager UI
12. `client/src/views/electron/Settings.vue` - Electron settings (optional)

#### Build Configuration (2 files)
13. `client/vite.config.electron.js` - Electron renderer build config
14. `.github/workflows/electron-build.yml` - CI/CD for multi-platform builds (optional)

#### Documentation (1 file)
15. `PLAN.md` - This file

### Modified Files (4 total)

1. `client/src/js/utils.js` - Use platform layer for baseURL()
2. `client/src/main.js` - Use platform layer for WebSocket URL
3. `client/src/store/store.js` - Conditional storage (sessionStorage vs electron-store)
4. `client/src/router/index.js` - Add Electron routes + connection guard

---

## Implementation Phases

### Phase 1: Platform Abstraction Foundation (Week 1, Days 1-5)

**Goal**: Create the platform layer and integrate into existing Vue app

**Tasks**:
- [ ] Create `client/src/js/platform/index.js` (environment detection)
- [ ] Create `client/src/js/platform/browser.js` (current behavior)
- [ ] Create `client/src/js/platform/electron.js` (IPC-based, placeholder)
- [ ] Modify `client/src/js/utils.js` to use platform.baseURL()
- [ ] Modify `client/src/main.js` WebSocket URL construction
- [ ] Modify `client/src/store/store.js` persistence config
- [ ] Test: Web build still works identically (regression test)
- [ ] Test: Platform detection logic with mock window.electronAPI

**Deliverable**: Web app works unchanged, platform layer ready for Electron

**Files Changed**: 3 new, 3 modified

---

### Phase 2: Electron Core Setup (Week 1-2, Days 6-10)

**Goal**: Set up Electron main process with IPC communication

**Tasks**:
- [ ] Create `electron/package.json` with dependencies
  - electron ^28.0.0
  - electron-store ^8.1.0
  - bonjour-service ^1.2.1
  - node-fetch ^3.3.2
  - @electron-forge/cli ^7.2.0
- [ ] Create `electron/main.js` (main process)
  - BrowserWindow creation
  - Dev mode: load http://localhost:5173
  - Prod mode: load file://renderer/index.html
- [ ] Create `electron/preload.js` (contextBridge API)
  - Expose window.electronAPI
  - IPC methods: getServerURL, setServerURL, getConnections, etc.
- [ ] Create `electron/services/ConnectionManager.js`
  - electron-store integration
  - CRUD operations
  - Schema: {id, url, nickname, lastConnected, credentials?, sslEnabled}
- [ ] Test: Run `npm start` in electron dir (shows blank window)
- [ ] Test: IPC communication (call window.electronAPI methods from console)

**Deliverable**: Electron app launches, loads Vite dev server, IPC works

**Files Changed**: 4 new

---

### Phase 3: Version Check & Discovery Services (Week 2, Days 11-13)

**Goal**: Implement server validation and discovery

**Tasks**:
- [ ] Create `electron/services/VersionChecker.js`
  - Fetch /api/v1/settings from server
  - Compare versions (exact match)
  - Return {compatible, serverVersion, clientVersion, error?}
- [ ] Create `electron/services/MDNSDiscovery.js`
  - Use bonjour-service
  - Scan for _digiscript._tcp.local
  - Return [{name, host, port, url}]
  - 5 second timeout
- [ ] Add IPC handlers in main.js
  - check-version
  - discover-servers
- [ ] Test: Version check against real server
- [ ] Test: mDNS discovery (requires backend changes or mock)

**Deliverable**: Version validation and discovery services functional

**Files Changed**: 2 new, 1 modified

---

### Phase 4: Connection Selector UI (Week 2-3, Days 14-18)

**Goal**: Build the connection management interface

**Tasks**:
- [ ] Create `client/src/views/electron/ServerSelector.vue`
  - List saved connections (nickname, URL, last connected)
  - "Discover Servers" button + results display
  - Manual entry form (URL, nickname, SSL toggle)
  - "Test Connection" button (version check)
  - "Connect" button (saves + redirects)
  - Delete connection button with confirmation
- [ ] Modify `client/src/router/index.js`
  - Add /electron/server-selector route (conditional)
  - Add beforeEach guard: redirect to selector if no connection
- [ ] Implement connection flow
  - Validate server version
  - Save connection to electron-store
  - Set active connection
  - Redirect to home page
- [ ] Test: Full connection workflow
- [ ] Test: Connection switching mid-session

**Deliverable**: Users can manage and connect to servers

**Files Changed**: 1 new, 1 modified

---

### Phase 5: Electron Build Configuration (Week 3, Days 19-21)

**Goal**: Configure build pipeline for Electron app

**Tasks**:
- [ ] Create `client/vite.config.electron.js`
  - Copy from vite.config.js
  - Change outDir to '../electron/renderer'
  - Change base to './'
  - Same plugins and chunking strategy
- [ ] Update `client/package.json`
  - Add script: "build:electron": "vite build --config vite.config.electron.js"
- [ ] Create `electron/forge.config.js`
  - Configure makers: squirrel (Win), zip (Mac), deb/rpm (Linux)
  - Set app ID, icon paths
- [ ] Test: Build renderer
  - `cd client && npm run build:electron`
  - Verify output in electron/renderer/
- [ ] Test: Package Electron app
  - `cd electron && npm run package`
  - Verify .app/.exe created
- [ ] Test: Create installers
  - `cd electron && npm run make`
  - Verify DMG/EXE/DEB/AppImage created

**Deliverable**: Electron app can be built and packaged for distribution

**Files Changed**: 2 new, 1 modified

---

### Phase 6: Credential Storage (Optional) (Week 3-4, Days 22-24)

**Goal**: Secure credential storage for saved connections

**Tasks**:
- [ ] Update `electron/services/ConnectionManager.js`
  - Add hasCredentials flag to connection schema
- [ ] Create credential storage in ConnectionManager
  - Use safeStorage.encryptString()
  - Store encrypted blob in electron-store
  - Implement getCredentials(), setCredentials(), deleteCredentials()
- [ ] Add to preload.js
  - Expose credentials IPC methods
- [ ] Update ServerSelector.vue
  - Add "Remember Credentials" checkbox
  - Add credential input fields (username/password)
  - Auto-fill credentials on reconnect
- [ ] Test: Save credentials
- [ ] Test: Decrypt and auto-login
- [ ] Test: Clear credentials

**Deliverable**: Optional credential storage working

**Files Changed**: 2 modified, 1 new

---

### Phase 7: Auto-Updater (Optional) (Week 4, Days 25-27)

**Goal**: Automatic update checking and installation

**Tasks**:
- [ ] Install electron-updater
- [ ] Create update service in main.js
  - Check for updates on app launch
  - Configure GitHub Releases as update server
- [ ] Create Settings.vue (Electron-specific)
  - Toggle auto-update preference
  - Manual "Check for Updates" button
  - Display current version
- [ ] Configure package.json publish settings
  - GitHub repository info
  - Update channel (stable, beta)
- [ ] Test update flow
  - Create test release on GitHub
  - Verify update prompt appears
  - Test download and install

**Deliverable**: Auto-update working via GitHub Releases

**Files Changed**: 1 new, 2 modified

---

### Phase 8: Testing & Polish (Week 4, Days 28-30)

**Goal**: Comprehensive testing and bug fixes

**Tasks**:
- [ ] Unit tests for platform layer
  - Mock window.electronAPI
  - Test browser vs Electron detection
- [ ] Integration tests
  - Connection CRUD operations
  - Version check logic
  - mDNS discovery (mocked)
- [ ] E2E tests
  - Full connection flow
  - WebSocket reconnection after app restart
  - Version mismatch blocking
- [ ] Manual testing
  - Test on all 3 platforms (macOS, Windows, Linux)
  - Connection switching
  - Persistent WebSocket UUID
- [ ] Bug fixes and polish
  - Error handling improvements
  - UI refinements
  - Loading states
- [ ] Documentation
  - Update README with Electron build instructions
  - Add user guide for connection management
  - Document dev workflow

**Deliverable**: Production-ready Electron app

---

## Development Workflows

### Web Development (Unchanged)

```bash
# Terminal 1: Backend
cd server
python3 main.py

# Terminal 2: Frontend dev server
cd client
npm run dev
# Access at http://localhost:5173
```

### Electron Development

```bash
# Terminal 1: Backend (or use remote server)
cd server
python3 main.py

# Terminal 2: Frontend dev server
cd client
npm run dev
# Runs on http://localhost:5173

# Terminal 3: Electron in dev mode
cd electron
NODE_ENV=development npm start
# Electron window loads http://localhost:5173
# Hot-reload works!
```

**Key Feature**: Same Vite dev server serves both web and Electron. No conflicts!

---

## Build Process

### Web Build (Unchanged)

```bash
cd client
npm ci
npm run build
# Output: ../server/static/
```

### Electron Build

```bash
# Step 1: Build Vue app for Electron
cd client
npm ci
npm run build:electron
# Output: ../electron/renderer/

# Step 2: Package Electron app (development testing)
cd ../electron
npm ci
npm run package
# Output: electron/out/DigiScript-darwin-x64/ (portable .app/.exe)

# Step 3: Create installers (production distribution)
npm run make
# Output:
# - macOS: electron/out/make/*.dmg
# - Windows: electron/out/make/squirrel.windows/*.exe
# - Linux: electron/out/make/*.deb, *.AppImage
```

---

## Data Flow

### Startup Flow (Electron)

```
1. User launches Electron app
   ↓
2. main.js loads
   → connectionManager.getActiveConnection()
   → If NO connection: Show ServerSelector.vue
   → If HAS connection: Load renderer with configured URL
   ↓
3. Renderer starts (Vue app)
   → platform/index.js detects window.electronAPI exists
   → platform/electron.js loads
   ↓
4. baseURL() called
   → IPC to main: getServerURL()
   → Main returns stored URL (e.g., "http://192.168.1.100:8080")
   ↓
5. WebSocket connects using returned URL
   ↓
6. Version check (background)
   → Fetch /api/v1/settings
   → Compare versions
   → If mismatch: Show warning, disconnect
```

### Connection Management Flow

```
1. User opens ServerSelector.vue
   ↓
2. Click "Discover Servers"
   → Vue component → window.electronAPI.discoverServers()
   → IPC to main → MDNSDiscovery.scan()
   → Returns [{name, host, port, url}]
   → Display in UI list
   ↓
3. User selects server or enters manually
   ↓
4. Click "Test Connection"
   → window.electronAPI.checkVersion(url)
   → Fetch ${url}/api/v1/settings
   → Check version match
   → Show success/error message
   ↓
5. Click "Connect"
   → connectionManager.save({url, nickname, timestamp})
   → Set as active connection
   → Redirect to home page
   → App reloads with new server URL
```

### WebSocket UUID Persistence

```
Web (current):
- UUID stored in sessionStorage
- Cleared on browser close
- New UUID on each session

Electron (new):
- UUID stored in electron-store (persistent)
- Preserved across app restarts
- Server recognizes returning client
- Enables session continuity
```

---

## Key Technical Details

### Platform Detection

```javascript
// client/src/js/platform/index.js
const isElectron = () => {
  return window.electronAPI !== undefined;
};

// Load appropriate implementation
if (isElectron()) {
  platformAPI = await import('./electron.js');
} else {
  platformAPI = await import('./browser.js');
}
```

### IPC Security

```javascript
// electron/preload.js
// ✅ Secure: Uses contextBridge
contextBridge.exposeInMainWorld('electronAPI', {
  getServerURL: () => ipcRenderer.invoke('get-server-url'),
  // ... only whitelisted methods exposed
});

// ❌ Insecure: Would be nodeIntegration: true (NEVER do this)
```

### Storage Abstraction

```javascript
// Web: Uses localStorage
getStorageAdapter() {
  return {
    getItem: (key) => localStorage.getItem(key),
    setItem: (key, val) => localStorage.setItem(key, val),
  };
}

// Electron: Uses electron-store via IPC
getStorageAdapter() {
  return {
    getItem: (key) => window.electronAPI.storageGet(key),
    setItem: (key, val) => window.electronAPI.storageSet(key, val),
  };
}
```

---

## Testing Strategy

### Unit Tests (Vitest)

**What to test**:
- Platform layer detection logic
- Browser platform implementation
- Electron platform implementation (with mocked IPC)
- Connection validation logic

**Example**:
```javascript
// Mock window.electronAPI
global.window.electronAPI = {
  getServerURL: vi.fn(() => 'http://test:8080'),
};

// Test platform detection
const platform = await import('@/js/platform');
expect(platform.baseURL()).toBe('http://test:8080');
```

### Integration Tests

**What to test**:
- ConnectionManager CRUD operations
- VersionChecker with mocked fetch
- MDNSDiscovery with mocked bonjour

### E2E Tests (Playwright/Spectron)

**What to test**:
- Full connection flow (add → test → connect → login)
- Connection switching
- WebSocket reconnection after restart
- Version mismatch blocking

### Manual Testing Checklist

**Platforms**:
- [ ] macOS (Intel)
- [ ] macOS (Apple Silicon)
- [ ] Windows 10/11
- [ ] Linux (Ubuntu/Debian)

**Scenarios**:
- [ ] First launch (no connections)
- [ ] Add connection manually
- [ ] Discover servers via mDNS
- [ ] Test connection with compatible server
- [ ] Test connection with incompatible server (version mismatch)
- [ ] Connect to server
- [ ] Login with credentials
- [ ] Use application (script navigation, cues, etc.)
- [ ] Switch to different server
- [ ] Close app and reopen (UUID persistence)
- [ ] Update app (auto-updater)

---

## Error Handling

### Connection Failures

**Scenario**: Server unreachable
**Handling**:
- Show error toast: "Cannot connect to server"
- Offer retry button
- Provide "Change Server" option

### Version Mismatch

**Scenario**: Client v0.23.0, Server v0.24.0
**Handling**:
- Block connection immediately
- Show error modal: "Version mismatch: Client 0.23.0, Server 0.24.0. Please update."
- Provide links to download latest version
- No "Connect Anyway" option (exact match required)

### WebSocket Disconnect

**Scenario**: Network interruption during use
**Handling**:
- Existing reconnect logic continues to work (unchanged)
- Show connection status in navbar (existing)
- Auto-reconnect when network available

### mDNS Unavailable

**Scenario**: Platform doesn't support mDNS
**Handling**:
- Gracefully disable discovery button
- Show message: "Service discovery not available on this platform"
- Manual entry always available as fallback

---

## Performance Considerations

### Bundle Size

**Web Build** (unchanged):
- ~2MB gzipped with manual chunking
- No Electron code included (tree-shaken)

**Electron Renderer** (same as web):
- ~2MB gzipped
- Platform layer adds negligible size (~2KB)

**Electron Distribution**:
- ~150MB base (Electron + Chromium)
- ~152MB total with app

### Startup Time

**Web** (unchanged): <1s
**Electron**:
- Cold start: ~2-3s (Electron overhead)
- Warm start: ~1s
- Acceptable for desktop app

### Memory Usage

**Web** (unchanged): ~100MB
**Electron**: ~300MB total
- ~150MB Electron/Chromium base
- ~150MB app + renderer

### Network

**mDNS Scan**:
- 5 second timeout
- Non-blocking (runs in background)
- Minimal bandwidth (multicast UDP)

---

## Security Considerations

### Context Isolation

✅ **Enabled** via preload script with contextBridge
- Renderer has no direct access to Node.js
- Only whitelisted IPC channels exposed
- Prevents XSS → RCE attacks

### Node Integration

❌ **Disabled** in renderer
- No `require()` in renderer
- No `fs`, `child_process` access
- Security best practice

### Credential Storage

✅ **OS-Level Encryption** via safeStorage
- macOS: Keychain
- Windows: DPAPI
- Linux: Secret Service (libsecret)
- Fallback: Base64 with warning (no plaintext)

### SSL Verification

⚠️ **Optional Toggle** for self-signed certs
- Default: SSL verification enabled
- Dev mode: Can disable for testing
- Warning shown when disabled

### Code Signing

**Required for Distribution**:
- macOS: Developer ID certificate (Gatekeeper)
- Windows: Code signing cert (SmartScreen)
- Linux: Not required (but recommended for repos)

---

## Backend Requirements

### Version Endpoint

**Current**: Version not exposed in API
**Required**: Add version to `/api/v1/settings` response

```python
# server/controllers/api/settings.py
@route('settings', api_version=ApiVersion.V1)
class SettingsController(BaseAPIController):
    async def get(self):
        from importlib.metadata import version
        pkg_version = version('digiscript')  # or from pyproject.toml

        self.write({
            'settings': self.application.digi_settings.get_all_settings(),
            'version': pkg_version,  # NEW
        })
```

### mDNS Service Advertisement (Optional)

**Current**: No mDNS advertisement
**Optional**: Advertise DigiScript service for discovery

```python
# server/digi_server/mdns_service.py (NEW FILE)
from zeroconf import ServiceInfo, Zeroconf
import socket

class MDNSService:
    def __init__(self, port, version):
        self.zeroconf = Zeroconf()
        hostname = socket.gethostname()

        self.info = ServiceInfo(
            "_digiscript._tcp.local.",
            f"DigiScript-{hostname}._digiscript._tcp.local.",
            addresses=[socket.inet_aton(self._get_local_ip())],
            port=port,
            properties={
                'version': version,
                'api': 'v1',
            },
        )

    def register(self):
        self.zeroconf.register_service(self.info)

    def unregister(self):
        self.zeroconf.unregister_service(self.info)
        self.zeroconf.close()
```

**Note**: Backend changes are separate scope. Electron app works without mDNS (manual entry fallback).

---

## CI/CD Configuration

### GitHub Actions Workflow

**File**: `.github/workflows/electron-build.yml`

**Triggers**:
- On release creation
- Manual workflow dispatch

**Jobs**:
- `build-mac`: Build DMG on macOS runner
- `build-win`: Build NSIS installer on Windows runner
- `build-linux`: Build DEB/AppImage on Ubuntu runner

**Artifacts**:
- Upload to GitHub Releases
- Signed with code signing certificates (stored in GitHub Secrets)

**Auto-Update**:
- electron-updater checks GitHub Releases API
- Downloads and installs updates automatically
- User notified via notification

---

## Migration Path

### Existing Web Users

**No changes required**:
- Web build process unchanged
- Web app behavior identical
- Electron code tree-shaken from web bundle
- Zero impact on existing deployments

### Electron Users (New)

**Initial Setup**:
1. Download installer (.dmg/.exe/.deb)
2. Install application
3. Launch app
4. Enter server URL or discover via mDNS
5. Login with credentials
6. Optionally save credentials for future

---

## Rollback Plan

If critical issues found:

1. **Branch Level**: Don't merge to `dev` until fully tested
2. **Feature Flag**: Could add runtime flag to disable Electron routes
3. **Build Separation**: Web and Electron are separate artifacts
4. **Code Isolation**: Platform layer can be removed cleanly

**Worst Case**: Delete electron/ directory, revert 4 modified files

---

## Success Criteria

### Functional Requirements

- [ ] Electron app launches on all 3 platforms
- [ ] Can connect to remote DigiScript servers
- [ ] Version check blocks incompatible servers
- [ ] Connection list persists across restarts
- [ ] mDNS discovery finds servers on network
- [ ] WebSocket UUID persists across restarts
- [ ] Login/logout works correctly
- [ ] All existing app features work in Electron
- [ ] Can switch servers mid-session
- [ ] Auto-updater notifies of new versions (optional)

### Non-Functional Requirements

- [ ] Web build still works identically (regression test passes)
- [ ] Hot-reload works in Electron dev mode
- [ ] Build process completes in <5 minutes
- [ ] Installer size <200MB
- [ ] Startup time <3 seconds
- [ ] No console errors in production build
- [ ] Code passes existing linters (ESLint, Ruff)

### Documentation Requirements

- [ ] README updated with Electron build instructions
- [ ] User guide for connection management
- [ ] Developer guide for platform layer
- [ ] CLAUDE.md updated with Electron architecture

---

## Resources

### Dependencies

**Electron App** (electron/package.json):
```json
{
  "dependencies": {
    "electron-store": "^8.1.0",
    "bonjour-service": "^1.2.1",
    "node-fetch": "^3.3.2"
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "@electron-forge/cli": "^7.2.0",
    "@electron-forge/maker-squirrel": "^7.2.0",
    "@electron-forge/maker-zip": "^7.2.0",
    "@electron-forge/maker-deb": "^7.2.0",
    "@electron-forge/maker-rpm": "^7.2.0"
  }
}
```

**Optional** (for auto-update):
```json
{
  "dependencies": {
    "electron-updater": "^6.3.9"
  }
}
```

### External Resources

- [Electron Documentation](https://www.electronjs.org/docs/latest/)
- [Electron Forge](https://www.electronforge.io/)
- [electron-store](https://github.com/sindresorhus/electron-store)
- [Electron safeStorage API](https://www.electronjs.org/docs/latest/api/safe-storage)
- [bonjour-service](https://github.com/cyberphone/bonjour-service)

---

## Contact & Support

**Primary Developer**: Tim (dreamteamprod)
**Repository**: https://github.com/dreamteamprod/DigiScript
**Issue**: #839
**Branch**: feature/electron-standalone-frontend

---

## Revision History

- **2025-01-12**: Initial plan created
- Architecture: Hybrid Build with Runtime Detection
- Estimated completion: 3-4 weeks (30 days)
- Total files: 19 (15 new, 4 modified)