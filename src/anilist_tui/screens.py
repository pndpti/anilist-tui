from textual.app import ComposeResult, Screen
from textual.widgets import Input, Label, Markdown, Button, Link, Static
from textual.containers import Center, Vertical, Horizontal, VerticalScroll
from textual_image.widget import Image
from PIL import Image as PILImage

from .auth import get_oauth_url, save_token, save_username, load_client_id, save_client_id

import httpx
import io


class AuthScreen(Screen):
    """Full-screen OAuth setup shown when no token is saved."""

    _missing_client_id_text = "Enter your Client ID to generate the authorization link"

    def _current_client_id(self) -> str:
        entered_client_id = self.query_one("#auth-client-id-input", Input).value.strip()
        if entered_client_id:
            return entered_client_id
        return load_client_id() or ""

    def _update_auth_link(self) -> None:
        client_id = self._current_client_id()
        auth_link = self.query_one("#auth-url-label", Link)
        if not client_id:
            auth_link.update(self._missing_client_id_text)
            auth_link.url = ""
            return

        url = get_oauth_url(client_id)
        auth_link.update(url)
        auth_link.url = url

    def compose(self) -> ComposeResult:
        initial_client_id = load_client_id() or ""
        initial_url = get_oauth_url(initial_client_id) if initial_client_id else ""
        initial_link_label = initial_url or self._missing_client_id_text
        with Center(id="auth-outer"):
            with Vertical(id="auth-box"):
                yield Label("AniList Authentication", id="auth-title")
                yield Label("Step 1: Enter your AniList client ID", classes="auth-step")
                yield Input(placeholder="Client ID", value=initial_client_id, id="auth-client-id-input")
                yield Label("Step 2: Open the link below and authorise the app", classes="auth-step")
                yield Link(initial_link_label, url=initial_url, id="auth-url-label")
                yield Label("Step 3: Copy the access token from the URL after authorising", classes="auth-step")
                yield Label("Step 4: Paste the access token here", classes="auth-step")
                yield Input(placeholder="Access token", password=True, id="auth-token-input")
                yield Button("Save & Continue", id="auth-submit-btn")
                yield Label("", id="auth-error")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "auth-client-id-input":
            self._update_auth_link()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "auth-submit-btn":
            client_id = self.query_one("#auth-client-id-input", Input).value.strip()
            token = self.query_one("#auth-token-input", Input).value.strip()
            error = self.query_one("#auth-error", Label)
            if not client_id:
                error.update("Client ID is required.")
                return
            if not token:
                error.update("Access token is required.")
                return
            save_client_id(client_id)
            save_token(token)
            username = await save_username(token)
            if not username:
                error.update("Could not fetch AniList username. Check the token and try again.")
                return
            if hasattr(self.app, "username"):
                self.app.username = username
            self.app.pop_screen()


class UserInfoScreen(Screen):
    """Dedicated screen for user profile and stats."""

    BINDINGS = [("q", "app.pop_screen", "Back")]

    _pil_image: PILImage.Image | None = None
    _stats_line_count: int = 0

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title

    def compose(self) -> ComposeResult:
        with Center(id="user-info-outer"):
            with Vertical(id="user-info-box"):
                with Horizontal(id="user-info-content"):
                    with Center(id="user-info-image-center"):
                        yield Image(id="user-info-image")
                    with VerticalScroll(id="user-info-scroll"):
                        yield Markdown("Loading...", id="user-info-markdown")
                        yield Static("", id="user-info-stats")
                yield Label("q Back", id="user-info-footer")

    def on_mount(self) -> None:
        self.query_one("#user-info-image", Image).display = False
        self.query_one("#user-info-stats", Static).display = False

    def on_resize(self) -> None:
        if self._pil_image is not None and self.query_one("#user-info-image", Image).display:
            self._scale_avatar_to_stats()

    def set_content(self, markdown_content: str, avatar_url: str | None = None) -> None:
        self._stats_line_count = 0
        self.query_one("#user-info-markdown", Markdown).display = True
        self.query_one("#user-info-stats", Static).display = False
        self.query_one("#user-info-markdown", Markdown).update(markdown_content)
        if avatar_url:
            self.run_worker(self._load_avatar(avatar_url), exclusive=True)
        else:
            self.query_one("#user-info-image", Image).display = False

    def set_neofetch_content(self, info_lines: list[str], avatar_url: str | None = None) -> None:
        self._stats_line_count = len(info_lines)
        stats_widget = self.query_one("#user-info-stats", Static)
        self.query_one("#user-info-markdown", Markdown).display = False
        stats_widget.display = True
        stats_widget.update("\n".join(info_lines))
        if avatar_url:
            self.run_worker(self._load_avatar(avatar_url), exclusive=True)
        else:
            self.query_one("#user-info-image", Image).display = False

    async def _load_avatar(self, avatar_url: str) -> None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(avatar_url)
                response.raise_for_status()
            self._pil_image = PILImage.open(io.BytesIO(response.content))
            image_widget = self.query_one("#user-info-image", Image)
            image_widget.image = self._pil_image
            image_widget.display = True
            self._scale_avatar_to_stats()
        except Exception:
            self.query_one("#user-info-image", Image).display = False

    def _scale_avatar_to_stats(self) -> None:
        if self._pil_image is None:
            return
        stats_height = self.query_one("#user-info-scroll", VerticalScroll).size.height
        available_h = max(1, stats_height - 2) if stats_height > 0 else 0
        desired_h = max(1, self._stats_line_count) if self._stats_line_count > 0 else 10
        image_h = min(desired_h, available_h) if available_h > 0 else desired_h

        iw, ih = self._pil_image.size
        cell_ratio = 0.5

        image_w = max(1, int(image_h * iw / (ih * cell_ratio)))

        image_widget = self.query_one("#user-info-image", Image)
        image_widget.styles.height = image_h
        image_widget.styles.width = image_w

        center_widget = self.query_one("#user-info-image-center", Center)
        center_widget.styles.width = image_w + 2
