import sys
import os
from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QLocalSocket, QLocalServer
from PySide6.QtWidgets import QApplication
from app import MiniIDM

SERVER_NAME = "DownGo_4_SingleInstance_Server"

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Check if another instance is already running
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(500):
        # Notify the running instance to show itself
        socket.write(b"SHOW")
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        sys.exit(0)  # Close the secondary instance

    # If no instance is running, start the Local Server
    server = QLocalServer()
    server.listen(SERVER_NAME)

    background = "--background" in sys.argv
    window = MiniIDM(start_hidden=background)

    # Listen for signals from duplicate launches
    def handle_connection():
        client_socket = server.nextPendingConnection()
        if client_socket:
            client_socket.readyRead.connect(lambda: _read_socket(client_socket, window))

    def _read_socket(client, win):
        msg = client.readAll().data().decode().strip()
        if msg == "SHOW":
            win.show_normal()
        client.disconnectFromServer()

    server.newConnection.connect(handle_connection)

    # Normal launch shows the window. Windows Startup uses --background so the
    # app initializes quietly in the tray and never pops open after boot.
    if not background:
        window.show()
    else:
        window.hide()
        # Give Windows/network services a moment to settle without showing UI.
        QTimer.singleShot(2500, lambda: None)

    ret = app.exec()
    server.close()
    sys.exit(ret)

if __name__ == "__main__":
    main()