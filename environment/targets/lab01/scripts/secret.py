import socket

def main():
    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket to a specific address and port
    server_socket.bind(('0.0.0.0', 1337))

    # Listen for incoming connections
    server_socket.listen(1)
    print('Server listening on port 1337...')

    while True:
        try:
            # Accept a connection from a client
            client_socket, client_address = server_socket.accept()
            print('Received connection from:', client_address)
            head = "Press enter to start this powerful program: "
            client_socket.sendall(head.encode('utf-8'))
            # Receive data from the client
            data = client_socket.recv(1024).decode('utf-8')
            print('Received data:', data)

            # Send a response back to the client
            response = \
    "                      /^--^\     /^--^\     /^--^\\\n" + \
    "                      \____/     \____/     \____/\n" + \
    "                     /      \   /      \   /      \\\n" + \
    "                    |        | |        | |        |\n" + \
    "                     \__  __/   \__  __/   \__  __/\n" + \
    " ^|^|^|^|^|^|^|^|^|^|^|^\ \^|^|^|^/ /^|^|^|^|^\ \^|^|^|^|^|^|^|^|^|^|^|^|\n" + \
    "| | | | | | | | | | | | |\ \| | |/ /| | | | | | \ \ | | | | | | | | | | |\n" + \
    "########################/ /######\ \###########/ /#######################\n" + \
    "| | | | | | | | | | | | \/| | | | \/| | | | | |\/ | | | | | | | | | | | |\n" + \
    "|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|\n" + \
    "\n\nSUPER SECRET ASCII CAT v2.4.67 proudly made by NSA\n\n" + \
    "SSI{p0rt_scann3r5_4r3_4w3s0m3}\n"
            client_socket.sendall(response.encode('utf-8'))

            # Close the connection
            client_socket.close()
        except Exception as e:
            print(e)
            client_socket.close()
            break
    server_socket.close()

if __name__ == '__main__':
    while True:
        main()