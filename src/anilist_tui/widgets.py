import html2text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Input, Label, Static, Tree, DataTable, Markdown, TabbedContent, TabPane, Button, Select
from textual.widgets._select import SelectOverlay
from textual.containers import Horizontal, VerticalScroll, Vertical
from textual.message import Message
from textual_image.widget import Image
from PIL import Image as PILImage

from .api import (
    update_anime_status,
    remove_anime_from_library as remove_anime_from_library_api,
    update_anime_progress,
    update_anime_rating,
    get_anime_details,
    get_library_status,
    get_library_progress,
    get_library_score,
)

import httpx
import io
import webbrowser


SelectOverlay.BINDINGS = [
    Binding("escape", "dismiss", "Dismiss menu"),
    Binding("j", "cursor_down", "Down", show=False),
    Binding("k", "cursor_up", "Up", show=False),
]


class VimDataTable(DataTable):
    """DataTable with vim-style row movement."""

    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
    ]


class AnimeDataTable(VimDataTable):
    """DataTable that rebuilds its columns to fit its own width on resize."""

    _anime_data: list[dict] = []

    def on_mount(self) -> None:
        self.cursor_type = "row"

    def on_resize(self) -> None:
        if self._anime_data:
            self._rebuild()

    def load(self, data: list[dict]) -> None:
        self._anime_data = data
        self._rebuild()

    def _rebuild(self) -> None:
        w = self.size.width - 1
        self.clear(columns=True)
        self.add_column("Title", width=int(w * 0.5))
        self.add_column("Episodes", width=int(w * 0.1))
        self.add_column("Status", width=int(w * 0.2))
        self.add_column("Score", width=int(w * 0.1))
        for anime in self._anime_data:
            title = anime["title"]["english"] or anime["title"]["romaji"]
            episodes = str(anime["episodes"]) if anime["episodes"] else "?"
            status = anime["status"].replace("_", " ").title()
            score = str(anime["averageScore"]) if anime.get("averageScore") else "?"
            self.add_row(title, episodes, status, score)


