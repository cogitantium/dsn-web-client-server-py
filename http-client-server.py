import socket
import threading
import time

"""
    The purpose of this exercise is to focus on programming using sockets, 
        i.e. you are not allowed to use higher level abstractions provided by the language.
    Implement a simple web client-server using TCP. The client should be able to request a static web-page
    from the web-server and present the returned code on the screen (it should also work with standard web-servers).
    The server should be able to accept requests (HTTP GET) and return a static web-page.
    Remember that the server must be able to handle concurrent requests
    (again the server should also work if the request comes from a standard web-server).
"""

# Define host and port - the address to bind to - from machine hostname
# and any port >1024 to avoid privilege escalation
HOST, PORT = socket.gethostbyname(socket.gethostname()), 8080
# Allow for 10 incoming connections in backlog
SERVER_BACKLOG = 10
# Declare a global lock for allowing prints to finish when threading.
PRINT_LOCK = threading.Lock()


def get_server_addr() -> (str, int):
    """
    Return the server-address constants for external use by clients
    :return: Tuple [str: address, int: port]
    """
    return HOST, PORT


def thread_print(arg):
    # Ensure only one thread holds the printing lock to avoid mangling output
    with PRINT_LOCK:
        print(arg)


def handle_client(sock: socket, addr):
    data = sock.recv(512).decode("UTF-8")

    thread_print(f"[SERVER] Received from {addr[0]}:{addr[1]}: {data}")

    # If request was not a HTTP/1.1 request, send notice, close socket and thread
    if not validate_protocol(data):
        thread_print("[SERVER] Got a non HTTP/1.1 request. Informing and closing socket")
        sock.sendall(b"Server only accepts HTTP/1.1. Please try again")
        sock.close()
        return

    # Process a GET request
    if data.startswith("GET"):
        location = data.split(" ")[1]
        if location == "/":
            location = "index.html"
        thread_print(f"[SERVER] Got GET request, trying to open {location}")
        # Try finding request
        try:
            with open(location, "r") as file:
                # Send requested location, joining list, and encoding
                sock.sendall("".join(file.readlines()).encode("UTF-8"))
        except OSError:
            print("shit")


def validate_protocol(req):
    """
    Returns whether request specified HTTP/1.1 protocol
    :param req: the request to validate
    :return: boolean on accept
    """
    return req.split(" ")[2] == "HTTP/1.1"


def start_server():
    """
    Starts a socket using IPv4 and TCP, listens for incoming connections,
    and passes accepted connections' sockets to handle_client()
    :return: None
    """
    thread_print(f"[SERVER] Address: {HOST}:{PORT}")

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
        # Omit the server-thread from counting active connections. Todo: figure out if main thread counts
        thread_print(f"[SERVER] Currently handling: {threading.active_count() - 2} active connections")
        # socket.accept() returns a new socket, representing each new connection established
        (connection, address) = sock.accept()
        threading.Thread(target=handle_client, args=(connection, address)).start()


def start_client():
    # Create a socket using IPv4 and TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    thread_print(f"[CLIENT] Attempting to connect to: {get_server_addr()}")
    sock.connect(get_server_addr())

    # Form a HTTP/1.1 GET request for '/'
    request = b"GET / HTTP/1.1"

    thread_print(f"[CLIENT] Sending: {request}")
    sock.sendall(request)

    # Get response from server
    data = sock.recv(512).decode("UTF-8")
    thread_print(f"[CLIENT] Received: {data}")


def test():
    # Start a single server, todo: spin multiple servers up, incrementing port when unable to bind (client discovery)?
    threading.Thread(target=start_server).start()
    time.sleep(1)
    for i in range(5):
        threading.Thread(target=start_client).start()


# Run test on execution
test()
