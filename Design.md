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
**Frontend:** Python CLI (argparse)
**Backend:** Python 3.10+ with garminexport==1.2.0
**Database:** SQLite (garmin.db)
**Hosting:** Docker container
**Key Libraries:** garminexport, python-dotenv, sqlite3

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
1. User launches container with credentials: `docker run -it --env-file .env garminsync`
2. User is presented with CLI menu of options
3. User selects command (e.g., `garminsync download --missing`)
4. Application executes task with progress indicators
5. Application displays completion status and summary

## File Structure
```
GarminSync/
├── Dockerfile
├── .env.example
├── requirements.txt
└── main.py
```

## Technical Implementation Notes
- **Single-file architecture:** All logic in main.py (CLI, DB, Garmin integration)
- **Authentication:** Credentials via GARMIN_EMAIL/GARMIN_PASSWORD env vars (never stored)
- **File naming:** `activity_{id}_{timestamp}.fit` (e.g., activity_123456_20240807.fit)
- **Rate limiting:** 2-second delays between API requests
- **Database:** In-memory during auth testing, persistent garmin.db for production
- **Docker** All docker commands require the use of sudo

## Development Phases
### Phase 1: Core Infrastructure
- [X] Dockerfile with Python 3.10 base
- [X] Environment variable handling
- [X] garminexport client initialization

### Phase 2: Activity Listing
- [ ] SQLite schema implementation
- [ ] Activity listing commands
- [ ] Database synchronization

### Phase 3: Download Pipeline
- [ ] FIT file download implementation
- [ ] Idempotent download logic
- [ ] Database update on success

### Phase 4: Polish
- [ ] Progress indicators
- [ ] Error handling
- [ ] README documentation

## Critical Roadblocks
1. **Garmin API changes:** garminexport is abandoned, switch to garmin-connect-export instead
2. **Rate limiting:** Built-in 2-second request delays
3. **Session management:** Automatic cookie handling via garminexport
4. **File conflicts:** Atomic database updates during downloads
5. **Docker permissions:** Volume-mounted /data directory for downloads

## Current Status
**Working on:** Phase 1 - Core Infrastructure (Docker setup, env vars)
**Next steps:** Implement activity listing with SQLite schema
**Known issues:** Garmin API rate limits (mitigated by 2s delays), session timeout handling
