import pandas as pd
from prophet import Prophet
from app.repositories import (
    DatasetRepository,
    ForecastResultRepository,
    SimulationRepository,
)
from app.models import ServerForecastSimulation

class ForecastService:
    pass