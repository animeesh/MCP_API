from typing import Any
import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from mcp.server.fastmcp import FastMCP

mcp= FastMCP("weather")

NWS_API_BASE= "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
        
def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
        Event: {props.get('event', 'Unknown')}
        Area: {props.get('areaDesc', 'Unknown')}
        Severity: {props.get('severity', 'Unknown')}
        Description: {props.get('description', 'No description available')}
        Instructions: {props.get('instruction', 'No specific instructions provided')}
        """

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)



@mcp.resource("echo://{message}")
def echo_resource(message: str) -> str:
    """Echo a message as a resource"""
    return f"Resource echo: {message}"


app = FastAPI()

class AlertsRequest(BaseModel):
    state: str

@app.post("/get_alerts")
async def get_alerts_api(request: AlertsRequest):
    """HTTP endpoint to call MCP get_alerts tool"""
    response = await get_alerts(request.state)
    return {"result": response}

class EchoRequest(BaseModel):
    message: str

@app.post("/echo")
def echo_api(request: EchoRequest):
    """HTTP endpoint to call echo_resource"""
    response = echo_resource(request.message)
    return {"result": response}

# ------------------------
# Server Runner
# ------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
