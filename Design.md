# GarminSync Application Design

## Basic Info
**App Name:** GarminSync
**What it does:** CLI application that downloads FIT files for every activity in Garmin Connect

## Core Features
1. List activities (`garminsync list --all`)
2. List activities that have not been downloaded (`garminsync list --missing`)
3. List activities that have been downloaded (`garminsync list --downloaded`)
4. Download missing activities (`garminsync download --missing`)

## Tech Stack
**Frontend:** CLI (Go)
**Backend:** Go
**Database:** SQLite (garmin.db)
**Hosting:** Docker container
**Key Libraries:** garminexport (Go), viper (env vars), cobra (CLI framework), go-sqlite3

## Data Structure
**Main data object:**
```
Activity:
- activity_id: INTEGER (primary key, from Garmin)
- start_time: TEXT (ISO 8601 format)
- filename: TEXT (unique, e.g., activity_123_20240807.fit)
- downloaded: BOOLEAN (0 = pending, 1 = completed)
```

## User Flow
1. User launches container with credentials: `sudo docker run -it --env-file .env garminsync`
2. User is presented with CLI menu of options
3. User selects command (e.g., `garminsync download --missing`)
4. Application executes task with progress indicators
5. Application displays completion status and summary

## File Structure
```
/garminsync
├── main.go (CLI entrypoint and command implementations)
├── internal/
│   ├── config/
│   │   └── config.go (configuration loading)
│   ├── garmin/
│   │   ├── client.go (API integration)
│   │   └── activity.go (activity models)
│   └── db/
│       ├── database.go (embedded schema)
│       ├── sync.go (database synchronization)
│       └── migrations.go (versioned migrations)
├── Dockerfile
├── .env
└── README.md
```

## Technical Implementation Notes
- **Architecture:** Go-based implementation with Cobra CLI framework
- **Authentication:** Credentials via GARMIN_EMAIL/GARMIN_PASSWORD env vars (never stored)
- **File naming:** `activity_{id}_{timestamp}.fit` (e.g., activity_123456_20240807.fit)
- **Rate limiting:** 2-second delays between API requests
- **Database:** Embedded schema creation in Go code with versioned migrations
- **Database Sync:** Before any list/download operation, the application performs a synchronization between Garmin Connect and the local SQLite database to ensure activity records are up-to-date.
- **CLI Structure:** All CLI commands and flags are implemented in main.go using Cobra, without separate command files
- **Docker:** 
    - All commands require sudo as specified
    - Fully containerized build process (no host Go dependencies)
- **Session management:** Automatic cookie handling via garminexport with file-based persistence
- **Pagination:** Implemented for activity listing
- **Package stability:** Always use stable, released versions of packages to ensure reproducibility

## Development Phases
### Phase 1: Core Infrastructure - COMPLETE
- [x] Dockerfile creation
- [x] Environment variable handling (viper)
- [x] Cobra CLI framework setup
- [x] garminexport client initialization (with session persistence)

### Phase 2: Activity Listing - COMPLETE
- [x] SQLite schema implementation
- [x] Activity listing commands
- [x] Database synchronization
- [x] List command UI implementation

### Phase 3: Download Pipeline - COMPLETE
- [x] FIT file download implementation
- [x] Idempotent download logic (with exponential backoff)
- [x] Database update on success
- [x] Database sync integration

### Phase 4: Polish
- [x] Progress indicators (download command)
- [~] Error handling (partial implementation - retry logic exists but needs expansion)
- [ ] README documentation
- [x] Session timeout handling (via garminexport)

## Critical Roadblocks
1. **Rate limiting:** Built-in 2-second request delays (implemented)
2. **Session management:** Automatic cookie handling via garminexport (implemented)
3. **File conflicts:** Atomic database updates during downloads (implemented)
4. **Docker permissions:** Volume-mounted /data directory for downloads (implemented)
5. ~~**Database sync:** Efficient Garmin API ↔ local sync~~ (implemented)

## Current Status
**Working on:** Phase 4 - Final polish and error handling  
**Next steps:**  
1. Fix command flag parsing issue  
2. Implement comprehensive error handling  
3. Complete README documentation  
4. Final testing and validation  

**Known issues:** None

## Recent Fixes
- Fixed package declaration conflicts in cmd/ directory (changed from `package cmd` to `package main`)
- Removed unnecessary import in root.go that was causing build errors
- Verified Docker build process now completes successfully
