import logging
from datetime import datetime
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

app = FastAPI()

logger = logging.getLogger("uvicorn")

# ✅ Initialize Rate Limiter (5 requests per minute per IP)
limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

#base URLs for APIs
WEATHER_API_BASE = "https://swd.weatherflow.com/swd/rest/better_forecast"
PARQET_API_BASE = "https://api.parqet.com/v1/portfolios/assemble?useInclude=true&include=ttwror&include=performance_charts&resolution=200"


# Model for the new query parameters
class WeatherRequest(BaseModel):
    station_id: str
    units_temp: Literal["c", "f"]
    units_wind: Literal["mph", "kph", "m/s"]
    units_pressure: Literal["mb", "inHg"]
    units_precip: Literal["in", "mm"]
    units_distance: Literal["mi", "km"]
    api_key: str

class PortfolioRequest(BaseModel):
    id: str
    timeframe: Literal["today", "1d", "1w", "1m", "3m", "6m", "1y", "5y", "10y", "mtd", "ytd", "max"]
    perf: Literal["returnGross", "returnNet", "totalReturnGross", "totalReturnNet", "ttwror", "izf"]
    perfChart: Literal["perfHistory", "perfHistoryUnrealized", "ttwror", "drawdown"]



async def fetch_weather_data(url: str, params: dict):
    """Helper function to send a request to the Weather API."""
    logger.info(f"Sending request to {url} with params {params}")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Weather API error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")

async def fetch_parqet_data(url: str, payload: dict):
    """Helper function to send a request to Parqet."""
    logger.info(f"Sending request to {url} with payload {payload}")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Parqet API error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")


def transform_data_tempest(data: dict) -> dict:
    """
    Filters and restructures JSON to include only specified fields.
    Includes the first 4 daily forecast items and adds `day_start_local`.
    """
    filtered_data = {
        "current_conditions": {},
        "forecast": {
            "daily": []  # Initialize an empty list for daily forecasts
        }
    }

    # Filter current conditions
    if "current_conditions" in data:
        current_conditions = data["current_conditions"]
        filtered_data["current_conditions"]["air_temperature"] = current_conditions.get("air_temperature")
        filtered_data["current_conditions"]["icon"] = current_conditions.get("icon")
        filtered_data["current_conditions"]["conditions"] = current_conditions.get("conditions")
        filtered_data["current_conditions"]["feels_like"] = current_conditions.get("feels_like")
        filtered_data["current_conditions"]["relative_humidity"] = current_conditions.get("relative_humidity")
        filtered_data["current_conditions"]["station_pressure"] = current_conditions.get("station_pressure")
        filtered_data["current_conditions"]["precip_probability"] = current_conditions.get("precip_probability")
        filtered_data["current_conditions"]["wind_gust"] = current_conditions.get("wind_gust")

    # Filter forecast data (first 4 days)
    if "forecast" in data and "daily" in data["forecast"]:
        for daily_forecast in data["forecast"]["daily"][:4]:  # Only take the first 4 items
            filtered_daily = {
                "day_start_local": daily_forecast.get("day_start_local"),
                "air_temp_high": daily_forecast.get("air_temp_high"),
                "air_temp_low": daily_forecast.get("air_temp_low"),
                "conditions": daily_forecast.get("conditions"),
                "day_num": daily_forecast.get("day_num"),
                "month_num": daily_forecast.get("month_num"),
                "precip_probability": daily_forecast.get("precip_probability"),
                "precip_type": daily_forecast.get("precip_type"),
                "icon": daily_forecast.get("icon"),
                "precip_icon": daily_forecast.get("precip_icon")

            }
            filtered_data["forecast"]["daily"].append(filtered_daily)

    return filtered_data


def transform_data_parquet(data: dict, perf, perf_chart):
    """Filters and restructures JSON to keep only specified fields."""
    filtered_data = {"holdings": [], "performance": {}, "chart": []}

    if "holdings" in data:
        for holding in data["holdings"]:
            asset_type = holding.get("assetType", "").lower()
            if asset_type not in ["security", "crypto"]:
                continue
            is_sold = holding.get("position", {}).get("isSold")
            shares = holding.get("position", {}).get("shares")
            if is_sold or shares == 0:
                continue
            filtered_holding = {
                "assetType": asset_type,
                "currency": holding.get("currency"),
                "id": holding.get("asset", {}).get("identifier"),
                "name": holding.get("sharedAsset", {}).get("name"),
                "priceStart": holding.get("performance", {}).get("priceAtIntervalStart"),
                "valueStart": holding.get("performance", {}).get("purchaseValueForInterval"),
                "priceNow": holding.get("position", {}).get("currentPrice"),
                "valueNow": holding.get("position", {}).get("currentValue"),
                "shares": holding.get("position", {}).get("shares"),
                "perf": get_perf(holding.get("performance", {}), perf)
            }
            filtered_data["holdings"].append(filtered_holding)

    performance_data = data.get("performance", {})
    filtered_data["performance"] = {
        "valueStart": performance_data.get("purchaseValueForInterval"),
        "valueNow": performance_data.get("value"),
    }
    # logger.info(f"Got portfolio perf for {perf}: {get_perf(performance_data, perf)}")
    filtered_data["performance"]["perf"] = get_perf(performance_data, perf)

    if "charts" in data:
        first = True
        for chart in data["charts"]:
            if first:
                # skip first
                first = False
                continue
            filtered_data["chart"].append(get_perf_chart(chart, perf_chart))

    return filtered_data


