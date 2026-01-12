# API Reference

This document covers the NegMAS App REST API endpoints.

## Base URL

```
http://127.0.0.1:8019/api
```

## Endpoints

### Negotiations

#### Start Negotiation

```http
POST /api/negotiation/start
```

**Request Body:**
```json
{
    "scenario_path": "anac2015/Amsterdam",
    "negotiators": [
        {
            "type_name": "AspirationNegotiator",
            "name": "Agent1",
            "params": {}
        },
        {
            "type_name": "BoulwareTBNegotiator",
            "name": "Agent2",
            "params": {}
        }
    ],
    "mechanism_type": "SAOMechanism",
    "mechanism_params": {
        "n_steps": 100
    },
    "mode": "realtime",
    "step_delay": 100
}
```

**Response:**
```json
{
    "id": "abc123",
    "status": "running"
}
```

#### Get Negotiation Status

```http
GET /api/negotiation/{id}
```

**Response:**
```json
{
    "id": "abc123",
    "status": "running",
    "step": 45,
    "scenario": "Amsterdam",
    "negotiators": [...]
}
```

#### Stream Negotiation Events (SSE)

```http
GET /api/negotiation/{id}/stream
```

**Event Types:**
- `offer` - New offer made
- `response` - Response to offer
- `agreement` - Negotiation completed with agreement
- `failure` - Negotiation failed

### Scenarios

#### List Scenarios

```http
GET /api/scenarios
```

**Query Parameters:**
- `source` - Filter by source (optional)
- `search` - Search by name (optional)

**Response:**
```json
[
    {
        "path": "anac2015/Amsterdam",
        "name": "Amsterdam",
        "source": "anac2015",
        "n_negotiators": 2,
        "n_issues": 3,
        "n_outcomes": 1000
    }
]
```

#### Get Scenario Details

```http
GET /api/scenarios/{path}
```

**Response:**
```json
{
    "path": "anac2015/Amsterdam",
    "name": "Amsterdam",
    "issues": [
        {
            "name": "price",
            "type": "discrete",
            "values": ["low", "medium", "high"]
        }
    ],
    "n_negotiators": 2
}
```

### Negotiators

#### List Negotiator Types

```http
GET /api/negotiators
```

**Query Parameters:**
- `source` - Filter by source (optional)

**Response:**
```json
[
    {
        "type_name": "AspirationNegotiator",
        "name": "Aspiration Negotiator",
        "source": "negmas",
        "description": "Time-based aspiration strategy"
    }
]
```

#### Get Negotiator Parameters

```http
GET /api/negotiators/{type_name}/params
```

**Response:**
```json
{
    "params": [
        {
            "name": "aspiration_type",
            "type": "choice",
            "choices": ["linear", "boulware", "conceder"],
            "default": "linear"
        }
    ]
}
```

### Mechanisms

#### List Mechanism Types

```http
GET /api/mechanisms
```

**Response:**
```json
[
    {
        "class_name": "SAOMechanism",
        "name": "Stacked Alternating Offers",
        "description": "Standard SAO protocol"
    }
]
```

### Settings

#### Get Settings

```http
GET /api/settings
```

#### Update Settings

```http
POST /api/settings
```

### Genius Bridge

#### Get Bridge Status

```http
GET /api/genius/status
```

**Response:**
```json
{
    "installed": true,
    "running": false,
    "port": 25337
}
```

#### Start Bridge

```http
POST /api/genius/start
```

#### Stop Bridge

```http
POST /api/genius/stop
```

## Error Handling

All errors return JSON with the format:

```json
{
    "detail": "Error message"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad request
- `404` - Not found
- `500` - Server error
