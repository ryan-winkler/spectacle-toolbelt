"""Full-page webpage capture through a Chromium DevTools backend."""

from __future__ import annotations

import asyncio
import base64
import json
import math
import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from spectacle_toolbelt.desktop.dialogs import DialogError, KdeDialog
from spectacle_toolbelt.output.editor_handoff import EditorHandoffError, open_in_spectacle

SAFE_URL_SCHEMES = {"http", "https", "file"}
DEFAULT_MAX_PIXELS = 180_000_000


class WebCaptureError(RuntimeError):
    """Raised when full-page web capture cannot complete."""


Backend = Callable[..., None]


@dataclass(frozen=True)
class FullPageCaptureRequest:
    url: str | None = None
    output: Path | None = None
    width: int = 1365
    timeout_seconds: float = 30.0
    max_pixels: int = DEFAULT_MAX_PIXELS
    overwrite: bool = False
    copy_to_clipboard: bool = True
    open_in_spectacle: bool = True
    resolve_active_tab: bool = True
    prompt_for_url: bool = True


@dataclass(frozen=True)
class FullPageCaptureOutcome:
    status: str
    output_path: Path
    url: str
    copied_to_clipboard: bool
    opened_in_spectacle: bool = False


@dataclass(frozen=True)
class ActiveBrowserTab:
    url: str
    websocket_url: str


def capture_fullpage_web(
    request: FullPageCaptureRequest,
    *,
    backend: Backend | None = None,
) -> FullPageCaptureOutcome:
    output = request.output
    if output is None:
        from spectacle_toolbelt.output.files import timestamped_output_path

        output = timestamped_output_path(prefix="Full Page Web Capture")
    if output.exists() and not request.overwrite:
        raise WebCaptureError(f"output already exists: {output} (use --force to overwrite)")

    url = request.url
    active_tab: ActiveBrowserTab | None = None
    if not url and request.resolve_active_tab:
        active_tab = resolve_active_browser_tab()
        if active_tab is not None:
            url = active_tab.url
    if not url and request.prompt_for_url:
        try:
            url = KdeDialog().prompt_url()
        except DialogError as exc:
            raise WebCaptureError(str(exc)) from exc
    if not url:
        raise WebCaptureError("no URL supplied and active-tab resolution failed")
    _validate_url(url)

    output.parent.mkdir(parents=True, exist_ok=True)
    if backend is not None:
        backend(
            url,
            output,
            width=request.width,
            timeout_seconds=request.timeout_seconds,
            max_pixels=request.max_pixels,
        )
    elif active_tab is not None:
        capture_existing_chromium_tab(
            active_tab.websocket_url,
            output,
            width=request.width,
            timeout_seconds=request.timeout_seconds,
            max_pixels=request.max_pixels,
        )
    else:
        capture_with_chromium(
            url,
            output,
            width=request.width,
            timeout_seconds=request.timeout_seconds,
            max_pixels=request.max_pixels,
        )
    if not output.exists():
        raise WebCaptureError(f"browser backend did not create {output}")

    copied = False
    if request.copy_to_clipboard:
        copied = copy_png_to_clipboard(output)

    opened = False
    if request.open_in_spectacle:
        try:
            open_in_spectacle(output)
            opened = True
        except EditorHandoffError as exc:
            raise WebCaptureError(f"captured {output}, but Spectacle editor handoff failed: {exc}") from exc

    return FullPageCaptureOutcome(
        status="complete",
        output_path=output,
        url=url,
        copied_to_clipboard=copied,
        opened_in_spectacle=opened,
    )


def resolve_active_browser_url() -> str | None:
    tab = resolve_active_browser_tab()
    return tab.url if tab else None


def resolve_active_browser_tab() -> ActiveBrowserTab | None:
    """Resolve the active Chromium-family tab when DevTools metadata is exposed."""

    active_title = _active_window_title()
    for port in (9222, 9223, 9224):
        try:
            tabs = _http_json(f"http://127.0.0.1:{port}/json/list", timeout=0.2)
        except WebCaptureError:
            continue
        if not isinstance(tabs, list):
            continue
        page_tabs = [
            tab
            for tab in tabs
            if isinstance(tab, dict)
            and tab.get("type") == "page"
            and isinstance(tab.get("url"), str)
            and isinstance(tab.get("webSocketDebuggerUrl"), str)
            and _is_safe_url(tab["url"])
        ]
        if active_title:
            matching_tabs = [
                tab
                for tab in page_tabs
                if _browser_window_title_matches(active_title, str(tab.get("title") or ""))
            ]
            if len(matching_tabs) == 1:
                return ActiveBrowserTab(
                    url=str(matching_tabs[0]["url"]),
                    websocket_url=str(matching_tabs[0]["webSocketDebuggerUrl"]),
                )
        if not active_title and len(page_tabs) == 1:
            return ActiveBrowserTab(
                url=str(page_tabs[0]["url"]),
                websocket_url=str(page_tabs[0]["webSocketDebuggerUrl"]),
            )
    return None


