package config

import (
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// Config holds application configuration
type Config struct {
	GarminEmail    string
	GarminPassword string
	DatabasePath   string
	RateLimit      time.Duration
	SessionPath    string
}

// LoadConfig loads configuration from environment variables
func LoadConfig() (*Config, error) {
	email := os.Getenv("GARMIN_EMAIL")
	password := os.Getenv("GARMIN_PASSWORD")
	if email == "" || password == "" {
		return nil, fmt.Errorf("GARMIN_EMAIL and GARMIN_PASSWORD environment variables are required")
	}

	databasePath := os.Getenv("DATABASE_PATH")
	if databasePath == "" {
		databasePath = "garmin.db"
	}

	rateLimit := parseDuration(os.Getenv("RATE_LIMIT"), 2*time.Second)
	sessionPath := os.Getenv("SESSION_PATH")
	if sessionPath == "" {
		sessionPath = "/data/session.json"
	}

	// Ensure session path directory exists
	if err := os.MkdirAll(filepath.Dir(sessionPath), 0755); err != nil {
		return nil, fmt.Errorf("failed to create session directory: %w", err)
	}

	return &Config{
		GarminEmail:    email,
		GarminPassword: password,
		DatabasePath:   databasePath,
		RateLimit:      rateLimit,
		SessionPath:    sessionPath,
	}, nil
}

// parseDuration parses a duration string with a default
func parseDuration(value string, defaultValue time.Duration) time.Duration {
	if value == "" {
		return defaultValue
	}
	
	d, err := time.ParseDuration(value)
	if err != nil {
		return defaultValue
	}
	
	return d
}
