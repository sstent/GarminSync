package db

import (
	"fmt"
	"time"

	"github.com/sstent/garminsync/internal/config"
	"github.com/sstent/garminsync/internal/garmin"
)

// SyncActivities synchronizes Garmin Connect activities with local database
func SyncActivities(cfg *config.Config) error {
	// Initialize Garmin client
	client, err := garmin.NewClient(cfg)
	if err != nil {
		return fmt.Errorf("failed to create Garmin client: %w", err)
	}

	// Initialize database
	db, err := NewDatabase(cfg.DatabasePath)
	if err != nil {
		return fmt.Errorf("failed to connect to database: %w", err)
	}
	defer db.Close()

	// Get activities from Garmin API
	garminActivities, err := client.GetActivities()
	if err != nil {
		return fmt.Errorf("failed to get Garmin activities: %w", err)
	}

	// Get all activities from local database
	localActivities, err := db.GetAll()
	if err != nil {
		return fmt.Errorf("failed to get local activities: %w", err)
	}

	// Create map for quick lookup of local activities
	localMap := make(map[int]garmin.Activity)
	for _, activity := range localActivities {
		localMap[activity.ActivityId] = activity
	}

	// Process each Garmin activity
	for _, ga := range garminActivities {
		localActivity, exists := localMap[ga.ActivityId]

		// New activity - insert into database
		if !exists {
			_, err := db.db.Exec(
				"INSERT INTO activities (activity_id, start_time, filename, downloaded) VALUES (?, ?, ?, ?)",
				ga.ActivityId,
				ga.StartTime.Format("2006-01-02 15:04:05"),
				ga.Filename,
				false,
			)
			if err != nil {
				return fmt.Errorf("failed to insert new activity %d: %w", ga.ActivityId, err)
			}
			continue
		}

		// Existing activity - check for metadata changes
		if localActivity.StartTime != ga.StartTime || localActivity.Filename != ga.Filename {
			_, err := db.db.Exec(
				"UPDATE activities SET start_time = ?, filename = ? WHERE activity_id = ?",
				ga.StartTime.Format("2006-01-02 15:04:05"),
				ga.Filename,
				ga.ActivityId,
			)
			if err != nil {
				return fmt.Errorf("failed to update activity %d: %w", ga.ActivityId, err)
			}
		}
	}

	return nil
}