class SearchBar(Static):
    """Display a search bar for the user to input their query."""

    class SearchSubmitted(Message):
        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    def compose(self) -> ComposeResult:
        with Horizontal(id="search-bar-row"):
            yield Label("Search", id="search-label")
            yield SearchInput(placeholder="Search for anime...", id="search-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.post_message(self.SearchSubmitted(query))


class SearchInput(Input):
    """Input with visible focus-navigation bindings."""

    BINDINGS = [
        Binding("tab", "app.focus_next", "Next Focus", show=False),
    ]


class VimTree(Tree[str]):
    """Tree with vim-style cursor movement."""

    BINDINGS = [
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
    ]


class SideBar(Static):
    """Display a sidebar with navigation options."""

    def on_mount(self) -> None:
        self.border_title = "Navigation"
        self.query_one("#anime-tree", Tree).show_guides = False
        self.query_one("#user-tree", Tree).show_guides = False

    def compose(self) -> ComposeResult:
        animeTree: VimTree = VimTree("Anime", id="anime-tree")
        animeTree.root.expand()
        browse = animeTree.root.add("Browse")
        browse.add_leaf("Seasonal")
        browse.add_leaf("Trending")
        browse.add_leaf("Popular")
        browse.add_leaf("Top Rated")
        browse.expand()
        library = animeTree.root.add("Library")
        library.add_leaf("Watching")
        library.add_leaf("Planning")
        library.add_leaf("Completed")
        library.add_leaf("Dropped")
        library.add_leaf("Paused")
        library.add_leaf("Repeating")
        library.expand()

        userTree: VimTree = VimTree("User", id="user-tree")
        userTree.root.expand()
        userTree.root.add_leaf("Stats")
        userTree.root.add_leaf("Log Out")

        with VerticalScroll(id="sidebar-scroll-container", can_focus=False):
            yield animeTree
            yield userTree


class TabbedDetails(TabbedContent):
    BINDINGS = [
        ("h", "previous_details_tab", "Prev Tab"),
        ("l", "next_details_tab", "Next Tab"),
        ("a", "focus_library_select", "Library"),
        ("r", "focus_rating_select", "Rating"),
        ("v", "open_anilist", "View"),
        ("i", "increment_episode_binding", "Episode +"),
        ("plus", "increment_episode_binding", "Episode +"),
        ("d", "decrement_episode_binding", "Episode -"),
        ("minus", "decrement_episode_binding", "Episode -"),
    ]

    class AnimeSelected(Message):
        def __init__(self, anime: dict) -> None:
            super().__init__()
            self.anime = anime

    _pil_image: PILImage.Image | None = None
    _watched_episodes: int = 0
    _total_episodes: int = 0
    _current_anime_id: int | None = None
    _current_site_url: str | None = None
    _recs_data: list[dict] = []
    _library_statuses = ["Watching", "Planning", "Completed", "Dropped", "Paused", "Repeating"]
    _rating_score_to_value = {
        1: ":(",
        2: ":|",
        3: ":)",
    }
    _rating_value_to_score = {value: score for score, value in _rating_score_to_value.items()}
    _rating_values = list(_rating_value_to_score.keys())

    def _update_library_select(self, status_label: str | None) -> None:
        library_select = self.query_one("#library-status-select", Select)
        if status_label in self._library_statuses:
            library_select.value = status_label
        else:
            library_select.clear()

    def _update_rating_select(self, score: int | None) -> None:
        rating_select = self.query_one("#rating-select", Select)
        if isinstance(score, int) and score in self._rating_score_to_value:
            rating_select.value = self._rating_score_to_value[score]
        else:
            rating_select.clear()

    def on_mount(self) -> None:
        self.query_one("#recommendations-table", DataTable).cursor_type = "row"

    def action_previous_details_tab(self) -> None:
        tabs = self.query_one("#details-tabs", TabbedContent)
        tabs.active = "details-tab"

    def action_next_details_tab(self) -> None:
        tabs = self.query_one("#details-tabs", TabbedContent)
        tabs.active = "recommendations-tab"

    def _is_details_tab_active(self) -> bool:
        return self.query_one("#details-tabs", TabbedContent).active == "details-tab"

    def action_focus_library_select(self) -> None:
        if not self._is_details_tab_active():
            return
        library_select = self.query_one("#library-status-select", Select)
        library_select.focus()
        library_select.action_show_overlay()

    def action_focus_rating_select(self) -> None:
        if not self._is_details_tab_active():
            return
        rating_select = self.query_one("#rating-select", Select)
        rating_select.focus()
        rating_select.action_show_overlay()

    def action_open_anilist(self) -> None:
        if not self._is_details_tab_active():
            return
        self.query_one("#view-anilist-btn", Button).press()

    def action_increment_episode_binding(self) -> None:
        if not self._is_details_tab_active():
            return
        self.increment_episode()

    def action_decrement_episode_binding(self) -> None:
        if not self._is_details_tab_active():
            return
        self.decrement_episode()

    def on_key(self, event: events.Key) -> None:
        if not self._is_details_tab_active():
            return
        if event.key not in {"j", "k"}:
            return

        library_select = self.query_one("#library-status-select", Select)
        rating_select = self.query_one("#rating-select", Select)

        active_select: Select | None = None
        if library_select.expanded:
            active_select = library_select
        elif rating_select.expanded:
            active_select = rating_select

        if active_select is None:
            return

        overlay = active_select.query_one(SelectOverlay)
        if event.key == "j":
            overlay.action_cursor_down()
        else:
            overlay.action_cursor_up()
        event.stop()
        event.prevent_default()

    def compose(self) -> ComposeResult:
        with TabbedContent(id="details-tabs"):
            with TabPane("Details", id="details-tab"):
                with Horizontal(id="details-inner"):
                    yield Image(id="cover-image")
                    with Vertical(id="details-info"):
                        yield Label("", id="details-label")
                        with Horizontal(id="episode-counter"):
                            yield Button("-", id="ep-dec-btn")
                            yield Label("Ep ? / ?", id="ep-label")
                            yield Button("+", id="ep-inc-btn")
                        with Horizontal(id="details-buttons"):
                            yield Select.from_values(
                                self._library_statuses,
                                prompt="Add to Library",
                                id="library-status-select",
                                compact=True,
                                type_to_search=False,
                            )
                            yield Select.from_values(
                                self._rating_values,
                                prompt="Rate",
                                id="rating-select",
                                compact=True,
                                type_to_search=False,
                            )
                            yield Button("View on AniList", id="view-anilist-btn")
                        with VerticalScroll(id="description-container", can_focus=False):
                            yield Markdown("", id="description-markdown")
            with TabPane("Recommendations", id="recommendations-tab"):
                with VerticalScroll(id="recommendations-scroll", can_focus=False):
                    yield VimDataTable(id="recommendations-table")

    def on_resize(self) -> None:
        if self._pil_image is not None:
            self._resize_image()

    def _resize_image(self) -> None:
        max_w = max(1, int(self.size.width * 0.30))
        max_h = max(1, self.size.height - 3)
        iw, ih = self._pil_image.size
        cell_ratio = 0.5

        img_w = max_w
        img_h = int(img_w * ih * cell_ratio / iw)

        if img_h > max_h:
            img_h = max_h
            img_w = int(img_h * iw / (ih * cell_ratio))

        image_widget = self.query_one("#cover-image", Image)
        image_widget.styles.width = max(1, img_w)
        image_widget.styles.height = max(1, img_h)

    def on_tabbed_details_anime_selected(self, event: Message) -> None:
        self.run_worker(self._update_details(event.anime), exclusive=True)

    def _populate_recommendations(self, recs: list[dict]) -> None:
        self._recs_data = []
        table = self.query_one("#recommendations-table", DataTable)
        table.clear(columns=True)
        table.add_column("Title", width=40)
        table.add_column("Score", width=8)
        for rec in recs:
            media = rec.get("mediaRecommendation")
            if not media:
                continue
            title = media["title"].get("english") or media["title"].get("romaji") or "?"
            score = str(media.get("averageScore") or "?")
            table.add_row(title, score)
            self._recs_data.append(media)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "recommendations-table":
            event.stop()
            anime = self._recs_data[event.cursor_row]
            self.run_worker(self._load_rec_details(anime["id"]), exclusive=True)

    async def _load_rec_details(self, anime_id: int) -> None:
        try:
            full = await get_anime_details(anime_id)
            self.query_one("#details-tabs", TabbedContent).active = "details-tab"
            await self._update_details(full)
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    def _update_ep_label(self) -> None:
        total = str(self._total_episodes) if self._total_episodes else "?"
        self.query_one("#ep-label", Label).update(f"Ep {self._watched_episodes} / {total}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ep-inc-btn":
            self.increment_episode()
        elif event.button.id == "ep-dec-btn":
            self.decrement_episode()
        elif event.button.id == "view-anilist-btn":
            if self._current_site_url:
                webbrowser.open(self._current_site_url)
            else:
                self.app.notify("AniList link is unavailable for this anime.", severity="warning")

    def increment_episode(self) -> None:
        if self._current_anime_id is None:
            return
        if self._total_episodes != 0 and self._watched_episodes >= self._total_episodes:
            return
        self._watched_episodes += 1
        self._update_ep_label()
        self.run_worker(self._persist_episode_progress(), exclusive=False)

    def decrement_episode(self) -> None:
        if self._current_anime_id is None:
            return
        if self._watched_episodes <= 0:
            return
        self._watched_episodes -= 1
        self._update_ep_label()
        self.run_worker(self._persist_episode_progress(), exclusive=False)

    async def _persist_episode_progress(self) -> None:
        if self._current_anime_id is None:
            return
        try:
            await update_anime_progress(self._current_anime_id, self._watched_episodes)
        except Exception as e:
            self.app.notify(f"Error updating episode progress: {e}", severity="error")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "library-status-select":
            status = event.value

            if self._current_anime_id is None:
                return

            if isinstance(status, str):
                self.run_worker(self.update_anime_status(self._current_anime_id, status), exclusive=False)
            else:
                if event.select.has_focus:
                    self.run_worker(self.remove_anime_from_library(self._current_anime_id), exclusive=False)
        elif event.select.id == "rating-select":
            score = event.value

            if not isinstance(score, str):
                return

            mapped_score = self._rating_value_to_score.get(score)
            if self._current_anime_id is not None and mapped_score is not None:
                self.run_worker(self.update_anime_rating(self._current_anime_id, mapped_score), exclusive=False)

    async def update_anime_status(self, anime_id: int, status: str) -> None:
        try:
            await update_anime_status(anime_id, status)
            library_keys = ["Watching", "Planning", "Completed", "Dropped", "Paused", "Repeating"]
            for key in library_keys:
                self.app._cache.pop(key, None)
            current_tree = self.app.query_one("#anime-tree", Tree).cursor_node
            if current_tree and str(current_tree.label) in library_keys:
                self.app.on_tree_node_selected(Tree.NodeSelected(current_tree))
        except Exception as e:
            self.app.notify(f"Error updating library status: {e}", severity="error")

    async def remove_anime_from_library(self, anime_id: int) -> None:
        try:
            await remove_anime_from_library_api(anime_id)
            library_keys = ["Watching", "Planning", "Completed", "Dropped", "Paused", "Repeating"]
            for key in library_keys:
                self.app._cache.pop(key, None)
            current_tree = self.app.query_one("#anime-tree", Tree).cursor_node
            if current_tree and str(current_tree.label) in library_keys:
                self.app.on_tree_node_selected(Tree.NodeSelected(current_tree))
        except Exception as e:
            self.app.notify(f"Error removing anime from library: {e}", severity="error")

    async def update_anime_rating(self, anime_id: int, score: int) -> None:
        try:
            await update_anime_rating(anime_id, score)
        except Exception as e:
            self.app.notify(f"Error updating rating: {e}", severity="error")

    async def _update_details(self, anime: dict) -> None:
        try:
            details = (
                f"Title: {anime['title']['english'] or anime['title']['romaji']}\n"
                f"Genre: {', '.join(anime['genres']) if anime['genres'] else '?'}\n"
                f"Status: {anime['status'].replace('_', ' ').title()}\n"
                f"Score: {anime['averageScore'] or '?'}\n"
            )
            htmlDescription = anime.get("description") or "No description available."
            markdownDescription = html2text.html2text(htmlDescription)
            self.query_one("#cover-image", Image).display = True
            self.query_one("#details-label", Label).update(details)
            self.query_one("#description-markdown", Markdown).update(markdownDescription)
            self.query_one("#details-buttons").display = True
            self._update_library_select(None)
            self._update_rating_select(None)
            self._current_site_url = None
            self._total_episodes = anime.get("episodes") or 0
            self._watched_episodes = 0
            self._update_ep_label()
            self.query_one("#episode-counter").display = True

            anime_id = anime.get("id")
            self._current_anime_id = anime_id if isinstance(anime_id, int) else None
            site_url = anime.get("siteUrl")
            self._current_site_url = site_url if isinstance(site_url, str) and site_url else None
            if anime_id is not None:
                library_status = await get_library_status(anime_id)
                self._update_library_select(library_status)
                library_progress = await get_library_progress(anime_id)
                if library_progress is not None:
                    self._watched_episodes = library_progress
                    self._update_ep_label()
                library_score = await get_library_score(anime_id)
                self._update_rating_select(library_score)

            recs = (anime.get("recommendations") or {}).get("nodes") or []
            self._populate_recommendations(recs)

            cover_url = (anime.get("coverImage") or {}).get("large") or (anime.get("coverImage") or {}).get("medium")
            if cover_url:
                async with httpx.AsyncClient() as client:
                    response = await client.get(cover_url)
                pil_image = PILImage.open(io.BytesIO(response.content))
                self._pil_image = pil_image
                self.query_one("#cover-image", Image).image = pil_image
                self._resize_image()
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")
