# DigiScript - Claude Code Context

## Project Overview

DigiScript is a digital script management system for cueing theatrical shows. It provides a web-based platform for managing scripts, cues, cast, characters, and live show execution with real-time websocket communication between clients and server.

**Branching Strategy**: Feature branch → dev → main

**Development Branch**: `dev` 

**Main Branch**: `main`

## Architecture

### Client (Frontend)
- **Technology**: Vue.js 2.7.14 with Vue Router 3.6.5 and Vuex 3.6.2
- **UI Framework**: Bootstrap 4.6.2 + BootstrapVue 2.23.1
- **Build Tool**: Vite 4.5.5
- **Location**: `/client/`
- **Port**: Served through server at port 8080

### Server (Backend)  
- **Technology**: Python 3.13.x with Tornado web framework 6.5.2
- **Database**: SQLite with SQLAlchemy ORM and Alembic migrations
- **Authentication**: JWT with bcrypt password hashing
- **Real-time**: WebSocket communication
- **Location**: `/server/`
- **Port**: 8080

### Infrastructure
- **Containerization**: Docker with docker-compose
- **Monitoring**: Prometheus + Grafana + cAdvisor + Node Exporter
- **Monitoring Ports**: Grafana (3000), Prometheus (9090), cAdvisor (8090), Node Exporter (9100)

## Key Technologies & Frameworks

### Frontend Dependencies
- **Core**: Vue.js, Vue Router, Vuex, Bootstrap Vue
- **Forms**: Vuelidate (validation), Vue Multiselect
- **WebSocket**: vue-native-websocket
- **UI**: vue-toast-notification, contrast-color
- **State**: vuex-persistedstate
- **Utils**: lodash, deep-object-diff, loglevel

### Backend Dependencies
- **Web**: tornado, tornado-sqlalchemy
- **Database**: alembic (migrations), marshmallow-sqlalchemy (serialization)
- **Auth**: bcrypt, pyjwt[crypto]
- **Utils**: anytree, python-dateutil
- **Monitoring**: tornado-prometheus

## Project Structure

### Client Structure (`/client/`)
```
src/
├── App.vue              # Root component
├── main.js              # App entry point with WebSocket setup
├── router/              # Vue Router configuration
├── store/               # Vuex store modules
│   ├── modules/         # Feature-specific store modules
│   │   ├── script.js    # Script management
│   │   ├── show.js      # Show management
│   │   ├── user/        # User management
│   │   └── websocket.js # WebSocket state
├── views/               # Page-level Vue components
│   ├── show/           # Show management pages
│   ├── config/         # Configuration pages
│   └── user/           # User management pages
└── vue_components/     # Reusable Vue components
    ├── show/           # Show-related components
    ├── config/         # Configuration components
    └── user/           # User-related components
```

### Server Structure (`/server/`)
```
├── main.py                    # Application entry point
├── digi_server/              # Core server application
├── controllers/              # HTTP/WebSocket request handlers
│   ├── api/                  # REST API controllers
│   │   ├── show/            # Show management endpoints
│   │   └── user/            # User management endpoints
├── models/                   # SQLAlchemy database models
├── schemas/                  # Marshmallow serialization schemas
├── rbac/                     # Role-based access control
├── utils/                    # Utility modules
├── registry/                 # Application registries and locks
├── alembic_config/          # Database migration configuration
└── test/                    # Test files
```

## Git Workflow

### Branching Strategy
- **Feature development**: Create feature branches from `dev` branch
- **Integration**: Feature branches merge into `dev` branch 
- **Release**: `dev` branch merges into `main` branch for releases

### Merge Strategy
- **Feature → dev**: Squash merging is acceptable to keep dev history clean
- **dev → main**: Use merge commits to preserve history and maintain traceability
- **History preservation**: History between `dev` and `main` should be resolvable at all times

### Commit Guidelines
- **Commit size**: Prefer smaller, focused commits rather than single large commits
- **Purpose**: Makes reviewing change history easier and enables better debugging
- **Message format**: Follow conventional commit format where applicable

## Development Workflow

### Commands
**Client:**
- `npm ci` - Install dependencies
- `npm run build` - Build for production
- `npm run lint` - ESLint with auto-fix
- `npm run ci-lint` - ESLint check only

**Server:**
- `pip install -r requirements.txt` - Install dependencies
- `pip install -r test_requirements.txt` - Install test dependencies
- `pytest` - Run tests
- `black .` - Format code
- `isort . --profile=black` - Sort imports
- `pylint <files>` - Lint code

