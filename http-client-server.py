import socket
import threading
import time

# Define host and port from machine hostname and any port >1024 to avoid privilege escalation
HOST, PORT = socket.gethostbyname(socket.gethostname()), 8080
# Allow for 10 incoming connections in backlog
SERVER_BACKLOG = 10
# Declare a global lock for allowing prints to finish when threading
PRINT_LOCK = threading.Lock()


def thread_print(arg):
    """
    Thread-safe print function. Ensures only one thread holds the printing lock to avoid mangling output
    :param arg: the value to print
    :return: None
    """
    with PRINT_LOCK:
        print(arg)


def handle_client(sock: socket.socket, addr):
    """
    Server-handling of clients. Adheres to HTTP/1.1 with persistent connections but does not handle pipelined requests.
     Handles only GET requests and validates protocol.
    FIXME: time.time() calls are many and expensive - does not take actual handling into account.
     Busy-waiting on empty data is expensive. Implement pipelined requests by threading request-handling.
    :param sock: the socket representing the client connection
    :param addr: the address (IP:PORT) for printing
    :return: None
    """
    # Allow for, at most, thirty seconds to elapse between requests.
    timeout = 30
    time_now = time.time()
    # While within the timeout, continue handling requests, otherwise close socket and return
    while time.time() < time_now + timeout:
        # Receive, at max, 512 bytes of data over socket, from client and decode, expecting UTF-8 encoding
        data = sock.recv(512).decode("UTF-8")

        # Busy-wait if nothing was received
        if data == "":
            time.sleep(0.1)
            continue

        # Print client-request with address prepended
        thread_print(f"[SERVER] Received from {addr[0]}:{addr[1]}: {data.strip()}")

        # If request was not a HTTP/1.1 request, send notice, close socket, and thread
        if not data.split()[2].strip() == "HTTP/1.1":
            thread_print("[SERVER] Got a non HTTP/1.1 request. Informing and closing socket")
            sock.sendall(
                b"HTTP/1.1 505 HTTP Version not supported\r\n\r\nServer only accepts HTTP/1.1. Please try again.")
            sock.close()
            return

        # Process a GET request
        if data.startswith("GET"):
            # Get specified location of request-line
            location = data.split(" ")[1]

            # Contemporary browsers want favicons. Return 404 on such a request, close socket, and continue
            if location == "/favicon.ico":
                thread_print(f"[SERVER] Got GET request for 'favicon.ico' from {addr[0]}:{addr[1]}. Returning 404")
                sock.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")
                continue

            # Map implicit requests to root as 'index.html'
            if location == "/":
                location = "www/index.html"
            else:
                # Convert location to local mapping of public files.
                location = "www" + location

            thread_print(f"[SERVER] Got GET request, trying to open {location}")

            # Try finding requested location, replying with 200 and content, or 404, and error-message
            try:
                with open(location, "r") as file:
                    # Send requested location, joining read file from list, and encoding before sending
                    data = "HTTP/1.1 200 OK\r\n\r\n" + "".join(file.readlines())
                    sock.sendall(data.encode("UTF-8"))
                    thread_print(f"[SERVER] Sent: {data.strip()}")
            except FileNotFoundError as e:
                data = f"HTTP/1.1 404 Not Found\r\n\r\nCould not find {location}, server-stack: {e}"
                sock.sendall(data.encode("UTF-8"))
                thread_print(f"[SERVER] ERROR: could not find {location}. Sent: {data}")
            # Set new current-time after request has finished
            time_now = time.time()

        else:
            # Return a 500 for all other requests
            thread_print(f"[SERVER] Got a non-GET request. Sending 500 error to client. Received: {data.strip()}")
            sock.sendall("HTTP/1.1 500 Internal Server Error".encode("UTF-8"))

    thread_print(f"[SERVER] Timeout reached for {addr[0]}:{addr[1]}. Closing socket and thread.")
    sock.close()
    return


def start_server():
    """
    Starts a socket using IPv4 and TCP, listens for incoming connections,
    and passes accepted connections' sockets to handle_client()
    :return: None
    """
    thread_print(f"[SERVER] Using address: {HOST}:{PORT}")

    # Create socket using IPv4 and TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Allow rapid restarting of server
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind socket to address
    sock.bind((HOST, PORT))

    thread_print(f"[SERVER] Bound to: {HOST}:{PORT}")

    # Begin listening for incoming connections, allowing up to ten pending connections in backlog
    sock.listen(SERVER_BACKLOG)
    thread_print(f"[SERVER] Begun listening for incoming connections. Backlog set to {SERVER_BACKLOG}")

    # Continuously wait for new, incoming connections
    while True:
        # Count active 'Server-handle' threads.
        count = 0
        for th in threading.enumerate():
            if th.name == "Server-handle":
                count += 1

        thread_print(f"[SERVER] Currently handling: {count} active connections")
        # socket.accept() returns a new socket, representing each new connection established
        (connection, address) = sock.accept()
        threading.Thread(target=handle_client, name="Server-handle", args=(connection, address)).start()


def start_client():
    # Create a socket using IPv4 and TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    thread_print(f"[CLIENT] Attempting to connect to: {(HOST, PORT)}")
    sock.connect((HOST, PORT))

    # Form a HTTP/1.1 GET request for '/'
    request = "GET / HTTP/1.1"

    thread_print(f"[CLIENT] Sending: {request}")
    sock.sendall(request.encode("UTF-8"))

    # Get response from server
    data = sock.recv(512).decode("UTF-8").strip()
    thread_print(f"[CLIENT] Received: {data}")


def run():
    # Start a single server
    threading.Thread(target=start_server, name="Server-main").start()
    # Wait slightly to beautify output
    time.sleep(0.25)
    # Spin up two clients as simultaneously as possible
    for i in range(2):
        threading.Thread(target=start_client, name="Client").start()


run()
