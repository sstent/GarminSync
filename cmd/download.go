package main

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/spf13/cobra"
	"github.com/sstent/garminsync/internal/config"
	"github.com/sstent/garminsync/internal/db"
	"github.com/sstent/garminsync/internal/garmin"
)

// downloadCmd represents the download command
var downloadCmd = &cobra.Command{
	Use:   "download",
	Short: "Download missing FIT files",
	Long:  `Downloads missing activity files from Garmin Connect`,
}

var downloadAll bool
var downloadMissing bool
var maxRetries int

func init() {
	downloadCmd.Flags().BoolVar(&downloadAll, "all", false, "Download all activities")
	downloadCmd.Flags().BoolVar(&downloadMissing, "missing", false, "Download only missing activities")
	downloadCmd.Flags().IntVar(&maxRetries, "max-retries", 3, "Maximum download retry attempts (default: 3)")
	
	downloadCmd.MarkFlagsMutuallyExclusive("all", "missing")
	downloadCmd.MarkFlagsRequiredAtLeastOne("all", "missing")

	rootCmd.AddCommand(downloadCmd)

	downloadCmd.RunE = func(cmd *cobra.Command, args []string) error {
		// Load configuration
		cfg, err := config.LoadConfig()
		if err != nil {
			return fmt.Errorf("failed to load config: %w", err)
		}

		// Sync database with Garmin Connect
		if err := db.SyncActivities(cfg); err != nil {
			return fmt.Errorf("database sync failed: %w", err)
		}
		
		// Initialize Garmin client
		client, err := garmin.NewClient(cfg)
		if err != nil {
			return fmt.Errorf("failed to create Garmin client: %w", err)
		}
		
		// Initialize database
		db, err := db.NewDatabase(cfg.DatabasePath)
		if err != nil {
			return fmt.Errorf("failed to connect to database: %w", err)
		}
		defer db.Close()
		
		// Get activities to download
		var activities []garmin.Activity
		if downloadAll {
			activities, err = db.GetAll()
		} else if downloadMissing {
			activities, err = db.GetMissing()
		}
		if err != nil {
			return fmt.Errorf("failed to get activities: %w", err)
		}
		
		total := len(activities)
		if total == 0 {
			fmt.Println("No activities to download")
			return nil
		}
		
		// Ensure download directory exists
		dataDir := filepath.Dir(cfg.SessionPath)
		if err := os.MkdirAll(dataDir, 0755); err != nil {
			return fmt.Errorf("failed to create data directory: %w", err)
		}
		
		// Download activities with exponential backoff retry
		successCount := 0
		for i, activity := range activities {
			if activity.Downloaded {
				continue
			}
			
			filename := filepath.Join(dataDir, activity.Filename)
			fmt.Printf("[%d/%d] Downloading activity %d to %s\n", i+1, total, activity.ActivityId, filename)
			
			// Exponential backoff retry
			baseDelay := 2 * time.Second
			for attempt := 1; attempt <= maxRetries; attempt++ {
				err := client.DownloadActivityFIT(activity.ActivityId, filename)
				if err == nil {
					// Mark as downloaded in database
					if err := db.MarkDownloaded(activity.ActivityId, filename); err != nil {
						fmt.Printf("⚠️ Failed to mark activity %d as downloaded: %v\n", activity.ActivityId, err)
					} else {
						successCount++
						fmt.Printf("✅ Successfully downloaded activity %d\n", activity.ActivityId)
					}
					break
				}
				
				fmt.Printf("⚠️ Attempt %d/%d failed: %v\n", attempt, maxRetries, err)
				if attempt < maxRetries {
					retryDelay := time.Duration(attempt) * baseDelay
					fmt.Printf("⏳ Retrying in %v...\n", retryDelay)
					time.Sleep(retryDelay)
				} else {
					fmt.Printf("❌ Failed to download activity %d after %d attempts\n", activity.ActivityId, maxRetries)
				}
			}
		}
		
		fmt.Printf("\n📊 Download summary: %d/%d activities successfully downloaded\n", successCount, total)
		return nil
	}
}