**Development Setup:**
- `./hooks/setup-hooks.sh` - Setup git hooks for pre-commit linting
- `./scripts/start-compose.sh` - Start full Docker environment
- `./scripts/stop-compose.sh` - Stop Docker environment

### Testing
- **Python**: pytest with pytest-asyncio for async tests
- **JavaScript**: ESLint for code quality (no unit test framework detected)

## Key Features

### Show Management
- **Acts & Scenes**: Hierarchical show structure
- **Cast & Characters**: Actor assignments and character management
- **Scripts**: Line-by-line script editing with revisions
- **Cues**: Technical cue management tied to script lines
- **Microphones**: Mic allocation and management

### Live Show Execution
- **Sessions**: Live show session management
- **Real-time Updates**: WebSocket communication for script following across multiple connected clients
- **Script Following**: Real-time script following during performances

### User Management
- **Authentication**: JWT-based login system
- **RBAC**: Role-based access control for different permission levels
- **User Settings**: Personalized user preferences and overrides

## WebSocket Communication

### Message Format (Server → Client)
```json
{
  "OP": "OPERATION_CODE",
  "DATA": {},
  "ACTION": "VUEX_ACTION_NAME"
}
```

### Message Handling
- All messages trigger Vuex mutation `SOCKET_ONMESSAGE`
- Messages with `ACTION` also trigger corresponding Vuex action
- WebSocket reconnection is automatic

## Database

### Technology
- **Database**: SQLite with SQLAlchemy ORM
- **Migrations**: Alembic for schema versioning
- **Location**: `/server/conf/digiscript.sqlite` (dev), Docker volume (prod)

## Deployment

### Docker Production
- Uses multi-stage Docker build
- Includes full monitoring stack (Prometheus, Grafana, cAdvisor, Node Exporter)  
- SQLite database persisted in Docker volume
- Application accessible on port 8080

### Configuration
- Server settings in `/server/conf/digiscript.json`
- Docker environment variables for deployment settings
- Grafana provisioned dashboards and datasources

## Documentation

### User Documentation
- `/docs/` - GitHub Pages documentation
- Comprehensive guides for show setup, script configuration, cue management
- Getting started guide with screenshots

### Developer Documentation  
- `/documentation/development.md` - Development setup and WebSocket messaging
- `/documentation/deployment.md` - Deployment instructions
- Inline code documentation (minimal, following project conventions)

## Development Standards

### Code Style
- **Python**: Black formatting, isort imports, pylint compliance
- **JavaScript**: ESLint with Airbnb config, Vue.js best practices
- **Git**: Conventional commits

### Requirements
- **Node**: v22.x (npm 10.x) 
- **Python**: 3.13.x
- **Development**: pyenv + nvm recommended for version management

## Claude Development Guidelines

### Workflow Principles
**Reflective Planning**: After receiving tool results, carefully reflect on their quality and determine optimal next steps before proceeding. Use thinking to plan and iterate based on new information.

**Parallel Operations**: For maximum efficiency, invoke all relevant tools simultaneously rather than sequentially when performing multiple independent operations.

**Agent Utilization**: Use custom agents whenever possible when breaking down work into tasks. Consider whether a single feature can be delivered by multiple agents best suited for particular areas of the codebase.

**Cleanup**: If you create any temporary files, scripts, or helper files for iteration, clean up by removing them at the end of the task.

### Solution Quality
**General Purpose Solutions**: Write high-quality, general-purpose solutions that work correctly for all valid inputs, not just test cases. Do not hard-code values or create solutions that only work for specific scenarios.

**Principled Implementation**: Focus on understanding problem requirements and implementing correct algorithms. Tests verify correctness but don't define the solution. Provide robust, maintainable, and extendable implementations following best practices.

**Problem Assessment**: If a task is unreasonable, infeasible, or if tests are incorrect, communicate this clearly.

### Planning & Documentation  
**Plan First**: Always make a plan for approaching problems before writing code. Use GitHub issues as a workspace for documenting plans before execution. If no relevant issue exists, create one and use it as the planning workspace.

### Technical Guidelines
- Always run appropriate linting commands after making changes
- Use existing patterns and conventions found in the codebase
- WebSocket message handling follows specific patterns - refer to `main.js` 
- Database changes require Alembic migrations
- No unit test framework for frontend - focus on ESLint for quality
- Follow the existing Vue.js 2.x patterns (not Vue 3)