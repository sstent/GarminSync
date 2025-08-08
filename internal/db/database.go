package db

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	"github.com/mattn/go-sqlite3"
	"github.com/sstent/garminsync/internal/garmin"
)

// SQLiteDatabase implements ActivityRepository using SQLite
type SQLiteDatabase struct {
	db *sql.DB
}

// NewDatabase creates a new SQLite database connection
func NewDatabase(path string) (*SQLiteDatabase, error) {
	db, err := sql.Open("sqlite3", path)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	// Create table if it doesn't exist
	if err := createSchema(db); err != nil {
		return nil, fmt.Errorf("failed to create schema: %w", err)
	}

	return &SQLiteDatabase{db: db}, nil
}

// Close closes the database connection
func (d *SQLiteDatabase) Close() error {
	return d.db.Close()
}

// createSchema creates the database schema
func createSchema(db *sql.DB) error {
	schema := `
	CREATE TABLE IF NOT EXISTS activities (
		activity_id INTEGER PRIMARY KEY,
		start_time TEXT NOT NULL,
		filename TEXT NOT NULL,
		downloaded BOOLEAN NOT NULL DEFAULT 0
	);
	
	CREATE INDEX IF NOT EXISTS idx_activity_id ON activities(activity_id);
	CREATE INDEX IF NOT EXISTS idx_downloaded ON activities(downloaded);
	`

	if _, err := db.Exec(schema); err != nil {
		return fmt.Errorf("failed to create schema: %w", err)
	}

	return nil
}

// GetAll returns all activities from the database
func (d *SQLiteDatabase) GetAll() ([]garmin.Activity, error) {
	return d.GetAllPaginated(0, 0) // 0,0 means no pagination
}

// GetMissing returns activities that haven't been downloaded yet
func (d *SQLiteDatabase) GetMissing() ([]garmin.Activity, error) {
	return d.GetMissingPaginated(0, 0)
}

// GetDownloaded returns activities that have been downloaded
func (d *SQLiteDatabase) GetDownloaded() ([]garmin.Activity, error) {
	return d.GetDownloadedPaginated(0, 0)
}

// GetAllPaginated returns a paginated list of all activities
func (d *SQLiteDatabase) GetAllPaginated(page, pageSize int) ([]garmin.Activity, error) {
	offset := (page - 1) * pageSize
	query := "SELECT activity_id, start_time, filename, downloaded FROM activities"
	if pageSize > 0 {
		query += fmt.Sprintf(" LIMIT %d OFFSET %d", pageSize, offset)
	}
	rows, err := d.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to get all activities: %w", err)
	}
	defer rows.Close()

	return scanActivities(rows)
}

// GetMissingPaginated returns a paginated list of missing activities
func (d *SQLiteDatabase) GetMissingPaginated(page, pageSize int) ([]garmin.Activity, error) {
	offset := (page - 1) * pageSize
	query := "SELECT activity_id, start_time, filename, downloaded FROM activities WHERE downloaded = 0"
	if pageSize > 0 {
		query += fmt.Sprintf(" LIMIT %d OFFSET %d", pageSize, offset)
	}
	rows, err := d.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to get missing activities: %w", err)
	}
	defer rows.Close()

	return scanActivities(rows)
}

// GetDownloadedPaginated returns a paginated list of downloaded activities
func (d *SQLiteDatabase) GetDownloadedPaginated(page, pageSize int) ([]garmin.Activity, error) {
	offset := (page - 1) * pageSize
	query := "SELECT activity_id, start_time, filename, downloaded FROM activities WHERE downloaded = 1"
	if pageSize > 0 {
		query += fmt.Sprintf(" LIMIT %d OFFSET %d", pageSize, offset)
	}
	rows, err := d.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to get downloaded activities: %w", err)
	}
	defer rows.Close()

	return scanActivities(rows)
}

// MarkDownloaded updates the database when an activity is downloaded
func (d *SQLiteDatabase) MarkDownloaded(activityId int, filename string) error {
	_, err := d.db.Exec("UPDATE activities SET downloaded = 1, filename = ? WHERE activity_id = ?",
		filename, activityId)
	if err != nil {
		return fmt.Errorf("failed to mark activity as downloaded: %w", err)
	}

	return nil
}

// scanActivities converts database rows to Activity objects
func scanActivities(rows *sql.Rows) ([]garmin.Activity, error) {
	var activities []garmin.Activity

	for rows.Next() {
		var activity garmin.Activity
		var downloaded int
		var startTime string

		if err := rows.Scan(&activity.ActivityId, &startTime, &activity.Filename, &downloaded); err != nil {
			return nil, fmt.Errorf("failed to scan activity: %w", err)
		}

		// Convert SQLite time string to time.Time
		activity.StartTime, _ = time.Parse("2006-01-02 15:04:05", startTime)
		activity.Downloaded = downloaded == 1
		activities = append(activities, activity)
	}

	return activities, nil
}