def _browser_window_title_matches(active_window_title: str, tab_title: str) -> bool:
    active = _normalize_browser_window_title(active_window_title)
    tab = _normalize_title(tab_title)
    return bool(active and tab and active == tab)


def _normalize_browser_window_title(title: str) -> str:
    normalized = _normalize_title(title)
    for suffix in (
        " - Google Chrome",
        " - Chromium",
        " - Brave",
        " - Microsoft Edge",
        " - Vivaldi",
    ):
        if normalized.endswith(suffix):
            return _normalize_title(normalized[: -len(suffix)])
    return normalized


def _normalize_title(title: str) -> str:
    return " ".join(title.split())


def capture_existing_chromium_tab(
    websocket_url: str,
    output: Path,
    *,
    width: int | None = None,
    timeout_seconds: float = 30.0,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> None:
    if width is not None and width < 320:
        raise WebCaptureError("width must be at least 320")
    png_bytes = asyncio.run(
        _capture_page_png(
            websocket_url,
            url=None,
            width=width,
            timeout_seconds=timeout_seconds,
            max_pixels=max_pixels,
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(png_bytes)


def capture_with_chromium(
    url: str,
    output: Path,
    *,
    width: int = 1365,
    timeout_seconds: float = 30.0,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> None:
    _validate_url(url)
    if width < 320:
        raise WebCaptureError("width must be at least 320")
    if timeout_seconds <= 0:
        raise WebCaptureError("timeout must be positive")
    browser = _find_browser()
    port = _free_port()

    with tempfile.TemporaryDirectory(
        prefix="spectacle-toolbelt-browser-",
        ignore_cleanup_errors=True,
    ) as user_data_dir:
        process = subprocess.Popen(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--no-first-run",
                "--no-default-browser-check",
                f"--remote-debugging-port={port}",
                f"--user-data-dir={user_data_dir}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _wait_for_devtools(port, timeout_seconds=timeout_seconds)
            target = _open_devtools_target(port)
            websocket_url = target.get("webSocketDebuggerUrl")
            if not isinstance(websocket_url, str):
                raise WebCaptureError("browser did not expose a page debugger")
            png_bytes = asyncio.run(
                _capture_page_png(
                    websocket_url,
                    url,
                    width=width,
                    timeout_seconds=timeout_seconds,
                    max_pixels=max_pixels,
                )
            )
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(png_bytes)
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


def copy_png_to_clipboard(path: Path) -> bool:
    wl_copy = shutil.which("wl-copy")
    if wl_copy:
        with path.open("rb") as file:
            return subprocess.run(
                [wl_copy, "--type", "image/png"],
                stdin=file,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            ).returncode == 0

    xclip = shutil.which("xclip")
    if xclip:
        with path.open("rb") as file:
            return subprocess.run(
                [xclip, "-selection", "clipboard", "-t", "image/png", "-i"],
                stdin=file,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            ).returncode == 0

    xsel = shutil.which("xsel")
    if xsel:
        with path.open("rb") as file:
            return subprocess.run(
                [xsel, "--clipboard", "--input"],
                stdin=file,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            ).returncode == 0

    return False


async def _capture_page_png(
    websocket_url: str,
    url: str | None,
    *,
    width: int | None,
    timeout_seconds: float,
    max_pixels: int,
) -> bytes:
    import websockets

    async with websockets.connect(websocket_url, open_timeout=timeout_seconds) as websocket:
        client = _CdpClient(websocket)
        await client.call("Page.enable")
        await client.call("Runtime.enable")
        emulation_applied = False
        try:
            if width is not None:
                viewport_height = await _current_viewport_height(client)
                await client.call(
                    "Emulation.setDeviceMetricsOverride",
                    {
                        "width": width,
                        "height": viewport_height,
                        "deviceScaleFactor": 1,
                        "mobile": False,
                    },
                )
                emulation_applied = True
            if url is not None:
                await client.call("Page.navigate", {"url": url})
            await _wait_for_ready_state(client, timeout_seconds=timeout_seconds)
            metrics = await client.call("Page.getLayoutMetrics")
            css_size = metrics.get("cssContentSize", {})
            viewport_width = width or math.ceil(float(css_size.get("width") or 1))
            capture_width = max(viewport_width, math.ceil(float(css_size.get("width") or viewport_width)))
            capture_height = max(1, math.ceil(float(css_size.get("height") or 900)))
            pixels = capture_width * capture_height
            if pixels > max_pixels:
                raise WebCaptureError(
                    f"page is too large to capture safely: {pixels} pixels exceeds {max_pixels}"
                )
            screenshot = await client.call(
                "Page.captureScreenshot",
                {
                    "format": "png",
                    "fromSurface": True,
                    "captureBeyondViewport": True,
                    "clip": {
                        "x": 0,
                        "y": 0,
                        "width": capture_width,
                        "height": capture_height,
                        "scale": 1,
                    },
                },
            )
            data = screenshot.get("data")
            if not isinstance(data, str):
                raise WebCaptureError("browser did not return screenshot data")
            return base64.b64decode(data)
        finally:
            if emulation_applied:
                try:
                    await client.call("Emulation.clearDeviceMetricsOverride")
                except WebCaptureError:
                    pass


async def _current_viewport_height(client: "_CdpClient") -> int:
    metrics = await client.call("Page.getLayoutMetrics")
    visual_viewport = metrics.get("cssVisualViewport", {})
    if isinstance(visual_viewport, dict):
        raw_height = visual_viewport.get("clientHeight") or visual_viewport.get("height")
        try:
            return max(1, math.ceil(float(raw_height)))
        except (TypeError, ValueError):
            pass
    return 900


class _CdpClient:
    def __init__(self, websocket: object) -> None:
        self.websocket = websocket
        self.next_id = 1

    async def call(self, method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        message_id = self.next_id
        self.next_id += 1
        await self.websocket.send(
            json.dumps({"id": message_id, "method": method, "params": params or {}})
        )
        while True:
            raw_message = await self.websocket.recv()
            message = json.loads(raw_message)
            if message.get("id") != message_id:
                continue
            if "error" in message:
                raise WebCaptureError(f"browser command failed: {message['error']}")
            result = message.get("result", {})
            if not isinstance(result, dict):
                raise WebCaptureError(f"browser command returned unexpected result for {method}")
            return result


async def _wait_for_ready_state(client: _CdpClient, *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = await client.call("Runtime.evaluate", {"expression": "document.readyState"})
        value = result.get("result", {})
        if isinstance(value, dict) and value.get("value") == "complete":
            await _wait_for_visual_settle(client)
            return
        await asyncio.sleep(0.25)
    raise WebCaptureError("timed out waiting for page load")


async def _wait_for_visual_settle(client: _CdpClient) -> None:
    await client.call(
        "Runtime.evaluate",
        {
            "expression": (
                "Promise.race(["
                "Promise.all(Array.from(document.images)"
                ".filter((img) => !img.complete)"
                ".map((img) => new Promise((resolve) => {"
                "img.addEventListener('load', resolve, {once: true});"
                "img.addEventListener('error', resolve, {once: true});"
                "}))),"
                "new Promise((resolve) => setTimeout(resolve, 1500))"
                "]).then(() => true)"
            ),
            "awaitPromise": True,
        },
    )
    await client.call(
        "Runtime.evaluate",
        {
            "expression": (
                "Promise.race(["
                "(document.fonts ? document.fonts.ready : Promise.resolve(true)),"
                "new Promise((resolve) => setTimeout(resolve, 1500))"
                "]).then(() => true)"
            ),
            "awaitPromise": True,
        },
    )
    await client.call(
        "Runtime.evaluate",
        {
            "expression": (
                "new Promise((resolve) => "
                "requestAnimationFrame(() => requestAnimationFrame(() => resolve(true))))"
            ),
            "awaitPromise": True,
        },
    )


def _find_browser() -> str:
    for command in ("google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(command)
        if path:
            return path
    raise WebCaptureError("no Chromium-family browser found on PATH")


def _open_devtools_target(port: int) -> dict[str, object]:
    encoded_url = quote("about:blank", safe="")
    endpoint = f"http://127.0.0.1:{port}/json/new?{encoded_url}"
    try:
        value = _http_json(endpoint, method="PUT")
    except WebCaptureError:
        value = _http_json(endpoint)
    if not isinstance(value, dict):
        raise WebCaptureError("browser target endpoint returned unexpected data")
    return value


def _wait_for_devtools(port: int, *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            _http_json(f"http://127.0.0.1:{port}/json/version", timeout=0.2)
            return
        except WebCaptureError:
            time.sleep(0.1)
    raise WebCaptureError("timed out waiting for browser automation backend")


def _http_json(url: str, *, method: str = "GET", timeout: float = 2.0) -> object:
    request = Request(url, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise WebCaptureError(str(exc)) from exc


def _active_window_title() -> str | None:
    xdotool = shutil.which("xdotool")
    if not xdotool:
        return None
    completed = subprocess.run(
        [xdotool, "getactivewindow", "getwindowname"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if completed.returncode != 0:
        return None
    title = completed.stdout.strip()
    return title or None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _validate_url(url: str) -> None:
    if not _is_safe_url(url):
        parsed = urlparse(url)
        scheme = parsed.scheme or "<missing>"
        raise WebCaptureError(f"unsupported URL scheme: {scheme}")


def _is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in SAFE_URL_SCHEMES:
        return False
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        return False
    if parsed.scheme == "file" and not os.environ.get("SPECTACLE_TOOLBELT_ALLOW_FILE_URLS"):
        return False
    return True
