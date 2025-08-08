import os
import typer
from typing_extensions import Annotated
from .config import load_config

# Initialize environment variables
load_config()

app = typer.Typer(help="GarminSync - Download Garmin Connect activities", rich_markup_mode=None)

@app.command("list")
def list_activities(
    all_activities: Annotated[bool, typer.Option("--all", help="List all activities")] = False,
    missing: Annotated[bool, typer.Option("--missing", help="List missing activities")] = False,
    downloaded: Annotated[bool, typer.Option("--downloaded", help="List downloaded activities")] = False,
    offline: Annotated[bool, typer.Option("--offline", help="Work offline without syncing")] = False
):
    """List activities based on specified filters"""
    from tqdm import tqdm
    from .database import get_session, Activity, get_offline_stats, sync_database
    from .garmin import GarminClient
    
    # Validate input
    if not any([all_activities, missing, downloaded]):
        typer.echo("Error: Please specify at least one filter option (--all, --missing, --downloaded)")
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
            typer.echo(f"Working in offline mode - using cached data (last sync: {stats['last_sync']})")
        
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
            typer.echo(f"- ID: {activity.activity_id}, Start: {activity.start_time}, Status: {status}")
            
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)
    finally:
        if 'session' in locals():
            session.close()

@app.command("download")
def download(
    missing: Annotated[bool, typer.Option("--missing", help="Download missing activities")] = False
):
    """Download activities based on specified filters"""
    from tqdm import tqdm
    from pathlib import Path
    from .database import get_session, Activity
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
                typer.echo(f"Error downloading activity {activity.activity_id}: {str(e)}")
                session.rollback()
        
        typer.echo("Download completed successfully")
        
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)
    finally:
        if 'session' in locals():
            session.close()

@app.command("daemon")
def daemon_mode(
    start: Annotated[bool, typer.Option("--start", help="Start daemon")] = False,
    stop: Annotated[bool, typer.Option("--stop", help="Stop daemon")] = False,
    status: Annotated[bool, typer.Option("--status", help="Show daemon status")] = False,
    port: Annotated[int, typer.Option("--port", help="Web UI port")] = 8080
):
    """Daemon mode operations"""
    from .daemon import GarminSyncDaemon
    
    if start:
        daemon = GarminSyncDaemon()
        daemon.start(web_port=port)
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

def main():
    app()

if __name__ == "__main__":
    main()
