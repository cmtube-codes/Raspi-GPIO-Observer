"""REST API routes for GPIO observer."""

from fastapi import APIRouter

from classes import ObsGpioInput, ObsGpioOutput
from rpi_observer import IOs
from webserver.schemas import GPIOConfig, GPIOOutputConfig
from webserver.services.config_service import (
    build_config_snapshot,
    delete_config,
    ensure_input,
    ensure_output,
    load_config,
    save_config,
)

router = APIRouter()

ENDPOINTS: list[str] = [
    "GET /",
    "GET /dashboard",
    "GET /config",
    "POST /config",
    "DELETE /config/{gpio}",
    "POST /input",
    "DELETE /input/{gpio}",
    "POST /output",
    "PUT /output/{gpio}",
    "DELETE /output/{gpio}",
    "POST /save-config",
    "POST /load-config",
]


@router.get("/api")
def read_api_root():
    return {"message": "Raspi GPIO Observer API is running.", "endpoints": ENDPOINTS}


@router.get("/help")
def read_help():
    return {
        "help": "Use /dashboard for web UI or /config + /input + /output for API usage.",
        "examples": {
            "input": {"gpio": 17, "pull_down": True, "edge": "rising"},
            "output": {"gpio": 18, "state": "high"},
        },
    }


@router.get("/config")
def read_config():
    return {"configurations": build_config_snapshot()}


@router.post("/config")
def add_input_legacy(config: GPIOConfig):
    return ensure_input(config)


@router.delete("/config/{gpio}")
def delete_legacy(gpio: int):
    return delete_config(gpio)


@router.post("/input")
def add_input_gpio(config: GPIOConfig):
    return ensure_input(config)


@router.delete("/input/{gpio}")
def remove_input_gpio(gpio: int):
    if gpio not in IOs or not isinstance(IOs[gpio], ObsGpioInput):
        return {"message": f"GPIO {gpio} is not configured as an input."}
    return delete_config(gpio)


@router.get("/output")
def read_output_gpio():
    return {
        gpio: {"state": obs.state}
        for gpio, obs in IOs.items()
        if isinstance(obs, ObsGpioOutput)
    }


@router.post("/output")
def set_output_gpio(config: GPIOOutputConfig):
    return ensure_output(config)


@router.put("/output/{gpio}")
def update_output_gpio(gpio: int, config: GPIOOutputConfig):
    return ensure_output(GPIOOutputConfig(gpio=gpio, state=config.state))


@router.delete("/output/{gpio}")
def delete_output_gpio(gpio: int):
    if gpio not in IOs or not isinstance(IOs[gpio], ObsGpioOutput):
        return {"message": f"GPIO {gpio} is not configured as an output."}
    return delete_config(gpio)


@router.post("/save-config")
def save_config_route():
    return save_config()


@router.post("/load-config")
def load_config_route():
    return load_config()


@router.get("/input/all-states")
def read_status():
    return {gpio: {"state": obs_gpio.state} for gpio, obs_gpio in IOs.items()}


@router.get("/input/{gpio}/status")
def read_gpio_status(gpio: int):
    if gpio not in IOs:
        return {"error": f"GPIO {gpio} is not being observed."}
    return {"state": IOs[gpio].state}


@router.get("/input/{gpio}/history/")
def read_gpio_history(gpio: int):
    if gpio not in IOs:
        return {"error": f"GPIO {gpio} is not being observed."}
    if isinstance(IOs[gpio], ObsGpioInput):
        return {"history": IOs[gpio].history}
    return {"error": "GPIO is an output and does not have a tracked history."}


@router.get("/input/{gpio}/freq/")
def read_gpio_frequency(gpio: int):
    if gpio not in IOs:
        return {"error": f"GPIO {gpio} is not being observed."}
    if isinstance(IOs[gpio], ObsGpioInput):
        return {"frequency": IOs[gpio].calculate_frequency()}
    return {"error": "GPIO is an output and does not have a trackable frequency."}


@router.get("/input/{gpio}/duty/")
def read_gpio_duty_cycle(gpio: int):
    if gpio not in IOs:
        return {"error": f"GPIO {gpio} is not being observed."}
    if isinstance(IOs[gpio], ObsGpioInput):
        return {"duty_cycle": IOs[gpio].calculate_duty_cycle()}
    return {"error": "GPIO is an output and does not have a trackable duty cycle."}
