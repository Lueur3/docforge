"""Single instance application guard via QLocalServer / QLocalSocket.

When the user invokes DocForge again (e.g. via Explorer "Send to" or context menu),
incoming file paths are forwarded to the already running window, bringing it
to the foreground without spawning redundant Python processes or duplicating memory.
"""
import getpass
import logging
import os
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QWidget

log = logging.getLogger(__name__)


def server_name() -> str:
    user = getpass.getuser() or "default"
    return f"docforge_single_{user}"


def send_to_existing_instance(files: list[str]) -> bool:
    """If another DocForge instance is running, forward files to it and return True."""
    socket = QLocalSocket()
    socket.connectToServer(server_name())
    if not socket.waitForConnected(400):
        return False

    try:
        payload = "\n".join(os.path.abspath(f) for f in files).encode("utf-8")
        socket.write(payload)
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        if socket.state() != QLocalSocket.LocalSocketState.UnconnectedState:
            socket.waitForDisconnected(500)
        log.info("Передано %d файлов уже запущенному экземпляру DocForge", len(files))
        return True
    except Exception as e:
        log.debug("Ошибка отправки данных существующему экземпляру: %s", e)
        return False


class SingleInstanceServer:
    """Listens for files forwarded from secondary DocForge launches."""

    def __init__(self, on_files_received: Callable[[list[str]], None],
                 window: Optional[QWidget] = None) -> None:
        self._on_files_received = on_files_received
        self._window = window
        self._server = QLocalServer()
        name = server_name()
        # Clean up stale pipe/server from previous crashes
        self._server.removeServer(name)
        if not self._server.listen(name):
            log.warning("Не удалось запустить QLocalServer: %s", self._server.errorString())
        else:
            log.debug("QLocalServer слушает на %s", name)
            self._server.newConnection.connect(self._on_new_connection)

    def _on_new_connection(self) -> None:
        client = self._server.nextPendingConnection()
        if not client:
            return

        def read_client() -> None:
            data = bytes(client.readAll()).decode("utf-8", errors="replace")
            paths = [
                line.strip() for line in data.splitlines()
                if line.strip() and os.path.isfile(line.strip())
            ]
            if paths:
                log.info("Получено %d файлов от нового вызова", len(paths))
                self._on_files_received(paths)

            if self._window is not None:
                # Restore window if minimized and bring to front
                if self._window.isMinimized():
                    self._window.setWindowState(
                        self._window.windowState() & ~Qt.WindowState.WindowMinimized
                    )
                self._window.show()
                self._window.raise_()
                self._window.activateWindow()

        if client.bytesAvailable() > 0:
            read_client()
        else:
            client.readyRead.connect(read_client)

    def close(self) -> None:
        if self._server.isListening():
            self._server.close()
            self._server.removeServer(server_name())
