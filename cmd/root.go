package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
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

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func main() {
	Execute()
}

func init() {
	// Initialize environment variables
	viper.SetEnvPrefix("GARMINSYNC")
	viper.BindEnv("email")
	viper.BindEnv("password")

	// Set default values
	viper.SetDefault("db_path", "garmin.db")
	viper.SetDefault("data_path", "/data")
	viper.SetDefault("rate_limit", 2)
}
