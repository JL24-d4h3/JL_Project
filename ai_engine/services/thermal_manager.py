"""
services/thermal_manager.py — Gestión térmica adaptativa
Monitorea temperatura y ajusta NVPModel + speculative gamma dinámicamente.
Implementación pendiente — esqueleto con interface definida.
Ver ai-search-engine-plan.md §16 y jetson-comparison.md §8 para perfiles completos.
"""
import asyncio
import logging
from ai_engine.config import settings

logger = logging.getLogger(__name__)

# Perfiles de temperatura por plataforma
_PROFILES: dict = {
    "orin_nano_8gb": [
        {"name": "nominal",  "max_temp": 52,  "nvp_mode": 0, "draft_gamma": 4},
        {"name": "warm",     "max_temp": 65,  "nvp_mode": 1, "draft_gamma": 3},
        {"name": "critical", "max_temp": 999, "nvp_mode": 2, "draft_gamma": 2},
    ],
    "orin_nx_8gb": [
        {"name": "nominal",  "max_temp": 55,  "nvp_mode": 3, "draft_gamma": 4},
        {"name": "warm",     "max_temp": 68,  "nvp_mode": 2, "draft_gamma": 3},
        {"name": "hot",      "max_temp": 78,  "nvp_mode": 1, "draft_gamma": 2},
        {"name": "critical", "max_temp": 999, "nvp_mode": 0, "draft_gamma": 2},
    ],
    "orin_nx_16gb": [
        {"name": "nominal",  "max_temp": 55,  "nvp_mode": 4, "draft_gamma": 5},
        {"name": "warm",     "max_temp": 68,  "nvp_mode": 3, "draft_gamma": 4},
        {"name": "hot",      "max_temp": 78,  "nvp_mode": 2, "draft_gamma": 3},
        {"name": "critical", "max_temp": 999, "nvp_mode": 1, "draft_gamma": 2},
    ],
    "agx_orin_32gb": [
        {"name": "nominal",  "max_temp": 55,  "nvp_mode": 5, "draft_gamma": 6},
        {"name": "warm",     "max_temp": 68,  "nvp_mode": 4, "draft_gamma": 5},
        {"name": "hot",      "max_temp": 78,  "nvp_mode": 3, "draft_gamma": 4},
        {"name": "very_hot", "max_temp": 85,  "nvp_mode": 2, "draft_gamma": 3},
        {"name": "critical", "max_temp": 999, "nvp_mode": 1, "draft_gamma": 2},
    ],
}


class ThermalManager:
    def __init__(self):
        self.current_profile: str = "nominal"
        self.current_gamma:   int = settings.SPECULATIVE_GAMMA
        self._task:           asyncio.Task | None = None
        self._profiles = _PROFILES.get(settings.THERMAL_PROFILE, _PROFILES["orin_nx_16gb"])

    async def start(self):
        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        if self._task:
            self._task.cancel()

    def _read_temp_celsius(self) -> float:
        """Lee temperatura de la zona térmica de mayor temperatura."""
        import pathlib
        max_temp = 0.0
        for zone in pathlib.Path("/sys/class/thermal").glob("thermal_zone*/temp"):
            try:
                t = int(zone.read_text().strip()) / 1000.0
                max_temp = max(max_temp, t)
            except (OSError, ValueError):
                pass
        return max_temp

    async def _monitor_loop(self):
        while True:
            try:
                temp = self._read_temp_celsius()
                for profile in self._profiles:
                    if temp < profile["max_temp"]:
                        if self.current_profile != profile["name"]:
                            self.current_profile = profile["name"]
                            self.current_gamma   = profile["draft_gamma"]
                            logger.warning(
                                "Thermal: %s (%.1f°C) → NVPModel %d, gamma %d",
                                profile["name"], temp,
                                profile["nvp_mode"], profile["draft_gamma"],
                            )
                            # TODO: aplicar nvpmodel -m {nvp_mode} vía subprocess
                        break
            except Exception as exc:
                logger.error("Error en monitor térmico: %s", exc)
            await asyncio.sleep(10)


thermal_manager = ThermalManager()
