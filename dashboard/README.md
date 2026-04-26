# MLB Live Predictions Dashboard

Real-time dashboard for visualizing MLB game predictions from the WebSocket server.

## Quick Start

### 1. Start the WebSocket Server

```bash
cd /home/cbwinslow/workspace/retrosheet
baseball live server --port 8765
```

### 2. Open the Dashboard

Simply open `dashboard/index.html` in any modern web browser:

```bash
# On macOS
open dashboard/index.html

# On Linux
xdg-open dashboard/index.html

# On Windows
start dashboard/index.html
```

Or use a local server for better WebSocket support:

```bash
cd dashboard
python3 -m http.server 8080
# Then open http://localhost:8080
```

### 3. Connect to WebSocket

1. Enter the WebSocket URL (default: `ws://localhost:8765`)
2. Optionally enter a specific Game PK
3. Click **Connect**

The dashboard will auto-discover active games and display real-time predictions.

## Features

- **Real-time Updates**: Live game state with auto-refresh
- **Win Probability**: Visual probability bar (green = home, red = away)
- **Game Situation**: Inning, outs, count, base runners
- **Confidence Score**: Model confidence percentage
- **Latency Metrics**: Prediction latency in milliseconds
- **Connection Log**: Debug messages and server communication

## Dashboard UI

```
┌─────────────────────────────────────────┐
│ ⚾ MLB Live Predictions   [Connected]    │
├─────────────────────────────────────────┤
│ [ws://localhost:8765] [Connect] [Log]   │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ [LIVE]              Inning 5 ▲      │ │
│ │                                     │ │
│ │  Away 2    VS    Home 3           │ │
│ │                                     │ │
│ │   2 outs, 1-2 count • Runners on  │ │
│ │                                     │ │
│ │  ████████████████░░░░░░░░░░░░░░░░   │ │
│ │  38.2%                    61.8%   │ │
│ │                                     │ │
│ │ Confidence  92%  Latency  12ms      │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## WebSocket Protocol

The dashboard communicates with the server using JSON messages:

### Client → Server
```json
{"command": "games"}
{"command": "subscribe", "game_pk": 12345}
{"command": "unsubscribe", "game_pk": 12345}
{"command": "ping"}
```

### Server → Client
```json
{
  "type": "prediction",
  "game_pk": 12345,
  "game_state": {
    "inning": 5,
    "is_top": true,
    "outs": 2,
    "balls": 1,
    "strikes": 2,
    "home_score": 3,
    "away_score": 2,
    "base_state": 3,
    "status": "Live"
  },
  "prediction": {
    "home_win_probability": 0.618,
    "away_win_probability": 0.382,
    "confidence": 0.92,
    "model_version": "xgboost_v1",
    "latency_ms": 12.5
  }
}
```

## Configuration

Edit the default WebSocket URL in `index.html`:

```javascript
const DEFAULT_WS_URL = 'ws://localhost:8765';
```

## Browser Compatibility

- Chrome 80+
- Firefox 75+
- Safari 13.1+
- Edge 80+

Requires WebSocket support (all modern browsers).

## Development

To modify the dashboard:

1. Edit `index.html`
2. Refresh browser to see changes
3. Use browser DevTools for debugging

No build step required - pure HTML/CSS/JavaScript.

## Troubleshooting

### Connection Refused
- Ensure WebSocket server is running: `baseball live server`
- Check firewall settings for port 8765
- Verify correct URL in connection field

### No Games Displayed
- Check server logs for active games
- Verify MLB API is returning live data
- Try fetching games manually: `baseball live games`

### CORS Errors
- Use `python3 -m http.server` instead of opening file directly
- Or configure browser to allow file:// WebSocket connections

## Related

- `mlb_predict/streaming/server.py` - WebSocket server implementation
- `docs/agents/live_agent.md` - Live data architecture documentation
- Issue #95 - Phase 3 tracking
