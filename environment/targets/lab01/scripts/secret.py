#!/usr/bin/env python3
"""TCP challenge service retained for direct service-identification practice."""

import socket


RESPONSE = r"""                      /^--^\     /^--^\     /^--^\
                      \____/     \____/     \____/
                     /      \   /      \   /      \
                    |        | |        | |        |
                     \__  __/   \__  __/   \__  __/
 ^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|^|
| | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |
########################/ /######\ \###########/ /#######################
| | | | | | | | | | | | \/| | | | \/| | | | | | \/ | | | | | | | | | | | |
|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|

SUPER SECRET ASCII CAT v2.4.67 proudly made by NSA

SSI{p0rt_scann3r5_4r3_4w3s0m3}
"""


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", 1337))
        server.listen(16)
        print("Server listening on port 1337...", flush=True)

        while True:
            client, address = server.accept()
            with client:
                print(f"Received connection from {address}", flush=True)
                try:
                    client.sendall(b"Press enter to start this powerful program: ")
                    client.recv(1024)
                    client.sendall(RESPONSE.encode("utf-8"))
                except (ConnectionError, OSError) as error:
                    print(f"Client {address} disconnected: {error}", flush=True)


if __name__ == "__main__":
    main()
