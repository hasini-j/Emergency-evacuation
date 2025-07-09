# AI-Based Emergency Evacuation System

This project is a real-time, AI-driven emergency evacuation system that detects fire and crowd congestion using a YOLOv5-based model and calculates optimal evacuation routes via a hazard-aware A\* path planning algorithm. The system uses a client-server architecture with ZeroMQ for scalable communication and Pygame for user interface visualization.

## System Overview

### Components

- **Deploy Nodes**: Clients running fire and crowd detection using YOLOv5; act as surveillance cameras.
- **Server**: Central controller that receives detection data, updates hazard maps.
- **Clients**: Devices used by users to runs A\* pathfinding, and finds optimal routes and view evacuation routes via a Pygame interface, and send position updates to the server.

### Communication Architecture

- **ZeroMQ** is used for messaging:
  - `PUB-SUB` pattern: Server subscribes to detection data from deploys.
  - `REQ-REP` pattern: Clients request detection data; server responds with fire nodes.
- All components must be connected to the same WiFi or LAN.
- Server IP is hardcoded into clients and deploys for connectivity.

### Visualization

- Clients display:
  - Fire nodes (fire symbols)
  - User location (black diamond with client id)
  - Evacuation paths (orange lines )
- Server display:
  - All Clients current locations
  - Fire nodes
- Exit nodes are assumed in code.
- Crowd information is shown only on the server console for reference.

---

## Installation & Setup

### Requirements

- Python 3.8+
- `pygame`, `pyzmq`, `torch`, `opencv-python`, `yolov5`, `numpy`, `matplotlib`
- Network connectivity (local network or same WiFi)

### Download from Drive

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## How to Run the System

### 1. Start the Server

```bash
python server.py
```

### 2. Run Deploy (Camera/Detection Nodes)

Get SERVER_IP_ADDRESS using 'ipconfig' on cmd in server's device and hardcode in deploy and client codes.

```bash
python deploys.py
```

### 3. Run Client (Evacuee's Interface)

```bash
python client.py
```

---

## Directory Structure

```bash
├── client.py
├── deploys.py
├── server.py
├── YoloFire/
│   └── yolofire/model
├── README.md
├── requirements.txt
├── flame-png-4871.png
├── Building-Floor-Plans-3-Bedroom-House.png
```

---

## Key Features

- Unified YOLOv5 model detects **both fire and crowd** with high accuracy.
- Modified **A\*** algorithm avoids fire zones using weighted costs.
- **Real-time communication** via ZeroMQ ensures instant route updates.
- **Scalable architecture** supports up to 32 clients.
- **Intuitive UI** with evacuation path guidance.

---

## Notes

- Ensure all devices are on the **same network**.
- Exit nodes are pre-configured in the code.
- Crowd data is logged on the server console but not used in routing or client visualization.

---

## Future Work

- Multi-floor (3D) pathfinding
- IoT sensor integration
- AR-based navigation
- Edge inference support

---

## Authors
- Hasini Jaishetty (231AI012)
- Mubashir Afzal (231AI021)
- Prajwal Meshram (231AI019)

Department of Information Technology  
National Institute of Technology Karnataka
