from __future__ import annotations

import asyncio
import base64
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from spectacle_toolbelt.web.fullpage import (
    ActiveBrowserTab,
    FullPageCaptureRequest,
    WebCaptureError,
    capture_fullpage_web,
    copy_png_to_clipboard,
    resolve_active_browser_tab,
    _capture_page_png,
    _wait_for_ready_state,
)


def test_fullpage_capture_rejects_unsafe_url(tmp_path) -> None:
    with pytest.raises(WebCaptureError, match="unsupported URL scheme"):
        capture_fullpage_web(
            FullPageCaptureRequest(
                url="javascript:alert(1)",
                output=tmp_path / "page.png",
                prompt_for_url=False,
            )
        )


def test_fullpage_capture_uses_supplied_backend_and_skips_clipboard(tmp_path) -> None:
    output = tmp_path / "page.png"

    def backend(
        url: str,
        output_path: Path,
        *,
        width: int,
        timeout_seconds: float,
        max_pixels: int,
    ) -> None:
        assert url == "https://example.com/"
        assert output_path == output
        assert width == 1365
        assert timeout_seconds == 30.0
        assert max_pixels > 0
        output_path.write_bytes(b"png")

    result = capture_fullpage_web(
        FullPageCaptureRequest(
            url="https://example.com/",
            output=output,
            copy_to_clipboard=False,
            open_in_spectacle=False,
            prompt_for_url=False,
        ),
        backend=backend,
    )

    assert result.status == "complete"
    assert result.output_path == output
    assert result.copied_to_clipboard is False


def test_fullpage_capture_preserves_resolved_active_tab_session(tmp_path) -> None:
    output = tmp_path / "page.png"

    def existing_tab_backend(
        websocket_url: str,
        output_path: Path,
        *,
        width: int | None,
        timeout_seconds: float,
        max_pixels: int,
    ) -> None:
        assert websocket_url == "ws://127.0.0.1/devtools/page/1"
        assert width == 1365
        assert timeout_seconds == 30.0
        assert max_pixels > 0
        output_path.write_bytes(b"png")

    with (
        patch(
            "spectacle_toolbelt.web.fullpage.resolve_active_browser_tab",
            return_value=ActiveBrowserTab(
                url="https://example.com/account",
                websocket_url="ws://127.0.0.1/devtools/page/1",
            ),
        ),
        patch("spectacle_toolbelt.web.fullpage.capture_existing_chromium_tab", side_effect=existing_tab_backend),
        patch("spectacle_toolbelt.web.fullpage.capture_with_chromium") as new_browser_backend,
    ):
        result = capture_fullpage_web(
            FullPageCaptureRequest(
                output=output,
                copy_to_clipboard=False,
                open_in_spectacle=False,
                prompt_for_url=False,
            )
        )

    assert result.status == "complete"
    assert result.url == "https://example.com/account"
    assert output.exists()
    new_browser_backend.assert_not_called()


def test_fullpage_capture_reports_spectacle_handoff_failure(tmp_path) -> None:
    output = tmp_path / "page.png"

    def backend(
        url: str,
        output_path: Path,
        *,
        width: int,
        timeout_seconds: float,
        max_pixels: int,
    ) -> None:
        output_path.write_bytes(b"png")

    with patch("spectacle_toolbelt.web.fullpage.open_in_spectacle", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError, match="boom"):
            capture_fullpage_web(
                FullPageCaptureRequest(
                    url="https://example.com/",
                    output=output,
                    copy_to_clipboard=False,
                    prompt_for_url=False,
                ),
                backend=backend,
            )


def test_fullpage_capture_reports_editor_handoff_error(tmp_path) -> None:
    output = tmp_path / "page.png"

    def backend(
        url: str,
        output_path: Path,
        *,
        width: int,
        timeout_seconds: float,
        max_pixels: int,
    ) -> None:
        output_path.write_bytes(b"png")

    with patch(
        "spectacle_toolbelt.web.fullpage.open_in_spectacle",
        side_effect=_editor_handoff_error("spectacle failed"),
    ):
        with pytest.raises(WebCaptureError, match="Spectacle editor handoff failed"):
            capture_fullpage_web(
                FullPageCaptureRequest(
                    url="https://example.com/",
                    output=output,
                    copy_to_clipboard=False,
                    prompt_for_url=False,
                ),
                backend=backend,
            )


def test_active_tab_resolution_requires_exact_normalized_title_match() -> None:
    tabs = [
        {
            "type": "page",
            "title": "GitHub notifications",
            "url": "https://github.com/notifications",
            "webSocketDebuggerUrl": "ws://127.0.0.1/devtools/page/notifications",
        },
        {
            "type": "page",
            "title": "GitHub issues",
            "url": "https://github.com/issues",
            "webSocketDebuggerUrl": "ws://127.0.0.1/devtools/page/issues",
        },
    ]

    with (
        patch("spectacle_toolbelt.web.fullpage._active_window_title", return_value="GitHub - Google Chrome"),
        patch("spectacle_toolbelt.web.fullpage._http_json", return_value=tabs),
    ):
        assert resolve_active_browser_tab() is None


