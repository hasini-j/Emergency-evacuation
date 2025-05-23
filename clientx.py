import zmq
import json
import time
import pygame
import heapq

# --- Setup ---
client_id = input("Enter client ID: ")
current_node_letter = input("Enter current node (A-R): ").upper()

# Graph data (this should match the structure used in your server)
node_names = list("ABCDEFGHIJKLMNOPQR")
raw_graph = {  # Graph connectivity
    (95, 130): [(101, 272), (164, 264)],
    (101, 272): [(95, 130)],
    (124, 416): [(164, 264), (220, 420)],
    (164, 264): [(95, 130), (124, 416), (225, 310), (261, 180), (428, 171), (389, 260)],
    (220, 420): [(124, 416)],
    (225, 310): [(164, 264)],
    (295, 440): [(295, 360), (346, 407)],
    (295, 360): [(346, 407), (295, 440)],
    (346, 407): [(389, 260), (295, 360), (295, 440)],
    (389, 260): [(164, 264), (346, 407), (428, 171), (493, 264), (261, 180)],
    (428, 171): [(164, 264), (261, 180), (389, 260), (493, 264)],
    (493, 264): [(428, 171), (389, 260), (479, 466), (604, 258), (600, 157)],
    (600, 157): [(493, 264), (604, 258)],
    (604, 258): [(493, 264), (600, 157), (608, 351)],
    (608, 351): [(604, 258), (612, 448)],
    (612, 448): [(608, 351)],
    (479, 466): [(493, 264)],
    (261, 180): [(164, 264), (389, 260), (428, 171)],
}

coord_list = list(raw_graph.keys())
letter_to_coord = {letter: coord for letter, coord in zip(node_names, coord_list)}
coord_to_letter = {coord: letter for letter, coord in letter_to_coord.items()}

if current_node_letter not in letter_to_coord:
    raise ValueError("Invalid node letter")

current_node = letter_to_coord[current_node_letter]

# --- ZMQ SUB & PUSH Setup ---
context = zmq.Context()

# Client will send data to the server (PUSH)
req_socket = context.socket(zmq.PUSH)
req_socket.connect("tcp://192.168.1.6:5555") 

# --- ZMQ SUB Setup for receiving updates from server ---
sub_socket = context.socket(zmq.SUB)
sub_socket.connect("tcp://192.168.1.6:5556")
sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all topics

client_data = {
    "id": client_id,  # Client's ID
    "location": current_node_letter  # Sending initial node letter
}

# Send the initial node as JSON to the server
req_socket.send_string(json.dumps(client_data))

# Add delay to allow SUB socket to establish subscription
time.sleep(0.5)

# --- Pygame Setup ---
pygame.init()
IMAGE_WIDTH, IMAGE_HEIGHT = 700, 500
screen = pygame.display.set_mode((IMAGE_WIDTH, IMAGE_HEIGHT))
pygame.display.set_caption("Client Path Viewer")
floor_plan = pygame.image.load("Building-Floor-Plans-3-Bedroom-House-Floor-Plan.png")
floor_plan = pygame.transform.scale(floor_plan, (IMAGE_WIDTH, IMAGE_HEIGHT))

# Load flame image
flame_image = pygame.image.load("flame-png-4871.png")
flame_image = pygame.transform.scale(flame_image, (40, 40))  # Adjust the size as needed

WHITE, RED, BLUE, GREEN, ORANGE, BLACK, YELLOW = (255, 255, 255), (255, 0, 0), (0, 0, 255), (0, 255, 0), (255, 165, 0), (0, 0, 0), (255, 255, 0)

def scale(pt): return (int(pt[0] * IMAGE_WIDTH / 700), int(pt[1] * IMAGE_HEIGHT / 500))

scaled_graph = {
    scale(k): [scale(n) for n in v] for k, v in raw_graph.items()
}
scaled_coord_list = list(scaled_graph.keys())

# Create a reverse mapping from scaled coordinates to original coordinates
scaled_to_original = {scale(k): k for k in raw_graph.keys()}

# --- A* Setup ---
ALPHA = float('inf')  # Fire penalty
BETA = 10             # Crowd penalty

def heuristic(a, b):
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5

def a_star(start, goal, graph, fire_set, crowd_dict):
    open_set = [(0, start)]
    came_from = {}
    g_score = {node: float('inf') for node in graph}
    g_score[start] = 0
    f_score = {node: float('inf') for node in graph}
    f_score[start] = heuristic(start, goal)

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        for neighbor in graph[current]:
            fire_penalty = ALPHA if neighbor in fire_set else 0
            crowd_penalty = BETA * crowd_dict.get(neighbor, 0)
            move_cost = heuristic(current, neighbor)

            tentative_g = g_score[current] + move_cost + crowd_penalty + fire_penalty

            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return []

