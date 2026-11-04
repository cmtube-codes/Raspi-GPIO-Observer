"""This is the main file for the Raspi-GPIO-Observer project."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from classes import GpioState, ObsGpioInput, ObsGpioOutput
from rpi_observer import IOs, add_gpio_input, add_gpio_output, remove_gpio


class GPIOConfig(BaseModel):
    gpio: int = Field(..., ge=0, le=40)
    pull_down: bool = True
    edge: Literal["rising", "falling", "both"] = "rising"


class GPIOOutputConfig(BaseModel):
    gpio: int = Field(..., ge=0, le=40)
    state: Literal["high", "low"] = "low"


app = FastAPI(
    title="Raspi GPIO Observer",
    description="Monitor GPIO events and inspect signal history via a lightweight REST API.",
    version="1.0.0",
)

ENDPOINTS: list[str] = [
    "GET /",
    "GET /help",
    "POST /input",
    "DELETE /input/{gpio}",
    "POST /output",
    "DELETE /output/{gpio}",
    "PUT /output/{gpio}",
    "GET /status",
    "GET /status/{gpio}",
    "GET /history/{gpio}",
    "GET /freq/{gpio}",
    "GET /duty/{gpio}",
    "POST /save-config",
    "POST /load-config",
    "GET /config (legacy)",
    "POST /config (legacy)",
    "DELETE /config/{gpio} (legacy)",
]


@app.get("/")
def read_root():
    return {
        "message": "Raspi GPIO Observer is running.",
        "endpoints": ENDPOINTS,
    }


@app.get("/help")
def read_help():
    return {
        "help": "Use GET /config for input GPIOs and POST /output for output GPIOs.",
        "examples": {
            "input": {"gpio": 17, "pull_down": True, "edge": "rising"},
            "output": {"gpio": 18, "state": "high"},
        },
    }


# region Input GPIO configuration

@app.get("/input/help")
def read_input_help():
    return {
        "message": "Input GPIO configuration endpoints.",
        "add_input": "POST /input",
        "remove_input": "DELETE /input/{gpio}",
        "fields": {
            "gpio": "GPIO number on the board",
            "pull_down": "True for pull-down, False for pull-up",
            "edge": "One of: rising, falling, both",
        },
        "example": {
            "gpio": 17,
            "pull_down": True,
            "edge": "rising",
        },
    }


@app.post("/input")
def add_input_gpio(config: GPIOConfig):
    add_gpio_input(config.gpio, config.pull_down, config.edge)
    return {
        "message": f"Input GPIO {config.gpio} configured for {config.edge} edges.",
        "gpio": config.gpio,
        "pull_down": config.pull_down,
        "edge": config.edge,
    }


@app.delete("/input/{gpio}")
def remove_input_gpio(gpio: int):
    if gpio not in IOs or not isinstance(IOs[gpio], ObsGpioInput):
        return {"message": f"GPIO {gpio} is not configured as an input."}
    remove_gpio(gpio)
    return {"message": f"Input GPIO {gpio} was removed from the observer."}

# endregion Input GPIO configuration

# region Output GPIO configuration

@app.get("/output")
def read_output_gpio():
    return {
        gpio: {"state": obs.state}
        for gpio, obs in IOs.items()
        if isinstance(obs, ObsGpioOutput)
    }


@app.post("/output")
def set_output_gpio(config: GPIOOutputConfig):
    if config.gpio in IOs:
        if not isinstance(IOs[config.gpio], ObsGpioOutput):
            return {"error": f"GPIO {config.gpio} is already configured as an input."}
    else:
        add_gpio_output(config.gpio)

    target_state = GpioState.high if config.state == "high" else GpioState.low
    IOs[config.gpio].set_state(target_state)
    return {
        "message": f"Output GPIO {config.gpio} switched to {config.state}.",
        "gpio": config.gpio,
        "state": config.state,
    }


@app.put("/output/{gpio}")
def update_output_gpio(gpio: int, config: GPIOOutputConfig):
    if gpio not in IOs:
        add_gpio_output(gpio)
    if not isinstance(IOs[gpio], ObsGpioOutput):
        return {"error": f"GPIO {gpio} is not an output GPIO."}

    target_state = GpioState.high if config.state == "high" else GpioState.low
    IOs[gpio].set_state(target_state)
    return {"message": f"Output GPIO {gpio} switched to {config.state}.", "gpio": gpio, "state": config.state}


@app.delete("/output/{gpio}")
def delete_output_gpio(gpio: int):
    if gpio not in IOs or not isinstance(IOs[gpio], ObsGpioOutput):
        return {"message": f"GPIO {gpio} is not configured as an output."}
    remove_gpio(gpio)
    return {"message": f"Output GPIO {gpio} was removed from the observer."}

# endregion Output GPIO configuration


@app.post("/save-config")
def save_config():
    import json

    with open("gpio_config.json", "w") as f:
        json.dump(
            {
                gpio: {
                    "type": "input" if isinstance(obs_gpio, ObsGpioInput) else "output",
                    "pull_down": getattr(obs_gpio, "pull_down", None),
                    "edge": getattr(obs_gpio, "edge", None),
                    "state": str(obs_gpio.state),
                }
                for gpio, obs_gpio in IOs.items()
            },
            f,
        )
    return {"message": "Configuration saved successfully."}


@app.post("/load-config")
def load_config():
    if IOs:
        return {"error": "Observer is not empty. Please clear the observer before loading configuration."}

    import json

    try:
        with open("gpio_config.json", "r") as f:
            config = json.load(f)
        for gpio, conf in config.items():
            pin = int(gpio)
            if conf.get("type") == "output":
                add_gpio_output(pin)
                state = conf.get("state", "low")
                IOs[pin].set_state(GpioState.high if state.lower() == "high" else GpioState.low)
            else:
                add_gpio_input(pin, conf.get("pull_down", False), conf.get("edge", "rising"))
        return {"message": "Configuration loaded successfully."}
    except FileNotFoundError:
        return {"error": "Configuration file not found."}

#region Inputs

@app.delete("/input/{gpio}")
def delete_input(gpio: int):
    if gpio not in IOs or not isinstance(IOs[gpio], ObsGpioInput):
        return {"message": f"GPIO {gpio} is not configured as an input."}
    remove_gpio(gpio)
    return {"message": f"GPIO {gpio} was removed from the observer."}


@app.get("/input/all-states")
def read_status():
    return {gpio: {"state": obs_gpio.state} for gpio, obs_gpio in IOs.items()}


@app.get("/input/{gpio}/status")
def read_gpio_status(gpio: int):
    if gpio not in IOs:
        return {"error": f"GPIO {gpio} is not being observed."}
    return {"state": IOs[gpio].state}


@app.get("/input/{gpio}/history/")
def read_gpio_history(gpio: int):
    if gpio not in IOs:
        return {"error": f"GPIO {gpio} is not being observed."}
    if isinstance(IOs[gpio], ObsGpioInput):
        return {"history": IOs[gpio].history}
    return {"error": "GPIO is an output and does not have a tracked history."}


@app.get("/input/{gpio}/freq/")
def read_gpio_frequency(gpio: int):
    if gpio not in IOs:
        return {"error": f"GPIO {gpio} is not being observed."}
    if isinstance(IOs[gpio], ObsGpioInput):
        return {"frequency": IOs[gpio].calculate_frequency()}
    return {"error": "GPIO is an output and does not have a trackable frequency."}


@app.get("/input/{gpio}/duty/")
def read_gpio_duty_cycle(gpio: int):
    if gpio not in IOs:
        return {"error": f"GPIO {gpio} is not being observed."}
    if isinstance(IOs[gpio], ObsGpioInput):
        return {"duty_cycle": IOs[gpio].calculate_duty_cycle()}
    return {"error": "GPIO is an output and does not have a trackable duty cycle."}

#endregion Inputs

#region IF __NAME__ == __MAIN__
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
#endregion IF __NAME__ == __MAIN__