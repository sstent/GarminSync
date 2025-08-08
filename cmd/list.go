package main

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"
	"github.com/sstent/garminsync/internal/config"
	"github.com/sstent/garminsync/internal/db"
	"github.com/sstent/garminsync/internal/garmin"
)

// Global flag variables for list command
var listAll bool
var listMissing bool
var listDownloaded bool

// listCmd represents the list command
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
				if page == 1 {
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
			}
			
			// Only prompt if there might be more results
			if len(filteredActivities) == pageSize {
				fmt.Printf("\nPage %d - Show more? (y/n): ", page)
				var response string
				fmt.Scanln(&response)
				if strings.ToLower(response) != "y" {
					break
				}
				page++
			} else {
				break
			}
		}
		
		return nil
	},
}

func init() {
	// Bind flags to global variables
	listCmd.Flags().BoolVar(&listAll, "all", false, "List all activities")
	listCmd.Flags().BoolVar(&listMissing, "missing", false, "List activities that have not been downloaded")
	listCmd.Flags().BoolVar(&listDownloaded, "downloaded", false, "List activities that have been downloaded")
	
	listCmd.MarkFlagsMutuallyExclusive("all", "missing", "downloaded")
	listCmd.MarkFlagsRequiredAtLeastOne("all", "missing", "downloaded")

	rootCmd.AddCommand(listCmd)
}