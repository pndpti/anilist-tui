from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Tree, DataTable

from .api import (
    get_anime_list,
    get_trending_anime,
    get_popular_anime,
    get_seasonal_anime,
    get_top_rated_anime,
    get_user_stats,
    search_anime,
)
from .auth import load_token, clear_token, save_username, get_username
from .config import DEFAULT_THEME, load_app_config
from .screens import AuthScreen, UserInfoScreen
from .widgets import SearchBar, SideBar, AnimeDataTable, TabbedDetails


class AnilistTUI(App):
    """A Textual User Interface for Anilist."""

    CSS_PATH = "app.css"
    COMMAND_PALETTE_BINDING = "ctrl+shift+p"
    _anime_data: list[dict] = []
    _cache: dict[str, list[dict]] = {}
    username = ""

    BINDINGS = [
        ("slash", "focus_search", "Search"),
        ("ctrl+n", "focus_next", "Next Focus"),
        ("ctrl+p", "focus_previous", "Prev Focus"),
    ]

    def action_focus_navigation(self) -> None:
        self.query_one("#anime-tree", Tree).focus()

    def action_focus_anime_list(self) -> None:
        self.query_one("#anime-table").focus()

    def action_focus_details(self) -> None:
        self.query_one("#details-tabs").focus()

    def action_focus_search(self) -> None:
        self.query_one("#search-input").focus()

    def action_increment_episode(self) -> None:
        self.query_one(TabbedDetails).increment_episode()

    def action_decrement_episode(self) -> None:
        self.query_one(TabbedDetails).decrement_episode()

    def compose(self) -> ComposeResult:
        with Container(id="main-container"):
            yield SearchBar()
            with Horizontal(id="middle-container"):
                yield SideBar()
                with Vertical(id="content-container"):
                    with VerticalScroll(id="content-scroll-container", can_focus=False):
                        yield AnimeDataTable(id="anime-table")
                    with VerticalScroll(id="details-scroll-container", can_focus=False):
                        yield TabbedDetails(id="details-tabs")
            yield Footer()

    def on_mount(self) -> None:
        app_config = load_app_config()
        try:
            self.theme = app_config.theme
        except Exception:
            self.theme = DEFAULT_THEME
        self.query_one("#content-scroll-container").border_title = "Anime"
        self.query_one("#details-scroll-container").border_title = "Details"
        token = load_token()
        if not token:
            self.push_screen(AuthScreen())
            return
        self.username = get_username() or ""
        if not self.username:
            self.run_worker(self._initialize_username(token), exclusive=False)

    async def _initialize_username(self, token: str) -> None:
        try:
            username = await save_username(token)
            if username:
                self.username = username
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        label = str(event.node.label)
        if label == "Trending":
            self.run_worker(self.load_anime("Trending", get_trending_anime), exclusive=True)
        elif label == "Seasonal":
            self.run_worker(self.load_anime("Seasonal", get_seasonal_anime), exclusive=True)
        elif label == "Popular":
            self.run_worker(self.load_anime("Popular", get_popular_anime), exclusive=True)
        elif label == "Top Rated":
            self.run_worker(self.load_anime("Top Rated", get_top_rated_anime), exclusive=True)
        elif label == "Watching":
            self.run_worker(self.load_anime("Watching", lambda: get_anime_list(self.username, "CURRENT")), exclusive=True)
        elif label == "Planning":
            self.run_worker(self.load_anime("Planning", lambda: get_anime_list(self.username, "PLANNING")), exclusive=True)
        elif label == "Completed":
            self.run_worker(self.load_anime("Completed", lambda: get_anime_list(self.username, "COMPLETED")), exclusive=True)
        elif label == "Dropped":
            self.run_worker(self.load_anime("Dropped", lambda: get_anime_list(self.username, "DROPPED")), exclusive=True)
        elif label == "Paused":
            self.run_worker(self.load_anime("Paused", lambda: get_anime_list(self.username, "PAUSED")), exclusive=True)
        elif label == "Repeating":
            self.run_worker(self.load_anime("Repeating", lambda: get_anime_list(self.username, "REPEATING")), exclusive=True)
        elif label == "Stats":
            self.run_worker(self.load_stats(), exclusive=True)
        elif label == "Log Out":
            self.logout()
        else:
            table = self.query_one("#anime-table", AnimeDataTable)
            table.clear(columns=True)
            self._anime_data = []

    def logout(self) -> None:
        clear_token()
        self.username = ""
        self._cache.clear()
        self._anime_data = []

        table = self.query_one("#anime-table", AnimeDataTable)
        table.clear(columns=True)

        self.push_screen(AuthScreen())

    async def load_stats(self) -> None:
        screen = UserInfoScreen("Stats")
        self.push_screen(screen)
        try:
            user = await get_user_stats()
            name = user.get("name") or self.username or "Unknown"
            site_url = user.get("siteUrl") or "N/A"
            avatar = user.get("avatar") or {}
            avatar_url = avatar.get("large") or avatar.get("medium")
            stats = user.get("statistics") or {}
            anime_stats = stats.get("anime") or {}
            manga_stats = stats.get("manga") or {}

            info_lines = [
                f"[bold magenta]{name}[/bold magenta]",
                "[bright_black]────────────────────────[/bright_black]",
                f"[cyan]AniList[/cyan]: [blue]{site_url}[/blue]",
                "",
                "[bold yellow]Anime Stats[/bold yellow]",
                f"[cyan]Entries[/cyan]: {anime_stats.get('count', 0)}",
                f"[cyan]Episodes[/cyan]: {anime_stats.get('episodesWatched', 0)}",
                f"[cyan]Minutes[/cyan]: {anime_stats.get('minutesWatched', 0)}",
                f"[cyan]Mean Score[/cyan]: {anime_stats.get('meanScore', 0)}",
                "",
                "[bold yellow]Manga Stats[/bold yellow]",
                f"[cyan]Entries[/cyan]: {manga_stats.get('count', 0)}",
                f"[cyan]Chapters[/cyan]: {manga_stats.get('chaptersRead', 0)}",
                f"[cyan]Volumes[/cyan]: {manga_stats.get('volumesRead', 0)}",
                f"[cyan]Mean Score[/cyan]: {manga_stats.get('meanScore', 0)}",
            ]
            screen.set_neofetch_content(info_lines, avatar_url if isinstance(avatar_url, str) else None)
        except Exception as e:
            screen.set_content(f"Error loading stats: {e}")

    def on_search_bar_search_submitted(self, event: SearchBar.SearchSubmitted) -> None:
        self.run_worker(self.load_search_results(event.query), exclusive=True)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "anime-table":
            return
        table = self.query_one("#anime-table", AnimeDataTable)
        if not table._anime_data:
            return
        anime = table._anime_data[table.cursor_row]
        self.query_one("#details-tabs", TabbedDetails).post_message(
            TabbedDetails.AnimeSelected(anime)
        )

    async def load_anime(self, key: str, fetcher) -> None:
        try:
            if key in self._cache:
                self._anime_data = self._cache[key]
            else:
                self._anime_data = await fetcher()
                self._cache[key] = self._anime_data
            table = self.query_one("#anime-table", AnimeDataTable)
            table.load(self._anime_data)
        except Exception as e:
            table = self.query_one("#anime-table", AnimeDataTable)
            table.clear(columns=True)
            table.add_column("Error")
            table.add_row(str(e))

    async def load_search_results(self, query: str) -> None:
        key = f"search:{query.lower()}"
        try:
            if key in self._cache:
                self._anime_data = self._cache[key]
            else:
                self._anime_data = await search_anime(query)
                self._cache[key] = self._anime_data
            table = self.query_one("#anime-table", AnimeDataTable)
            table.load(self._anime_data)
        except Exception as e:
            table = self.query_one("#anime-table", AnimeDataTable)
            table.clear(columns=True)
            table.add_column("Error")
            table.add_row(str(e))

    def on_resize(self) -> None:
        pass
