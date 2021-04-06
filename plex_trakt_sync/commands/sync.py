import click

from plex_trakt_sync.requests_cache import requests_cache
from plex_trakt_sync.plex_server import get_plex_server
from plex_trakt_sync.config import CONFIG
from plex_trakt_sync.decorators import measure_time
from plex_trakt_sync.main import process_movie_section, process_show_section
from plex_trakt_sync.plex_api import PlexApi
from plex_trakt_sync.trakt_api import TraktApi
from plex_trakt_sync.trakt_list_util import TraktListUtil
from plex_trakt_sync.logging import logging


def sync_all(movies=True, tv=True):
    with requests_cache.disabled():
        server = get_plex_server()
    listutil = TraktListUtil()
    plex = PlexApi(server)
    trakt = TraktApi()

    with measure_time("Loaded Trakt lists"):
        trakt_watched_movies = trakt.watched_movies
        trakt_watched_shows = trakt.watched_shows
        trakt_movie_collection = trakt.movie_collection_set
        trakt_ratings = trakt.ratings
        trakt_watchlist_movies = trakt.watchlist_movies
        trakt_liked_lists = trakt.liked_lists

    if trakt_watchlist_movies:
        listutil.addList(None, "Trakt Watchlist", traktid_list=trakt_watchlist_movies)

    for lst in trakt_liked_lists:
        listutil.addList(lst['username'], lst['listname'])

    with requests_cache.disabled():
        logging.info("Server version {} updated at: {}".format(server.version, server.updatedAt))
        logging.info("Recently added: {}".format(server.library.recentlyAdded()[:5]))

    if movies:
        for section in plex.movie_sections:
            with measure_time("Processing section %s" % section.title):
                process_movie_section(section, trakt_watched_movies, listutil, trakt_movie_collection, trakt, plex)

    if tv:
        for section in plex.show_sections:
            with measure_time("Processing section %s" % section.title):
                process_show_section(section, trakt_watched_shows, listutil)

    with measure_time("Updated plex watchlist"):
        listutil.updatePlexLists(server)


@click.command()
@click.option(
    "--sync", "sync_option",
    type=click.Choice(["all", "movies", "tv"], case_sensitive=False),
    default="all",
    show_default=True, help="Specify what to sync"
)
def sync(sync_option: str):
    """
    Perform sync between Plex and Trakt
    """

    movies = sync_option in ["all", "movies"]
    tv = sync_option in ["all", "tv"]
    if not movies and not tv:
        click.echo("Nothing to sync!")
        return

    logging.info(f"Syncing with Plex {CONFIG['PLEX_USERNAME']} and Trakt {CONFIG['PLEX_USERNAME']}")
    logging.info(f"Syncing TV={tv}, Movies={movies}")

    with measure_time("Completed full sync"):
        sync_all(movies=movies, tv=tv)
