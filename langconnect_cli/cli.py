import asyncio
import csv
import glob
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from dotenv import load_dotenv

from .client import LangConnectClient
from .exceptions import LangConnectRequestError, MissingEnvironmentVariable

# Load environment variables from .env when the CLI starts.
load_dotenv()

app = typer.Typer(help="Interact with the LangConnect API from the command line.")

LOG_LEVELS = {
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
}


def _configure_logging(verbosity: int) -> None:
    level = LOG_LEVELS.get(min(verbosity, max(LOG_LEVELS.keys())), logging.DEBUG)
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def _run_async(coro):
    return asyncio.run(coro)


def _parse_key_value_pairs(pairs: Optional[List[str]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    if not pairs:
        return result
    for pair in pairs:
        if "=" not in pair:
            raise typer.BadParameter(f"Expected KEY=VALUE format, received '{pair}'.")
        key, value = pair.split("=", 1)
        result[key] = value
    return result


def _parse_json(json_payload: Optional[str]) -> Optional[Dict[str, Any]]:
    if not json_payload:
        return None
    try:
        return json.loads(json_payload)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON payload: {exc}") from exc


def _echo_response(response: Optional[Dict[str, Any]]) -> None:
    if response is None:
        typer.echo("No response received.")
        return
    typer.echo(json.dumps(response, indent=2, ensure_ascii=False))


@app.callback()
def main(
    ctx: typer.Context,
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase verbosity (repeatable)."),
) -> None:
    """CLI entrypoint configuring logging verbosity."""
    _configure_logging(verbose)
    ctx.obj = {"verbose": verbose}


@app.command()
def signin() -> None:
    """Authenticate with LangConnect using admin credentials."""
    try:
        client = LangConnectClient()
        success = _run_async(client.signin())
    except MissingEnvironmentVariable as exc:
        raise typer.Exit(code=1) from exc

    if success:
        typer.echo("Successfully authenticated with LangConnect.")
    else:
        typer.secho("Authentication failed. Check logs for details.", fg=typer.colors.RED)


@app.command()
def get(
    endpoint: str = typer.Argument(..., help="API endpoint, e.g. 'projects' or 'auth/me'."),
    params: Optional[List[str]] = typer.Option(None, "-p", "--param", help="Query parameters as KEY=VALUE."),
) -> None:
    """Perform a GET request against a LangConnect endpoint."""
    try:
        client = LangConnectClient()
        response = _run_async(client.get(endpoint, _parse_key_value_pairs(params)))
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc

    _echo_response(response)


@app.command()
def post(
    endpoint: str = typer.Argument(..., help="API endpoint, e.g. 'users'."),
    data: Optional[List[str]] = typer.Option(None, "-d", "--data", help="Form data as KEY=VALUE."),
    json_payload: Optional[str] = typer.Option(None, "-j", "--json", help="Raw JSON payload."),
) -> None:
    """Perform a POST request against a LangConnect endpoint."""
    if data and json_payload:
        raise typer.BadParameter("Use either --data or --json, not both.")

    try:
        client = LangConnectClient()
        payload = _parse_key_value_pairs(data)
        json_data = _parse_json(json_payload)
        response = _run_async(client.post(endpoint, data=payload or None, json_data=json_data))
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc

    _echo_response(response)


@app.command()
def delete(
    endpoint: str = typer.Argument(..., help="API endpoint, e.g. 'users/123'."),
    params: Optional[List[str]] = typer.Option(None, "-p", "--param", help="Query parameters as KEY=VALUE."),
) -> None:
    """Perform a DELETE request against a LangConnect endpoint."""
    try:
        client = LangConnectClient()
        response = _run_async(client.delete(endpoint, _parse_key_value_pairs(params)))
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc

    _echo_response(response)


@app.command("refresh-token")
def refresh_token() -> None:
    """Refresh the current access token using the stored refresh token."""
    try:
        client = LangConnectClient()
        signed_in = _run_async(client.signin())
        if not signed_in:
            typer.secho("Initial sign-in failed. Cannot refresh token.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        if _run_async(client.refresh_access_token()):
            typer.echo("Access token refreshed successfully.")
        else:
            typer.secho("Failed to refresh access token.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc


@app.command()
def signup(
    email: str = typer.Option(..., "--email", "-e", help="Email address for signup"),
    password: str = typer.Option(..., "--password", "-p", help="Password for signup", hide_input=True),
) -> None:
    """Sign up a new user."""
    try:
        client = LangConnectClient()
        response = _run_async(client.signup(email, password))
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc

    if response:
        typer.echo("Successfully signed up and authenticated.")
        _echo_response(response)
    else:
        typer.secho("Signup failed. Check logs for details.", fg=typer.colors.RED)


@app.command()
def signout() -> None:
    """Sign out the current user."""
    try:
        client = LangConnectClient()
        success = _run_async(client.signout())
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc

    if success:
        typer.echo("Successfully signed out.")
    else:
        typer.secho("Sign out failed. Check logs for details.", fg=typer.colors.RED)


@app.command()
def me() -> None:
    """Get current user information."""
    try:
        client = LangConnectClient()
        response = _run_async(client.get_current_user())
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc

    _echo_response(response)


@app.command()
def health() -> None:
    """Check API health status."""
    try:
        client = LangConnectClient()
        response = _run_async(client.health_check())
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc

    _echo_response(response)


@app.command("list-collections")
def list_collections() -> None:
    """List all collections."""
    try:
        client = LangConnectClient()
        response = _run_async(client.list_collections())
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc

    _echo_response(response)


@app.command("create-collection")
def create_collection(
    name: str = typer.Argument(..., help="Name of the collection to create"),
    metadata: Optional[str] = typer.Option(None, "--metadata", "-m", help="JSON metadata for the collection"),
) -> None:
    """Create a new collection."""
    try:
        client = LangConnectClient()
        metadata_dict = _parse_json(metadata) if metadata else None
        response = _run_async(client.create_collection(name, metadata_dict))
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc

    _echo_response(response)


@app.command("get-collection")
def get_collection(
    collection_id: str = typer.Argument(..., help="UUID of the collection to retrieve"),
) -> None:
    """Get details of a specific collection."""
    try:
        client = LangConnectClient()
        response = _run_async(client.get_collection(collection_id))
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc

    _echo_response(response)


@app.command("delete-collection")
def delete_collection(
    collection_id: str = typer.Argument(..., help="UUID of the collection to delete"),
) -> None:
    """Delete a collection."""
    try:
        client = LangConnectClient()
        success = _run_async(client.delete_collection(collection_id))
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc

    if success:
        typer.echo("Collection deleted successfully.")
    else:
        typer.secho("Failed to delete collection.", fg=typer.colors.RED)


@app.command("search-documents")
def search_documents(
    collection_id: str = typer.Argument(..., help="UUID of the collection to search in"),
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of results"),
    search_type: str = typer.Option("semantic", "--type", "-t", help="Search type: semantic, keyword, or hybrid"),
) -> None:
    """Search documents in a collection."""
    try:
        client = LangConnectClient()
        response = _run_async(client.search_documents(collection_id, query, limit, search_type))
    except (MissingEnvironmentVariable, LangConnectRequestError) as exc:
        raise typer.Exit(code=1) from exc

    _echo_response(response)


def _split_csv_to_documents(csv_file_path: str, output_dir: str) -> int:
    """
    Split a CSV file into individual documents.
    
    Args:
        csv_file_path: Path to the input CSV file
        output_dir: Directory to save individual documents
        
    Returns:
        Number of documents created
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        # Read the CSV file
        csv_reader = csv.reader(csvfile)
        
        # Get the header row
        header = next(csv_reader)
        
        # Process each data row
        for row_num, row in enumerate(csv_reader, start=1):
            # Create filename for this document
            filename = f"document_{row_num:05d}.txt"
            filepath = os.path.join(output_dir, filename)
            
            # Create document content with header and data row
            with open(filepath, 'w', encoding='utf-8') as doc_file:
                # Write header
                doc_file.write(','.join(header) + '\n')
                # Write data row
                doc_file.write(','.join(row) + '\n')
            
            # Print progress every 1000 documents
            if row_num % 1000 == 0:
                typer.echo(f"Processed {row_num} documents...")
    
    return row_num


@app.command()
def split(
    input_path: str = typer.Argument(..., help="Path to CSV file or folder containing CSV files"),
    output_dir: str = typer.Option("split_documents", "--output", "-o", help="Output directory for split documents"),
    pattern: str = typer.Option("*.csv", "--pattern", "-p", help="File pattern to match when input is a folder"),
) -> None:
    """Split CSV file(s) into individual documents.
    
    Each document will contain the header row and one data row.
    
    Examples:
        # Split a single CSV file
        langconnect-cli split data.csv
        
        # Split with custom output directory
        langconnect-cli split data.csv --output my_documents
        
        # Split all CSV files in a folder
        langconnect-cli split ./csv_files/
        
        # Split files matching a specific pattern
        langconnect-cli split ./data/ --pattern "*.csv"
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        typer.secho(f"Error: Input path '{input_path}' does not exist.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    csv_files = []
    
    if input_path.is_file():
        # Single file
        if input_path.suffix.lower() == '.csv':
            csv_files = [str(input_path)]
        else:
            typer.secho(f"Error: '{input_path}' is not a CSV file.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        # Folder - find CSV files
        search_pattern = str(input_path / pattern)
        csv_files = glob.glob(search_pattern)
        
        if not csv_files:
            typer.secho(f"Error: No CSV files found in '{input_path}' matching pattern '{pattern}'.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
    
    total_documents = 0
    
    for csv_file in csv_files:
        typer.echo(f"Splitting '{csv_file}'...")
        
        # Create subdirectory for each CSV file if processing multiple files
        if len(csv_files) > 1:
            file_name = Path(csv_file).stem
            file_output_dir = os.path.join(output_dir, file_name)
        else:
            file_output_dir = output_dir
        
        try:
            doc_count = _split_csv_to_documents(csv_file, file_output_dir)
            total_documents += doc_count
            typer.echo(f"✓ Created {doc_count} documents from '{csv_file}'")
        except Exception as e:
            typer.secho(f"✗ Error processing '{csv_file}': {e}", fg=typer.colors.RED)
            continue
    
    typer.echo(f"\n🎉 Successfully created {total_documents} documents in '{output_dir}'")
    typer.echo(f"📁 Output directory: {os.path.abspath(output_dir)}")


if __name__ == "__main__":
    app()
