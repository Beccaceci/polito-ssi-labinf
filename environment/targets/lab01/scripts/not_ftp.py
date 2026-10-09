import socket

def main():
    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket to a specific address and port
    server_socket.bind(('0.0.0.0', 2121))

    # Listen for incoming connections
    server_socket.listen(1)
    print('Server listening on port 2121...')

    while True:
        try:
            # Accept a connection from a client
            client_socket, client_address = server_socket.accept()
            print('Received connection from:', client_address)
            msg = "Enter your username: "
            client_socket.sendall(msg.encode('utf-8'))
            user = client_socket.recv(1024).decode('utf-8')
            msg = "Enter your password: "
            client_socket.sendall(msg.encode('utf-8'))
            password = client_socket.recv(1024).decode('utf-8')

            # Send a response back to the client
            response = 'I am not FTP and I just stole your credentials (◣_◢)!\n'
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