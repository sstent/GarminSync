package main

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"
	"github.com/sstent/garminsync/internal/config"
	"github.com/sstent/garminsync/internal/db"
	"github.com/sstent/garminsync/internal/garmin"
)

// listCmd represents the list command
var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List activities from Garmin Connect",
	Long: `List activities with various filters:
- All activities
- Missing activities (not yet downloaded)
- Downloaded activities`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// Get flag values
		listAll, _ := cmd.Flags().GetBool("all")
		listMissing, _ := cmd.Flags().GetBool("missing")
		listDownloaded, _ := cmd.Flags().GetBool("downloaded")

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
		db, err := db.NewDatabase(cfg.DatabasePath)
		if err != nil {
			return fmt.Errorf("failed to connect to database: %w", err)
		}
		defer db.Close()
		
		// Get activities from database with pagination
		page := 1
		pageSize := 20
		for {
			var filteredActivities []garmin.Activity
			var err error
			
			if listAll {
				filteredActivities, err = db.GetAllPaginated(page, pageSize)
			} else if listMissing {
				filteredActivities, err = db.GetMissingPaginated(page, pageSize)
			} else if listDownloaded {
				filteredActivities, err = db.GetDownloadedPaginated(page, pageSize)
			}
			
			if err != nil {
				return fmt.Errorf("failed to get activities: %w", err)
			}
			
			if len(filteredActivities) == 0 {
				break
			}
			
			// Print activities for current page
			for _, activity := range filteredActivities {
				fmt.Printf("Activity ID: %d, Start Time: %s, Filename: %s\n", 
					activity.ActivityId, activity.StartTime.Format("2006-01-02 15:04:05"), activity.Filename)
			}
			
			// Prompt to continue or quit
			fmt.Printf("\nPage %d - Show more? (y/n): ", page)
			var response string
			fmt.Scanln(&response)
			if strings.ToLower(response) != "y" {
				break
			}
			page++
		}
		
		return nil
	},
}

func init() {
	// Ensure rootCmd is properly initialized before adding subcommands
	if rootCmd == nil {
		panic("rootCmd must be initialized before adding subcommands")
	}

	listCmd.Flags().Bool("all", false, "List all activities")
	listCmd.Flags().Bool("missing", false, "List activities that have not been downloaded")
	listCmd.Flags().Bool("downloaded", false, "List activities that have been downloaded")
	
	listCmd.MarkFlagsMutuallyExclusive("all", "missing", "downloaded")
	listCmd.MarkFlagsRequiredAtLeastOne("all", "missing", "downloaded")

	rootCmd.AddCommand(listCmd)
}
