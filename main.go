package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/spf13/cobra"
	"github.com/sstent/garminsync/internal/config"
	"github.com/sstent/garminsync/internal/db"
	"github.com/sstent/garminsync/internal/garmin"
)

var rootCmd = &cobra.Command{
	Use:   "garminsync",
	Short: "GarminSync synchronizes Garmin Connect activities to FIT files",
	Long: `GarminSync is a CLI application that:
1. Authenticates with Garmin Connect
2. Lists activities (all, missing, downloaded)
3. Downloads missing FIT files  
4. Tracks download status in SQLite database`,
}

// List command flags
var listAll bool
var listMissing bool
var listDownloaded bool

// Download command flags
var downloadAll bool
var downloadMissing bool
var maxRetries int

var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List activities from Garmin Connect",
	Long: `List activities with various filters:
- All activities
- Missing activities (not yet downloaded)
- Downloaded activities`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// Initialize config
		cfg, err := config.LoadConfig()
		if err != nil {
			return fmt.Errorf("failed to load config: %w", err)
		}

		// Sync database with Garmin Connect
		fmt.Println("Syncing activities with Garmin Connect...")
		if err := db.SyncActivities(cfg); err != nil {
			return fmt.Errorf("database sync failed: %w", err)
		}
		
		// Initialize database
		database, err := db.NewDatabase(cfg.DatabasePath)
		if err != nil {
			return fmt.Errorf("failed to connect to database: %w", err)
		}
		defer database.Close()
		
		// Get activities from database with pagination
		page := 1
		pageSize := 20
		totalShown := 0
		
		for {
			var filteredActivities []garmin.Activity
			var err error
			
			if listAll {
				filteredActivities, err = database.GetAllPaginated(page, pageSize)
			} else if listMissing {
				filteredActivities, err = database.GetMissingPaginated(page, pageSize)
			} else if listDownloaded {
				filteredActivities, err = database.GetDownloadedPaginated(page, pageSize)
			}
			
			if err != nil {
				return fmt.Errorf("failed to get activities: %w", err)
			}
			
			if len(filteredActivities) == 0 {
				if totalShown == 0 {
					fmt.Println("No activities found matching the criteria")
				}
				break
			}
			
			// Print activities for current page
			for _, activity := range filteredActivities {
				status := "❌ Not Downloaded"
				if activity.Downloaded {
					status = "✅ Downloaded"
				}
				fmt.Printf("ID: %d | %s | %s | %s\n", 
					activity.ActivityId, 
					activity.StartTime.Format("2006-01-02 15:04:05"), 
					activity.Filename,
					status)
				totalShown++
			}
			
			// Only prompt if there might be more results
			if len(filteredActivities) == pageSize {
				fmt.Printf("\nPage %d (%d activities shown) - Show more? (y/n): ", page, totalShown)
				var response string
				fmt.Scanln(&response)
				if strings.ToLower(response) != "y" {
					break
				}
				page++
			} else {
				fmt.Printf("\nTotal: %d activities shown\n", totalShown)
				break
			}
		}
		
		return nil
	},
}

var downloadCmd = &cobra.Command{
	Use:   "download",
	Short: "Download missing FIT files",
	Long:  `Downloads missing activity files from Garmin Connect`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// Load configuration
		cfg, err := config.LoadConfig()
		if err != nil {
			return fmt.Errorf("failed to load config: %w", err)
		}

		// Sync database with Garmin Connect
		fmt.Println("Syncing activities with Garmin Connect...")
		if err := db.SyncActivities(cfg); err != nil {
			return fmt.Errorf("database sync failed: %w", err)
		}
		
		// Initialize Garmin client
		client, err := garmin.NewClient(cfg)
		if err != nil {
			return fmt.Errorf("failed to create Garmin client: %w", err)
		}
		
		// Initialize database
		database, err := db.NewDatabase(cfg.DatabasePath)
		if err != nil {
			return fmt.Errorf("failed to connect to database: %w", err)
		}
		defer database.Close()
		
		// Get activities to download
		var activities []garmin.Activity
		if downloadAll {
			activities, err = database.GetAll()
		} else if downloadMissing {
			activities, err = database.GetMissing()
		}
		if err != nil {
			return fmt.Errorf("failed to get activities: %w", err)
		}
		
		// Filter out already downloaded activities
		var toDownload []garmin.Activity
		for _, activity := range activities {
			if !activity.Downloaded {
				toDownload = append(toDownload, activity)
			}
		}
		
		total := len(toDownload)
		if total == 0 {
			fmt.Println("No activities to download")
			return nil
		}
		
		fmt.Printf("Found %d activities to download\n", total)
		
		// Ensure download directory exists
		downloadDir := "/data"
		if err := os.MkdirAll(downloadDir, 0755); err != nil {
			return fmt.Errorf("failed to create download directory: %w", err)
		}
		
		// Download activities with exponential backoff retry
		successCount := 0
		for i, activity := range toDownload {
			filename := filepath.Join(downloadDir, activity.Filename)
			fmt.Printf("[%d/%d] Downloading activity %d to %s\n", i+1, total, activity.ActivityId, filename)
			
			// Exponential backoff retry
			baseDelay := 2 * time.Second
			var lastErr error
			for attempt := 1; attempt <= maxRetries; attempt++ {
				err := client.DownloadActivityFIT(activity.ActivityId, filename)
				if err == nil {
					// Mark as downloaded in database
					if err := database.MarkDownloaded(activity.ActivityId, filename); err != nil {
						fmt.Printf("⚠️ Failed to mark activity %d as downloaded: %v\n", activity.ActivityId, err)
					} else {
						successCount++
						fmt.Printf("✅ Successfully downloaded activity %d\n", activity.ActivityId)
					}
					lastErr = nil
					break
				}
				
				lastErr = err
				fmt.Printf("⚠️ Attempt %d/%d failed: %v\n", attempt, maxRetries, err)
				if attempt < maxRetries {
					retryDelay := time.Duration(attempt) * baseDelay
					fmt.Printf("⏳ Retrying in %v...\n", retryDelay)
					time.Sleep(retryDelay)
				}
			}
			
			if lastErr != nil {
				fmt.Printf("❌ Failed to download activity %d after %d attempts: %v\n", activity.ActivityId, maxRetries, lastErr)
			}
		}
		
		fmt.Printf("\n📊 Download summary: %d/%d activities successfully downloaded\n", successCount, total)
		return nil
	},
}

func main() {
	Execute()
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func init() {
	// Configure list command flags
	listCmd.Flags().BoolVar(&listAll, "all", false, "List all activities")
	listCmd.Flags().BoolVar(&listMissing, "missing", false, "List activities that have not been downloaded")
	listCmd.Flags().BoolVar(&listDownloaded, "downloaded", false, "List activities that have been downloaded")
	listCmd.MarkFlagsMutuallyExclusive("all", "missing", "downloaded")
	listCmd.MarkFlagsRequiredAtLeastOne("all", "missing", "downloaded")

	// Configure download command flags
	downloadCmd.Flags().BoolVar(&downloadAll, "all", false, "Download all activities")
	downloadCmd.Flags().BoolVar(&downloadMissing, "missing", false, "Download only missing activities")
	downloadCmd.Flags().IntVar(&maxRetries, "max-retries", 3, "Maximum download retry attempts")
	downloadCmd.MarkFlagsMutuallyExclusive("all", "missing")
	downloadCmd.MarkFlagsRequiredAtLeastOne("all", "missing")

	// Add subcommands to root
	rootCmd.AddCommand(listCmd)
	rootCmd.AddCommand(downloadCmd)
}