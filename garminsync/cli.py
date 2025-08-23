import os

import typer
from typing_extensions import Annotated

from .config import load_config

# Initialize environment variables
load_config()

app = typer.Typer(
    help="GarminSync - Download Garmin Connect activities", rich_markup_mode=None
)


@app.command("list")
def list_activities(
    all_activities: Annotated[
        bool, typer.Option("--all", help="List all activities")
    ] = False,
    missing: Annotated[
        bool, typer.Option("--missing", help="List missing activities")
    ] = False,
    downloaded: Annotated[
        bool, typer.Option("--downloaded", help="List downloaded activities")
    ] = False,
    offline: Annotated[
        bool, typer.Option("--offline", help="Work offline without syncing")
    ] = False,
):
    """List activities based on specified filters"""
    from tqdm import tqdm

    from .database import (Activity, get_offline_stats, get_session,
                           sync_database)
    from .garmin import GarminClient

    # Validate input
    if not any([all_activities, missing, downloaded]):
        typer.echo(
            "Error: Please specify at least one filter option (--all, --missing, --downloaded)"
        )
        raise typer.Exit(code=1)

    try:
        client = GarminClient()
        session = get_session()

        if not offline:
            # Sync database with latest activities
            typer.echo("Syncing activities from Garmin Connect...")
            sync_database(client)
        else:
            # Show offline status with last sync info
            stats = get_offline_stats()
            typer.echo(
                f"Working in offline mode - using cached data (last sync: {stats['last_sync']})"
            )

        # Build query based on filters
        query = session.query(Activity)

        if all_activities:
            pass  # Return all activities
        elif missing:
            query = query.filter_by(downloaded=False)
        elif downloaded:
            query = query.filter_by(downloaded=True)

        # Execute query and display results
        activities = query.all()
        if not activities:
            typer.echo("No activities found matching your criteria")
            return

        # Display results with progress bar
        typer.echo(f"Found {len(activities)} activities:")
        for activity in tqdm(activities, desc="Listing activities"):
            status = "Downloaded" if activity.downloaded else "Missing"
            typer.echo(
                f"- ID: {activity.activity_id}, Start: {activity.start_time}, Status: {status}"
            )

    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)
    finally:
        if "session" in locals():
            session.close()


@app.command("download")
def download(
    missing: Annotated[
        bool, typer.Option("--missing", help="Download missing activities")
    ] = False,
):
    """Download activities based on specified filters"""
    from pathlib import Path

    from tqdm import tqdm

    from .database import Activity, get_session
    from .garmin import GarminClient

    # Validate input
    if not missing:
        typer.echo("Error: Currently only --missing downloads are supported")
        raise typer.Exit(code=1)

    try:
        client = GarminClient()
        session = get_session()

        # Sync database with latest activities
        typer.echo("Syncing activities from Garmin Connect...")
        from .database import sync_database

        sync_database(client)

        # Get missing activities
        activities = session.query(Activity).filter_by(downloaded=False).all()
        if not activities:
            typer.echo("No missing activities found")
            return

        # Create data directory if it doesn't exist
        data_dir = Path(os.getenv("DATA_DIR", "data"))
        data_dir.mkdir(parents=True, exist_ok=True)

        # Download activities with progress bar
        typer.echo(f"Downloading {len(activities)} missing activities...")
        for activity in tqdm(activities, desc="Downloading"):
            try:
                # Download FIT data
                fit_data = client.download_activity_fit(activity.activity_id)

                # Create filename-safe timestamp
                timestamp = activity.start_time.replace(":", "-").replace(" ", "_")
                filename = f"activity_{activity.activity_id}_{timestamp}.fit"
                filepath = data_dir / filename

                # Save file
                with open(filepath, "wb") as f:
                    f.write(fit_data)

                # Update database
                activity.filename = str(filepath)
                activity.downloaded = True
                session.commit()

            except Exception as e:
                typer.echo(
                    f"Error downloading activity {activity.activity_id}: {str(e)}"
                )
                session.rollback()

        typer.echo("Download completed successfully")

    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)
    finally:
        if "session" in locals():
            session.close()


@app.command("daemon")
def daemon_mode(
    start: Annotated[bool, typer.Option("--start", help="Start daemon")] = False,
    stop: Annotated[bool, typer.Option("--stop", help="Stop daemon")] = False,
    status: Annotated[
        bool, typer.Option("--status", help="Show daemon status")
    ] = False,
    port: Annotated[int, typer.Option("--port", help="Web UI port")] = 8080,
    run_migrations: Annotated[
        bool, 
        typer.Option(
            "--run-migrations/--skip-migrations", 
            help="Run database migrations on startup (default: run)"
        )
    ] = True,
):
    """Daemon mode operations"""
    from .daemon import GarminSyncDaemon

    if start:
        daemon = GarminSyncDaemon()
        daemon.start(web_port=port, run_migrations=run_migrations)
    elif stop:
        # Implementation for stopping daemon (PID file or signal)
        typer.echo("Stopping daemon...")
        # TODO: Implement stop (we can use a PID file to stop the daemon)
        typer.echo("Daemon stop not implemented yet")
    elif status:
        # Show current daemon status
        typer.echo("Daemon status not implemented yet")
    else:
        typer.echo("Please specify one of: --start, --stop, --status")


@app.command("migrate")
def migrate_activities():
    """Migrate database to add new activity fields"""
    from .migrate_activities import migrate_activities as run_migration

    typer.echo("Starting database migration...")
    success = run_migration()
    if success:
        typer.echo("Database migration completed successfully!")
    else:
        typer.echo("Database migration failed!")
        raise typer.Exit(code=1)

