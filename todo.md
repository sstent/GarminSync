# Activity Reprocessing Implementation

## Goal
Add capability to reprocess existing activities to calculate missing metrics like `avg_power`

## Requirements
- Reprocess all existing activities
- Add web UI button to trigger reprocessing
- Background processing for large jobs
- Progress tracking and status reporting

## Implementation Phases

### Phase 1: Database & Infrastructure
- [ ] Add `reprocessed` column to activities table
- [ ] Create migration script for new column
- [ ] Update activity parser to handle reprocessing
- [ ] Add CLI commands for reprocessing

### Phase 2: CLI & Backend
- [ ] Implement `garminsync reprocess` commands:
  - `--all`: Reprocess all activities
  - `--missing`: Reprocess activities missing metrics
  - `--activity-id`: Reprocess specific activity
- [ ] Add daemon support for reprocessing
- [ ] Create background job system

### Phase 3: Web UI Integration
- [ ] Add "Reprocess" button to activities page
- [ ] Create API endpoints:
  - POST /api/activities/reprocess
  - POST /api/activities/{id}/reprocess
- [ ] Implement progress indicators
- [ ] Add real-time status updates via websockets

### Phase 4: Testing & Optimization
- [ ] Write tests for reprocessing functionality
- [ ] Add pagination for large reprocessing jobs
- [ ] Implement caching for reprocessed activities
- [ ] Performance benchmarks

## Current Status
*Last updated: 2025-08-23*  
⏳ Planning phase - not yet implemented