def test_active_tab_resolution_does_not_fallback_to_single_tab_when_active_title_differs() -> None:
    tabs = [
        {
            "type": "page",
            "title": "Different Page",
            "url": "https://example.com/different",
            "webSocketDebuggerUrl": "ws://127.0.0.1/devtools/page/different",
        },
    ]

    with (
        patch("spectacle_toolbelt.web.fullpage._active_window_title", return_value="ShareX / ShareX - Google Chrome"),
        patch("spectacle_toolbelt.web.fullpage._http_json", return_value=tabs),
    ):
        assert resolve_active_browser_tab() is None


def test_active_tab_resolution_uses_single_exact_browser_title_match() -> None:
    tabs = [
        {
            "type": "page",
            "title": "ShareX / ShareX",
            "url": "https://github.com/ShareX/ShareX",
            "webSocketDebuggerUrl": "ws://127.0.0.1/devtools/page/sharex",
        },
        {
            "type": "page",
            "title": "GitHub issues",
            "url": "https://github.com/issues",
            "webSocketDebuggerUrl": "ws://127.0.0.1/devtools/page/issues",
        },
    ]

    with (
        patch("spectacle_toolbelt.web.fullpage._active_window_title", return_value="ShareX / ShareX - Google Chrome"),
        patch("spectacle_toolbelt.web.fullpage._http_json", return_value=tabs),
    ):
        tab = resolve_active_browser_tab()

    assert tab == ActiveBrowserTab(
        url="https://github.com/ShareX/ShareX",
        websocket_url="ws://127.0.0.1/devtools/page/sharex",
    )


def test_copy_png_to_clipboard_uses_xsel_fallback(tmp_path) -> None:
    image = tmp_path / "page.png"
    image.write_bytes(b"png")

    def which(command: str) -> str | None:
        return "/usr/bin/xsel" if command == "xsel" else None

    with (
        patch("spectacle_toolbelt.web.fullpage.shutil.which", side_effect=which),
        patch("spectacle_toolbelt.web.fullpage.subprocess.run") as run,
    ):
        run.return_value.returncode = 0

        assert copy_png_to_clipboard(image)

    assert run.call_args.args[0] == ["/usr/bin/xsel", "--clipboard", "--input"]


def test_wait_for_ready_state_requires_complete_and_visual_settle() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.ready_values = ["interactive", "complete"]
            self.calls: list[tuple[str, dict[str, object] | None]] = []

        async def call(self, method: str, params: dict[str, object] | None = None) -> dict[str, object]:
            self.calls.append((method, params))
            if params and params.get("expression") == "document.readyState":
                return {"result": {"value": self.ready_values.pop(0)}}
            return {"result": {"value": True}}

    client = FakeClient()

    asyncio.run(_wait_for_ready_state(client, timeout_seconds=2))

    expressions = [params.get("expression") for _, params in client.calls if params]
    assert expressions[0] == "document.readyState"
    assert expressions[1] == "document.readyState"
    assert any("document.images" in str(expression) for expression in expressions)
    assert any("document.fonts" in str(expression) for expression in expressions)
    assert any("requestAnimationFrame" in str(expression) for expression in expressions)


def test_capture_page_png_restores_active_tab_emulation() -> None:
    class FakeConnect:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
            return None

    class FakeClient:
        def __init__(self, websocket: object) -> None:
            self.calls: list[tuple[str, dict[str, object] | None]] = []

        async def call(self, method: str, params: dict[str, object] | None = None) -> dict[str, object]:
            self.calls.append((method, params))
            if method == "Runtime.evaluate":
                if params and params.get("expression") == "document.readyState":
                    return {"result": {"value": "complete"}}
                return {"result": {"value": True}}
            if method == "Page.getLayoutMetrics":
                return {
                    "cssVisualViewport": {"clientHeight": 777},
                    "cssContentSize": {"width": 1200, "height": 2400},
                }
            if method == "Page.captureScreenshot":
                return {"data": base64.b64encode(b"png").decode("ascii")}
            return {}

    fake_client_holder: dict[str, FakeClient] = {}

    def client_factory(websocket: object) -> FakeClient:
        client = FakeClient(websocket)
        fake_client_holder["client"] = client
        return client

    fake_websockets = SimpleNamespace(connect=lambda *args, **kwargs: FakeConnect())
    with (
        patch.dict(sys.modules, {"websockets": fake_websockets}),
        patch("spectacle_toolbelt.web.fullpage._CdpClient", side_effect=client_factory),
    ):
        png = asyncio.run(
            _capture_page_png(
                "ws://127.0.0.1/devtools/page/1",
                None,
                width=900,
                timeout_seconds=5,
                max_pixels=10_000_000,
            )
        )

    assert png == b"png"
    calls = fake_client_holder["client"].calls
    set_emulation = next(params for method, params in calls if method == "Emulation.setDeviceMetricsOverride")
    assert set_emulation is not None
    assert set_emulation["width"] == 900
    assert set_emulation["height"] == 777
    assert calls[-1][0] == "Emulation.clearDeviceMetricsOverride"


def _editor_handoff_error(message: str) -> Exception:
    from spectacle_toolbelt.output.editor_handoff import EditorHandoffError

    return EditorHandoffError(message)
