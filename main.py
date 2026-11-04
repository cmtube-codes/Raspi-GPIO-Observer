"""Main API and web dashboard for Raspi GPIO Observer."""

from __future__ import annotations

import json
from html import escape
from typing import Literal

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from classes import GpioState, ObsGpioInput, ObsGpioOutput
from rpi_observer import IOs, add_gpio_input, add_gpio_output, remove_gpio


CONFIG_FILE = "gpio_config.json"


class GPIOConfig(BaseModel):
    gpio: int = Field(..., ge=0, le=40)
    pull_down: bool = True
    edge: Literal["rising", "falling", "both"] = "rising"


class GPIOOutputConfig(BaseModel):
    gpio: int = Field(..., ge=0, le=40)
    state: Literal["high", "low"] = "low"


app = FastAPI(
    title="Raspi GPIO Observer",
    description="Monitor GPIO events, inspect GPIO status, and manage configurations.",
    version="1.1.0",
)

ENDPOINTS: list[str] = [
    "GET /",
    "GET /help",
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


def _build_config_snapshot() -> list[dict[str, object]]:
    snapshot: list[dict[str, object]] = []
    for gpio, obs in sorted(IOs.items()):
        if isinstance(obs, ObsGpioInput):
            snapshot.append(
                {
                    "gpio": gpio,
                    "type": "input",
                    "state": str(obs.state).lower(),
                    "pull_down": obs.pull_down,
                    "edge": obs.edge,
                }
            )
            continue

        output_state = "high" if obs.state == GpioState.high else "low"
        snapshot.append(
            {
                "gpio": gpio,
                "type": "output",
                "state": output_state,
                "pull_down": None,
                "edge": None,
            }
        )
    return snapshot


def _render_dashboard_html(message: str | None = None) -> str:
    rows = []
    for item in _build_config_snapshot():
        edge_value = item["edge"] if item["edge"] is not None else "-"
        pull_value = item["pull_down"] if item["pull_down"] is not None else "-"
        rows.append(
            f"""
            <tr>
              <td>{item["gpio"]}</td>
              <td>{escape(str(item["type"]))}</td>
              <td>{escape(str(item["state"]))}</td>
              <td>{escape(str(pull_value))}</td>
              <td>{escape(str(edge_value))}</td>
              <td>
                <form action="/dashboard/delete/{item["gpio"]}" method="post">
                  <button type="submit">Entfernen</button>
                </form>
              </td>
            </tr>
            """
        )

    table_body = "".join(rows) if rows else "<tr><td colspan='6'>Noch keine GPIOs konfiguriert.</td></tr>"
    message_box = f"<div class='message'>{escape(message)}</div>" if message else ""

    return f"""
    <!doctype html>
    <html lang="de">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Raspi GPIO Observer Dashboard</title>
        <style>
          body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 0;
            background: #f4f7fb;
            color: #1f2937;
          }}
          .container {{
            max-width: 1100px;
            margin: 1.5rem auto;
            padding: 0 1rem;
          }}
          .card {{
            background: white;
            border-radius: 14px;
            padding: 1rem 1.2rem;
            box-shadow: 0 8px 22px rgba(0,0,0,0.06);
            margin-bottom: 1rem;
          }}
          h1, h2 {{ margin: 0 0 .7rem 0; }}
          .forms {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1rem;
          }}
          form {{ display: grid; gap: .5rem; }}
          label {{ font-weight: 600; }}
          input, select, button {{
            font: inherit;
            padding: .55rem .65rem;
            border-radius: 8px;
            border: 1px solid #d1d5db;
          }}
          button {{
            background: #2563eb;
            color: white;
            border: none;
            cursor: pointer;
          }}
          button:hover {{ background: #1d4ed8; }}
          table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: .7rem;
          }}
          th, td {{
            text-align: left;
            padding: .6rem;
            border-bottom: 1px solid #e5e7eb;
          }}
          .message {{
            background: #dcfce7;
            color: #14532d;
            border: 1px solid #86efac;
            border-radius: 8px;
            padding: .7rem .8rem;
            margin-bottom: .9rem;
          }}
          .secondary-actions {{
            display: flex;
            gap: .5rem;
            flex-wrap: wrap;
          }}
          .secondary-actions form {{ display: inline; }}
        </style>
      </head>
      <body>
        <main class="container">
          <section class="card">
            <h1>Raspi GPIO Observer</h1>
            <p>Hier kannst du die aktuelle Konfiguration sehen und neue GPIO-Konfigurationen anlegen.</p>
            {message_box}
          </section>

          <section class="card">
            <h2>Aktuelle Konfiguration</h2>
            <table>
              <thead>
                <tr>
                  <th>GPIO</th>
                  <th>Typ</th>
                  <th>Status</th>
                  <th>Pull-Down</th>
                  <th>Edge</th>
                  <th>Aktion</th>
                </tr>
              </thead>
              <tbody>
                {table_body}
              </tbody>
            </table>
          </section>

          <section class="card forms">
            <div>
              <h2>Input hinzufügen</h2>
              <form action="/dashboard/input" method="post">
                <label for="input-gpio">GPIO (0-40)</label>
                <input id="input-gpio" name="gpio" type="number" min="0" max="40" required>
                <label for="input-edge">Edge</label>
                <select id="input-edge" name="edge">
                  <option value="rising">rising</option>
                  <option value="falling">falling</option>
                  <option value="both">both</option>
                </select>
                <label>
                  <input name="pull_down" type="checkbox" value="true" checked>
                  Pull-Down aktiv
                </label>
                <button type="submit">Input speichern</button>
              </form>
            </div>

            <div>
              <h2>Output setzen</h2>
              <form action="/dashboard/output" method="post">
                <label for="output-gpio">GPIO (0-40)</label>
                <input id="output-gpio" name="gpio" type="number" min="0" max="40" required>
                <label for="output-state">Zielzustand</label>
                <select id="output-state" name="state">
                  <option value="low">low</option>
                  <option value="high">high</option>
                </select>
                <button type="submit">Output speichern</button>
              </form>
            </div>
          </section>

          <section class="card">
            <h2>Konfiguration persistieren</h2>
            <div class="secondary-actions">
              <form action="/dashboard/save" method="post"><button type="submit">Konfiguration speichern</button></form>
              <form action="/dashboard/load" method="post"><button type="submit">Konfiguration laden</button></form>
            </div>
          </section>
        </main>
      </body>
    </html>
    """


@app.get("/")
def read_root():
    return {"message": "Raspi GPIO Observer is running.", "endpoints": ENDPOINTS}


@app.get("/help")
def read_help():
    return {
        "help": "Use GET /dashboard for the web UI or /config + /input + /output for API usage.",
        "examples": {
            "input": {"gpio": 17, "pull_down": True, "edge": "rising"},
            "output": {"gpio": 18, "state": "high"},
        },
    }


@app.get("/dashboard", response_class=HTMLResponse)
def read_dashboard(message: str | None = None):
    return _render_dashboard_html(message)


@app.post("/dashboard/input")
def create_input_from_dashboard(
    gpio: int = Form(...),
    edge: Literal["rising", "falling", "both"] = Form("rising"),
    pull_down: str | None = Form(None),
):
    add_gpio_input(gpio, pull_down == "true", edge)
    return RedirectResponse(url="/dashboard?message=Input+gespeichert", status_code=303)


@app.post("/dashboard/output")
def create_output_from_dashboard(
    gpio: int = Form(...),
    state: Literal["high", "low"] = Form("low"),
):
    if gpio not in IOs:
        add_gpio_output(gpio)
    if isinstance(IOs.get(gpio), ObsGpioOutput):
        IOs[gpio].set_state(GpioState.high if state == "high" else GpioState.low)
    return RedirectResponse(url="/dashboard?message=Output+gespeichert", status_code=303)


@app.post("/dashboard/delete/{gpio}")
def delete_from_dashboard(gpio: int):
    remove_gpio(gpio)
    return RedirectResponse(url="/dashboard?message=GPIO+entfernt", status_code=303)


@app.post("/dashboard/save")
def save_from_dashboard():
    save_config()
    return RedirectResponse(url="/dashboard?message=Konfiguration+gespeichert", status_code=303)


@app.post("/dashboard/load")
def load_from_dashboard():
    result = load_config()
    message = result.get("message", result.get("error", "Konfiguration geladen"))
    return RedirectResponse(url=f"/dashboard?message={escape(str(message)).replace(' ', '+')}", status_code=303)


@app.get("/config")
def read_config():
    return {"configurations": _build_config_snapshot()}


@app.post("/config")
def add_input_legacy(config: GPIOConfig):
    add_gpio_input(config.gpio, config.pull_down, config.edge)
    return {
        "message": f"GPIO {config.gpio} configured as input for {config.edge} edges.",
        "gpio": config.gpio,
        "pull_down": config.pull_down,
        "edge": config.edge,
    }


@app.delete("/config/{gpio}")
def delete_legacy(gpio: int):
    remove_gpio(gpio)
    return {"message": f"GPIO {gpio} was removed from the observer."}


@app.post("/input")
def add_input_gpio(config: GPIOConfig):
    return add_input_legacy(config)


@app.delete("/input/{gpio}")
def remove_input_gpio(gpio: int):
    if gpio not in IOs or not isinstance(IOs[gpio], ObsGpioInput):
        return {"message": f"GPIO {gpio} is not configured as an input."}
    remove_gpio(gpio)
    return {"message": f"Input GPIO {gpio} was removed from the observer."}


@app.get("/output")
def read_output_gpio():
    return {
        gpio: {"state": obs.state}
        for gpio, obs in IOs.items()
        if isinstance(obs, ObsGpioOutput)
    }


@app.post("/output")
def set_output_gpio(config: GPIOOutputConfig):
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


@app.post("/save-config")
def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as config_file:
        json.dump(
            {
                gpio: {
                    "type": "input" if isinstance(obs_gpio, ObsGpioInput) else "output",
                    "pull_down": getattr(obs_gpio, "pull_down", None),
                    "edge": getattr(obs_gpio, "edge", None),
                    "state": str(obs_gpio.state).lower(),
                }
                for gpio, obs_gpio in IOs.items()
            },
            config_file,
        )
    return {"message": "Configuration saved successfully."}


@app.post("/load-config")
def load_config():
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
            add_gpio_output(pin)
            state = conf.get("state", "low")
            IOs[pin].set_state(GpioState.high if str(state).lower() == "high" else GpioState.low)
        else:
            add_gpio_input(pin, conf.get("pull_down", False), conf.get("edge", "rising"))
    return {"message": "Configuration loaded successfully."}


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
