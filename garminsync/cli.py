import typer
from .config import load_config

# Initialize environment variables
load_config()

app = typer.Typer()

@app.command(name="list")
def list_activities(
    all: bool = typer.Option(False, "--all", help="List all activities"),
    missing: bool = typer.Option(False, "--missing", help="List missing activities"),
    downloaded: bool = typer.Option(False, "--downloaded", help="List downloaded activities")
):
    """
    List activities based on specified filters
    """
    from tqdm import tqdm
    from .database import get_session, Activity
    from .garmin import GarminClient
    
    # Validate input
    if not any([all, missing, downloaded]):
        typer.echo("Error: Please specify at least one filter option (--all, --missing, --downloaded)")
        raise typer.Exit(code=1)
    
    client = GarminClient()
    session = get_session()
    
    # Sync database with latest activities
    typer.echo("Syncing activities from Garmin Connect...")
    from .database import sync_database
    sync_database(client)
    
    # Build query based on filters
    query = session.query(Activity)
    
    if all:
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

@app.command()
def download(
    missing: bool = typer.Option(False, "--missing", help="Download missing activities")
):
    """
    Download activities based on specified filters
    """
    from tqdm import tqdm
    from pathlib import Path
    from .database import get_session, Activity
    from .garmin import GarminClient
    
    # Validate input
    if not missing:
        typer.echo("Error: Currently only --missing downloads are supported")
        raise typer.Exit(code=1)
    
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

if __name__ == "__main__":
    app()