@app.command("analyze")
def analyze_activities(
    activity_id: Annotated[int, typer.Option("--activity-id", help="Activity ID to analyze")] = None,
    missing: Annotated[bool, typer.Option("--missing", help="Analyze all cycling activities missing analysis")] = False,
    cycling: Annotated[bool, typer.Option("--cycling", help="Run cycling-specific analysis")] = False,
):
    """Analyze activity data for cycling metrics"""
    from tqdm import tqdm
    from .database import Activity, get_session
    from .activity_parser import get_activity_metrics
    
    if not cycling:
        typer.echo("Error: Currently only cycling analysis is supported")
        raise typer.Exit(code=1)
    
    session = get_session()
    activities = []

    if activity_id:
        activity = session.query(Activity).get(activity_id)
        if not activity:
            typer.echo(f"Error: Activity with ID {activity_id} not found")
            raise typer.Exit(code=1)
        activities = [activity]
    elif missing:
        activities = session.query(Activity).filter(
            Activity.activity_type == 'cycling',
            Activity.analyzed == False  # Only unanalyzed activities
        ).all()
        if not activities:
            typer.echo("No unanalyzed cycling activities found")
            return
    else:
        typer.echo("Error: Please specify --activity-id or --missing")
        raise typer.Exit(code=1)

    typer.echo(f"Analyzing {len(activities)} cycling activities...")
    for activity in tqdm(activities, desc="Processing"):
        metrics = get_activity_metrics(activity)
        if metrics and "gearAnalysis" in metrics:
            # Update activity with analysis results
            activity.analyzed = True
            activity.gear_ratio = metrics["gearAnalysis"].get("gear_ratio")
            activity.gear_inches = metrics["gearAnalysis"].get("gear_inches")
            # Add other metrics as needed
            session.commit()

    typer.echo("Analysis completed successfully")

@app.command("reprocess")
def reprocess_activities(
    all: Annotated[bool, typer.Option("--all", help="Reprocess all activities")] = False,
    missing: Annotated[bool, typer.Option("--missing", help="Reprocess activities missing metrics")] = False,
    activity_id: Annotated[int, typer.Option("--activity-id", help="Reprocess specific activity by ID")] = None,
):
    """Reprocess activities to calculate missing metrics"""
    from tqdm import tqdm
    from .database import Activity, get_session
    from .activity_parser import get_activity_metrics

    session = get_session()
    activities = []
    
    if activity_id:
        activity = session.query(Activity).get(activity_id)
        if not activity:
            typer.echo(f"Error: Activity with ID {activity_id} not found")
            raise typer.Exit(code=1)
        activities = [activity]
    elif missing:
        activities = session.query(Activity).filter(
            Activity.reprocessed == False
        ).all()
        if not activities:
            typer.echo("No activities to reprocess")
            return
    elif all:
        activities = session.query(Activity).filter(
            Activity.downloaded == True
        ).all()
        if not activities:
            typer.echo("No downloaded activities found")
            return
    else:
        typer.echo("Error: Please specify one of: --all, --missing, --activity-id")
        raise typer.Exit(code=1)

    typer.echo(f"Reprocessing {len(activities)} activities...")
    for activity in tqdm(activities, desc="Reprocessing"):
        # Use force_reprocess=True to ensure we parse the file again
        metrics = get_activity_metrics(activity, force_reprocess=True)
        
        # Update activity metrics
        if metrics:
            activity.activity_type = metrics.get("activityType", {}).get("typeKey")
            activity.duration = int(float(metrics.get("duration", 0))) if metrics.get("duration") else activity.duration
            activity.distance = float(metrics.get("distance", 0)) if metrics.get("distance") else activity.distance
            activity.max_heart_rate = int(float(metrics.get("maxHR", 0))) if metrics.get("maxHR") else activity.max_heart_rate
            activity.avg_heart_rate = int(float(metrics.get("avgHR", 0))) if metrics.get("avgHR") else activity.avg_heart_rate
            activity.avg_power = float(metrics.get("avgPower", 0)) if metrics.get("avgPower") else activity.avg_power
            activity.calories = int(float(metrics.get("calories", 0))) if metrics.get("calories") else activity.calories
        
        # Mark as reprocessed
        activity.reprocessed = True
        session.commit()
    
    typer.echo("Reprocessing completed")

@app.command("report")
def generate_report(
    power_analysis: Annotated[bool, typer.Option("--power-analysis", help="Generate power metrics report")] = False,
    gear_analysis: Annotated[bool, typer.Option("--gear-analysis", help="Generate gear analysis report")] = False,
):
    """Generate performance reports for cycling activities"""
    from .database import Activity, get_session
    from .web import app as web_app
    
    if not any([power_analysis, gear_analysis]):
        typer.echo("Error: Please specify at least one report type")
        raise typer.Exit(code=1)
    
    session = get_session()
    activities = session.query(Activity).filter(
        Activity.activity_type == 'cycling',
        Activity.analyzed == True
    ).all()
    
    if not activities:
        typer.echo("No analyzed cycling activities found")
        return
    
    # Simple CLI report - real implementation would use web UI
    typer.echo("Cycling Analysis Report")
    typer.echo("=======================")
    
    for activity in activities:
        typer.echo(f"\nActivity ID: {activity.activity_id}")
        typer.echo(f"Date: {activity.start_time}")
        
        if power_analysis:
            typer.echo(f"- Average Power: {activity.avg_power}W")
            # Add other power metrics as needed
            
        if gear_analysis:
            typer.echo(f"- Gear Ratio: {activity.gear_ratio}")
            typer.echo(f"- Gear Inches: {activity.gear_inches}")
    
    typer.echo("\nFull reports available in the web UI at http://localhost:8080")

def main():
    app()


if __name__ == "__main__":
    main()