# Function to check if a click is within a node's clickable area
def is_click_on_node(pos, node, radius=15):
    x, y = pos
    node_x, node_y = node
    distance = ((x - node_x) ** 2 + (y - node_y) ** 2) ** 0.5
    return distance <= radius

# --- Main Loop ---
running = True
clock = pygame.time.Clock()

# Initialize an empty set to store fire nodes across iterations
fire_set = set()
# Track hovering state
hover_node = None

while running:
    try:
        msg = sub_socket.recv_json(flags=zmq.NOBLOCK)
        fire_nodes = msg.get("fire_nodes", [])
        crowd_map = msg.get("crowd", {})
        print(f"Received fire nodes: {fire_nodes}")  # Debug print statement
    except zmq.Again:
        fire_nodes = []
        crowd_map = {}

    # Add the newly received fire nodes to the persistent fire_set
    fire_set.update({scale(letter_to_coord[l]) for l in fire_nodes if l in letter_to_coord})

    crowd_dict = {scale(letter_to_coord[l]): crowd_map.get(l, 0) for l in crowd_map if l in letter_to_coord}

    # Goal is always Q
    goal_node = letter_to_coord["Q"]
    current_scaled = scale(current_node)
    shortest_path = a_star(current_scaled, scale(goal_node), scaled_graph, fire_set, crowd_dict)

    # Check for events including clicks
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Check if any node was clicked
            for node_scaled in scaled_coord_list:
                if is_click_on_node(event.pos, node_scaled):
                    # Update current node to the clicked node
                    node_original = scaled_to_original[node_scaled]
                    current_node = node_original
                    current_node_letter = coord_to_letter[current_node]
                    
                    # Send update to server
                    client_data = {
                        "id": client_id,
                        "location": current_node_letter
                    }
                    req_socket.send_string(json.dumps(client_data))
                    print(f"Moved to node {current_node_letter}")
                    break
        elif event.type == pygame.MOUSEMOTION:
            # Check if mouse is hovering over any node
            hover_node = None
            for node_scaled in scaled_coord_list:
                if is_click_on_node(event.pos, node_scaled):
                    hover_node = node_scaled
                    break

    # Draw
    screen.fill(WHITE)
    screen.blit(floor_plan, (0, 0))

    # Draw the graph connections
    for node, neighbors in scaled_graph.items():
        for neighbor in neighbors:
            pygame.draw.line(screen, BLUE, node, neighbor, 3)

    # Draw the nodes and fire (with flame image)
    for node in scaled_graph:
        # Determine node color based on state
        if node in fire_set:
            color = RED
        elif node == hover_node:
            color = YELLOW  # Highlight when hovering
        else:
            color = GREEN
            
        # Draw larger clickable area for nodes (invisible)
        pygame.draw.circle(screen, color, node, 6)
        
        # Draw the letter next to each node
        font = pygame.font.SysFont("Arial", 14)
        node_letter = coord_to_letter.get(scaled_to_original.get(node, None), "?")
        text = font.render(node_letter, True, BLACK)
        screen.blit(text, (node[0] + 10, node[1] - 10))

        if node in fire_set:
            screen.blit(flame_image, (node[0] - flame_image.get_width() // 2, node[1] - flame_image.get_height() // 2))

    # Highlight the shortest path
    for i in range(len(shortest_path) - 1):
        pygame.draw.line(screen, ORANGE, shortest_path[i], shortest_path[i+1], 4)
        pygame.draw.circle(screen, ORANGE, shortest_path[i], 5)

    # Draw current position
    current_scaled = scale(current_node)
    pygame.draw.circle(screen, BLACK, current_scaled, 8)

    # Display Client ID as a black diamond with white text
    client_pos = current_scaled
    pygame.draw.polygon(screen, BLACK, [
        (client_pos[0] - 8, client_pos[1]),
        (client_pos[0], client_pos[1] - 8),
        (client_pos[0] + 8, client_pos[1]),
        (client_pos[0], client_pos[1] + 8)
    ])
    font = pygame.font.SysFont("Arial", 12)
    text = font.render(client_id, True, WHITE)
    text_rect = text.get_rect(center=client_pos)
    screen.blit(text, text_rect)

    pygame.display.flip()
    clock.tick(10)  # Increased frame rate for better responsiveness

pygame.quit()