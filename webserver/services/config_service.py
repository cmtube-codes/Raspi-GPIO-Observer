"""Shared configuration logic for GPIO API and web UI."""

from __future__ import annotations

import json

from classes import GpioState, ObsGpioInput, ObsGpioOutput
from rpi_observer import IOs, add_gpio_input, add_gpio_output, remove_gpio
from webserver.schemas import GPIOConfig, GPIOOutputConfig

CONFIG_FILE = "gpio_config.json"


def build_config_snapshot() -> list[dict[str, object]]:
    snapshot: list[dict[str, object]] = []
    for gpio, obs in sorted(IOs.items()):
        if isinstance(obs, ObsGpioInput):
            snapshot.append(
                {
                    "gpio": gpio,
                    "type": "input",
                    "state": "high" if obs.state == GpioState.high else "low",
                    "pull_down": obs.pull_down,
                    "edge": obs.edge,
                }
            )
            continue

        snapshot.append(
            {
                "gpio": gpio,
                "type": "output",
                "state": "high" if obs.state == GpioState.high else "low",
                "pull_down": None,
                "edge": None,
            }
        )
    return snapshot


def ensure_input(config: GPIOConfig) -> dict[str, object]:
    if config.gpio in IOs and isinstance(IOs[config.gpio], ObsGpioOutput):
        return {"error": f"GPIO {config.gpio} is already configured as an output."}

    if config.gpio in IOs:
        remove_gpio(config.gpio)
    add_gpio_input(config.gpio, config.pull_down, config.edge)
    return {
        "message": f"GPIO {config.gpio} configured as input for {config.edge} edges.",
        "gpio": config.gpio,
        "pull_down": config.pull_down,
        "edge": config.edge,
    }


def ensure_output(config: GPIOOutputConfig) -> dict[str, object]:
    if config.gpio in IOs and not isinstance(IOs[config.gpio], ObsGpioOutput):
        return {"error": f"GPIO {config.gpio} is already configured as an input."}

    if config.gpio not in IOs:
        add_gpio_output(config.gpio)
    target_state = GpioState.high if config.state == "high" else GpioState.low
    IOs[config.gpio].set_state(target_state)
    return {
        "message": f"Output GPIO {config.gpio} switched to {config.state}.",
        "gpio": config.gpio,
        "state": config.state,
    }


def delete_config(gpio: int) -> dict[str, str]:
    remove_gpio(gpio)
    return {"message": f"GPIO {gpio} was removed from the observer."}


def save_config() -> dict[str, str]:
    with open(CONFIG_FILE, "w", encoding="utf-8") as config_file:
        json.dump(
            {
                gpio: {
                    "type": "input" if isinstance(obs_gpio, ObsGpioInput) else "output",
                    "pull_down": getattr(obs_gpio, "pull_down", None),
                    "edge": getattr(obs_gpio, "edge", None),
                    "state": "high" if obs_gpio.state == GpioState.high else "low",
                }
                for gpio, obs_gpio in IOs.items()
            },
            config_file,
        )
    return {"message": "Configuration saved successfully."}


def load_config() -> dict[str, str]:
    if IOs:
        return {"error": "Observer is not empty. Please clear the observer before loading configuration."}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        return {"error": "Configuration file not found."}

    for gpio, conf in config.items():
        pin = int(gpio)
        if conf.get("type") == "output":
            ensure_output(GPIOOutputConfig(gpio=pin, state=str(conf.get("state", "low")).lower()))
            continue
        ensure_input(
            GPIOConfig(
                gpio=pin,
                pull_down=bool(conf.get("pull_down", False)),
                edge=str(conf.get("edge", "rising")),
            )
        )
    return {"message": "Configuration loaded successfully."}
