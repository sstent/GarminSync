package garmin

import "time"

// Activity represents a Garmin Connect activity
type Activity struct {
	ActivityId  int       `db:"activity_id"`
	StartTime   time.Time `db:"start_time"`
	Filename    string    `db:"filename"`
	Downloaded  bool      `db:"downloaded"`
}

// ActivityRepository provides methods for activity persistence
type ActivityRepository interface {
	GetAll() ([]Activity, error)
	GetMissing() ([]Activity, error)
	GetDownloaded() ([]Activity, error)
	MarkDownloaded(activityId int, filename string) error
}
