import click
from pathlib import Path

from config import load_config_folder_ids, load_cover_config
from pdf import generate_songbook
from filters import FilterParser


def make_cli_progress_callback():
    """Return a callback that displays progress updates to the console."""

    def _callback(percent: float, message: str = None):
        percentage = int(percent * 100)
        click.echo(f"[{percentage:3d}%] {message or ''}")

    return _callback


@click.command()
@click.option(
    "--source-folder",
    "-s",
    multiple=True,
    default=load_config_folder_ids(),
    help="Drive folder IDs to read files from (can be passed multiple times)",
)
@click.option(
    "--destination-path",
    "-d",
    required=True,
    help="Where to save the generated pdf",
)
@click.option(
    "--open-generated-pdf",
    is_flag=True,
    help="Open the generated pdf",
)
@click.option(
    "--cover-file-id",
    "-c",
    default=load_cover_config(),
    help="File ID of the cover",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=None,
    help="Limit the number of files to process (no limit by default)",
)
@click.option(
    "--filter",
    "-f",
    help="Filter files using property syntax. Examples: 'specialbooks:contains:regular', 'year:gte:2000', 'artist:equals:Beatles', 'difficulty:in:easy,medium'",
)
@click.option(
    "--preface-file-id",
    multiple=True,
    help="Google Drive file IDs for preface pages (after cover, before TOC). Can be specified multiple times.",
)
@click.option(
    "--postface-file-id",
    multiple=True,
    help="Google Drive file IDs for postface pages (at the very end). Can be specified multiple times.",
)
def cli(
    source_folder: str,
    destination_path: Path,
    open_generated_pdf,
    cover_file_id: str,
    limit: int,
    filter,
    preface_file_id,
    postface_file_id,
):
    client_filter = None
    if filter:
        try:
            client_filter = FilterParser.parse_simple_filter(filter)
            click.echo(f"Applying client-side filter: {filter}")
        except ValueError as e:
            click.echo(f"Error parsing filter: {e}")
            return

    # Convert tuples to lists
    preface_file_ids = list(preface_file_id) if preface_file_id else None
    postface_file_ids = list(postface_file_id) if postface_file_id else None

    if preface_file_ids:
        click.echo(f"Using {len(preface_file_ids)} preface file(s)")
    if postface_file_ids:
        click.echo(f"Using {len(postface_file_ids)} postface file(s)")

    progress_callback = make_cli_progress_callback()
    generate_songbook(
        source_folder,
        destination_path,
        limit,
        cover_file_id,
        client_filter,
        preface_file_ids,
        postface_file_ids,
        progress_callback,
    )
    if open_generated_pdf:
        click.echo(f"Opening generated songbook: {destination_path}")
        click.launch(destination_path)


cli()
