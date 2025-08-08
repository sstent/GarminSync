package garmin

import (
	"fmt"
	"os"
	"time"

	garminconnect "github.com/abrander/garmin-connect"
	"github.com/sstent/garminsync/internal/config"
)

// Client represents a Garmin Connect API client
type Client struct {
	client     *garminconnect.Client
	cfg        *config.Config
	lastAuth   time.Time
}

const (
	defaultSessionTimeout = 30 * time.Minute
)

// NewClient creates a new Garmin Connect client
func NewClient(cfg *config.Config) (*Client, error) {
	// Create client with session persistence
	client := garminconnect.New(garminconnect.WithCredentials(cfg.GarminEmail, cfg.GarminPassword))
	client.SessionFile = cfg.SessionPath

	// Attempt to load existing session
	if err := client.Login(); err != nil {
		// If session is invalid, try re-authenticating with retry
		maxAttempts := 2
		for attempt := 1; attempt <= maxAttempts; attempt++ {
			if err := client.Authenticate(); err != nil {
				if attempt == maxAttempts {
					return nil, fmt.Errorf("authentication failed after %d attempts: %w", maxAttempts, err)
				}
				continue
			}
			break
		}
	}

	return &Client{
		client: client,
		cfg:    cfg,
		lastAuth: time.Now(),
	}, nil
}

// checkSession checks if session is still valid, refreshes if expired
func (c *Client) checkSession() error {
	timeout := c.cfg.SessionTimeout
	if timeout == 0 {
		timeout = defaultSessionTimeout
	}

	if time.Since(c.lastAuth) > timeout {
		if err := c.client.Authenticate(); err != nil {
			return fmt.Errorf("session refresh failed: %w", err)
		}
		c.lastAuth = time.Now()
	}
	return nil
}

// GetActivities retrieves activities from Garmin Connect
func (c *Client) GetActivities() ([]Activity, error) {
	// Check and refresh session if needed
	if err := c.checkSession(); err != nil {
		return nil, err
	}
	// Get activities from Garmin Connect
	garminActivities, err := c.client.GetActivities(0, 100) // Pagination: start=0, limit=100
	if err != nil {
		return nil, fmt.Errorf("failed to get activities: %w", err)
	}

	// Convert to our Activity struct
	var activities []Activity
	for _, ga := range garminActivities {
		activities = append(activities, Activity{
			ActivityId: int(ga.ActivityID),
			StartTime:  time.Time(ga.StartTime),
			Filename:   fmt.Sprintf("activity_%d_%s.fit", ga.ActivityID, ga.StartTime.Format("20060102")),
			Downloaded: false,
		})
	}

	return activities, nil
}

// DownloadActivityFIT downloads a specific FIT file
func (c *Client) DownloadActivityFIT(activityId int, filename string) error {
	// Check and refresh session if needed
	if err := c.checkSession(); err != nil {
		return err
	}

	// Apply rate limiting
	time.Sleep(c.cfg.RateLimit)

	// Download FIT file
	fitData, err := c.client.DownloadActivity(activityId, garminconnect.FormatFIT)
	if err != nil {
		return fmt.Errorf("failed to download activity %d: %w", activityId, err)
	}

	// Save to file
	if err := os.WriteFile(filename, fitData, 0644); err != nil {
		return fmt.Errorf("failed to save FIT file %s: %w", filename, err)
	}

	return nil
}
