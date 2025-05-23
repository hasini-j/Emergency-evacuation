import zmq
import json
import pygame
from collections import defaultdict
import time

# --- ZMQ Setup ---
context = zmq.Context()

pull_socket = context.socket(zmq.PULL)
pull_socket.bind("tcp://*:5555")  # From deploys

pub_socket = context.socket(zmq.PUB)
pub_socket.bind("tcp://*:5556")  # To clients

# --- Graph Setup ---
raw_graph = {
    (95, 130): [(101, 272)],
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

IMAGE_WIDTH, IMAGE_HEIGHT = 700, 500

def scale_coordinates(point):
    x, y = point
    return int(x * IMAGE_WIDTH / 700), int(y * IMAGE_HEIGHT / 500)

graph = {
    scale_coordinates(node): [scale_coordinates(neighbor) for neighbor in neighbors]
    for node, neighbors in raw_graph.items()
}
coord_list = list(graph.keys())

# Map node positions to letters
node_letters = list("ABCDEFGHIJKLMNOPQR")
coord_to_letter = {scale_coordinates(k): l for k, l in zip(raw_graph.keys(), node_letters)}
letter_to_coord = {v: k for k, v in coord_to_letter.items()}

# --- Pygame Setup ---
pygame.init()
screen = pygame.display.set_mode((IMAGE_WIDTH, IMAGE_HEIGHT))
pygame.display.set_caption("Server Visualization")
floor_plan = pygame.image.load("Building-Floor-Plans-3-Bedroom-House-Floor-Plan.png")
floor_plan = pygame.transform.scale(floor_plan, (IMAGE_WIDTH, IMAGE_HEIGHT))
flame_img = pygame.image.load("flame-png-4871.png")
flame_img = pygame.transform.scale(flame_img, (37, 37))

WHITE, RED, BLUE, GREEN, ORANGE, BLACK, PURPLE = (255, 255, 255), (255, 0, 0), (0, 0, 255), (0, 255, 0), (255, 165, 0), (0, 0, 0), (128, 0, 128)

# --- State ---
burned = [False] * 26
crowd = defaultdict(int)
client_locations = {}  # {client_id: node_letter}

# Timer setup to periodically broadcast fire nodes
last_broadcast_time = time.time()

# Better font for display
pygame.font.init()
font = pygame.font.SysFont("Arial", 14)
title_font = pygame.font.SysFont("Arial", 18, bold=True)

print("Server is running...")

# --- Main Loop ---
clock = pygame.time.Clock()

running = True
while running:
        
    try:
        msg = pull_socket.recv(flags=zmq.NOBLOCK)  # <-- Just recv() raw
        try:
            data = json.loads(msg)  # Try parse as JSON (either string or dict)
        except:
            data = msg  # If already dict (because of recv_json), keep as is

        if isinstance(data, dict):
            if "id" in data and "location" in data and isinstance(data["location"], str):
                # Client location message (like {"id": "1", "location": "A"})
                client_id = data.get("id")
                
                client_position = data.get("location", "").upper()
                if client_position in letter_to_coord:
                    client_locations[client_id] = client_position
                    print(f"Client {client_id} updated at Node {client_position}")
            else:
                # Update message (with fire info)
                try:
                    location_data = data['location']

                    # Check if location is coordinates (tuple or list)
                    if isinstance(location_data, (list, tuple)):
                        client_coord = tuple(location_data)  # (x, y)
                        # Find the nearest node
                        nearest_node = min(coord_list, key=lambda c: (c[0] - client_coord[0])**2 + (c[1] - client_coord[1])**2)
                        node = coord_to_letter.get(nearest_node, '?')  # Convert coordinate to letter

                    # Else assume it's already a node (like 'A', 'B')
                    elif isinstance(location_data, str):
                        node = location_data.upper()

                    else:
                        node = '?'

                    people = data.get('people', 0)
                    fire = data.get('fire', False)
                    client_id = data.get('client_id', 'Unknown')
                    if client_id is None or client_id=="Unknown":
                        client_id=''
                    if node != '?':
                        loc = ord(node) - 65

                        if fire and not burned[loc]:
                            print(f"🔥 Node {node} is now burned")
                        if fire:
                            burned[loc] = True

                        crowd[node] = people
                        if client_id:  # Only update if client_id is provided
                            client_locations[client_id] = node
                        print(f"📍 Node {node} | 👥 People: {people} | 🔥 Fire: {fire} | 🧍 Client: {client_id}")
                    else:
                        print(f"⚠️ Invalid node received from client {client_id}")

                except Exception as e:
                    print(f"⚠️ Error processing client message: {e}")

    except zmq.Again:
        pass  # No new data

    # --- Fire node broadcast --- 
    # Periodically broadcast fire nodes every 1 second
    current_time = time.time()
    if current_time - last_broadcast_time >= 1:
        fire_nodes = [chr(i + 65) for i, b in enumerate(burned) if b]
        
        # Include client locations in the broadcast
        broadcast_data = {
            "fire_nodes": fire_nodes,
            "crowd": crowd,
            "clients": client_locations  # Add client locations to the broadcast
        }
        
        pub_socket.send_json(broadcast_data)
        last_broadcast_time = current_time  # Reset broadcast timer

    # --- Drawing ---
    screen.fill(WHITE)
    screen.blit(floor_plan, (0, 0))

    # Draw edges
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            pygame.draw.line(screen, BLUE, node, neighbor, 3)

    # Draw nodes
    for coord in coord_list:
        letter = coord_to_letter.get(coord, '?')
        loc = ord(letter) - 65
        is_burned = burned[loc]
        
        # Draw node
        pygame.draw.circle(screen, RED if is_burned else GREEN, coord, 6)
        
        # Draw node letter
        text = font.render(letter, True, BLACK)
        screen.blit(text, (coord[0] + 10, coord[1] - 10))
        
        if is_burned:
            flame_rect = flame_img.get_rect(center=coord)
            screen.blit(flame_img, flame_rect)

    # Draw client positions with diamond shapes and IDs
    for client_id, letter in client_locations.items():
        if not client_id:
            continue
            
        coord = scale_coordinates(letter_to_coord[letter])
        
        # Draw diamond for client position
        diamond = [
            (coord[0], coord[1] - 15),  # Top
            (coord[0] - 15, coord[1]),  # Left
            (coord[0], coord[1] + 15),  # Bottom
            (coord[0] + 15, coord[1]),  # Right
        ]
        pygame.draw.polygon(screen, PURPLE, diamond)  # Draw filled diamond
        
        # Draw client ID text
        id_text = font.render(client_id, True, WHITE)
        id_rect = id_text.get_rect(center=coord)
        screen.blit(id_text, id_rect)
    
    # Draw legend
    legend_y = 10
    legend_x = 10
    
    # Title
    title_text = title_font.render("EMERGENCY EVACUATION SYSTEM", True, BLACK)
    screen.blit(title_text, (legend_x, legend_y))
    legend_y += 30
    
    # Fire nodes
    fire_text = font.render("🔥 Fire Nodes:", True, RED)
    screen.blit(fire_text, (legend_x, legend_y))
    
    # List fire nodes
    fire_nodes = [chr(i + 65) for i, b in enumerate(burned) if b]
    if fire_nodes:
        fire_list = ", ".join(fire_nodes)
    else:
        fire_list = "None"
    fire_list_text = font.render(fire_list, True, BLACK)
    screen.blit(fire_list_text, (legend_x + 120, legend_y))
    legend_y += 25
    
    # Client locations
    client_text = font.render("👤 Clients:", True, PURPLE)
    screen.blit(client_text, (legend_x, legend_y))
    
    # List clients with their locations
    client_y = legend_y
    for i, (client_id, location) in enumerate(client_locations.items()):
        if i > 0 and i % 3 == 0:  # Show 3 clients per row
            client_y += 20
            client_x = legend_x + 120
        else:
            client_x = legend_x + 120 + (i % 3) * 100
            
        client_info = f"{client_id}: Node {location}"
        client_info_text = font.render(client_info, True, BLACK)
        screen.blit(client_info_text, (client_x, client_y))
    
    # Handle quit
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    pygame.display.flip()
    clock.tick(5)

pygame.quit()