def get_perf(data, perf):
    return data.get(perf, 0)


def get_perf_chart(data, perf_chart):
    values = data.get("values", {})
    return values.get(perf_chart, 0)


@app.post("/proxy/tempest")
@app.get("/proxy/tempest")
@limiter.limit("5/minute")  # ⏳ Apply rate limit (5 requests per minute per IP)
async def proxy_request_tempest(request: Request):
    """Secure JSON proxy with rate limiting."""
    logger.info(
        f"{datetime.now().isoformat()} Received {request.method} request: {request.url} from {get_remote_address(request)}"
    )

    if request.method == "GET":
        # Extract and validate query parameters
        station_id = request.query_params.get("station_id")
        units_temp = request.query_params.get("units_temp")
        units_wind = request.query_params.get("units_wind")
        units_pressure = request.query_params.get("units_pressure")
        units_precip = request.query_params.get("units_precip")
        units_distance = request.query_params.get("units_distance")
        api_key = request.query_params.get("api_key")

        if not all([station_id, units_temp, units_wind, units_pressure, units_precip, units_distance, api_key]):
            raise HTTPException(status_code=400, detail="Missing required query parameters")

        request_data = WeatherRequest(
            station_id=station_id,
            units_temp=units_temp,
            units_wind=units_wind,
            units_pressure=units_pressure,
            units_precip=units_precip,
            units_distance=units_distance,
            api_key=api_key,
        )
    elif request.method == "POST":  # POST
        try:
            body = await request.json()
            request_data = WeatherRequest(**body)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid JSON body.") from e
    else:
        raise HTTPException(status_code=400, detail="Unsupported request method")

    # Construct API URL and query parameters
    params = {
        "station_id": request_data.station_id,
        "units_temp": request_data.units_temp,
        "units_wind": request_data.units_wind,
        "units_pressure": request_data.units_pressure,
        "units_precip": request_data.units_precip,
        "units_distance": request_data.units_distance,
        "api_key": request_data.api_key,
    }

    # Fetch the data
    raw_data = await fetch_weather_data(WEATHER_API_BASE, params)

    # Transform the data
    return transform_data_tempest(raw_data)

@app.post("/proxy/parquet")
@app.get("/proxy/parquet")
@limiter.limit("5/minute")  # ⏳ Apply rate limit (5 requests per minute per IP)
async def proxy_request_parquet(request: Request):
    """Secure JSON proxy with rate limiting."""
    logger.info(
        f"{datetime.now().isoformat()} Received {request.method} request: {request.url} from {get_remote_address(request)}")
    if request.method == "GET":
        id = request.query_params.get("id")
        timeframe = request.query_params.get("timeframe")
        perf = request.query_params.get("perf")
        perf_chart = request.query_params.get("perfChart")

        if not id or not timeframe or not perf or not perf_chart:
            raise HTTPException(status_code=400,
                                detail="Missing required query parameters")

        request_data = PortfolioRequest(id=id, timeframe=timeframe, perf=perf, perfChart=perf_chart)
    elif request.method == "POST":  # POST
        try:
            body = await request.json()
            request_data = PortfolioRequest(**body)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid JSON body.") from e
    else:
        raise HTTPException(status_code=400, detail="Unsupported")

    # Construct API URL and payload
    url = PARQET_API_BASE
    payload = {
        "portfolioIds": [request_data.id],
        "holdingIds": [],
        "assetTypes": [],
        "timeframe": request_data.timeframe
    }

    # Fetch the data
    raw_data = await fetch_parqet_data(url, payload)

    # logger.info(f"{datetime.now().isoformat()} Received raw data: {len(raw_data)}")
    return transform_data_parquet(raw_data, request_data.perf, request_data.perfChart)

