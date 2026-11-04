"""
This file holds the classes for various objects used in this project.
"""
from dataclasses import dataclass
from enum import StrEnum
from time import time_ns, sleep
try:
    import RPi.GPIO as GPIO
except ImportError:
    class DummyGPIO:
        BOARD = "BOARD"
        OUT = "OUT"
        HIGH = 1
        LOW = 0
        IN = "IN"
        PUD_DOWN = "PUD_DOWN"
        PUD_UP = "PUD_UP"
        RISING = "RISING"
        FALLING = "FALLING"
        BOTH = "BOTH"
        @staticmethod
        def input(*args, **kwargs): return 0
        @staticmethod
        def add_event_detect(*args, **kwargs): pass
        @staticmethod
        def setmode(*args, **kwargs): pass
        @staticmethod
        def setup(*args, **kwargs): pass
        @staticmethod
        def output(*args, **kwargs): pass
    GPIO = DummyGPIO()


@dataclass
class InputTimestamp:
    value: int # 0 or 1
    state: bool # Just a different type for the value
    timestamp: int # Nanoseconds since epoch


class GpioState(StrEnum):
    unknown: str = "Unknown"
    high: str = "High"
    low: str = "Low"


class ObsGpio:
    def __init__(self, number: int):
        self.number: int = number
        self.state: GpioState = GpioState.unknown


class ObsGpioOutput(ObsGpio):
    def __init__(self, number: int):
        super().__init__(number)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(number, GPIO.OUT)
        self.state = GpioState.low
        self.pwm_instance = None
        self.pwm_frequency = None
        self.pwm_duty_cycle = None

    def set_state(self, state: GpioState):
        self.state = state
        GPIO.output(self.number, GPIO.HIGH if state == GpioState.high else GPIO.LOW)

    def get_state(self) -> GpioState:
        return self.state

    def configure_pwm(self, frequency: float, duty_cycle: float):
        """
        Sets up PWM on the GPIO output with the specified frequency and duty cycle.
        """
        self.pwm_instance = GPIO.PWM(self.number, frequency)
        self.pwm_frequency = frequency
        self.pwm_duty_cycle = duty_cycle

    def start_pwm(self):
        if self.pwm_instance is not None and self.pwm_frequency is not None and self.pwm_duty_cycle is not None:
            self.pwm_instance.start(self.pwm_duty_cycle)

    def stop_pwm(self):
        if self.pwm_instance is not None:
            self.pwm_instance.stop()

    def pulse(self, duration: float, start_state: GpioState = GpioState.high):
        """
        Pulses the GPIO output high for the specified duration in seconds.
        """
        self.set_state(start_state)
        sleep(duration)
        self.set_state(GpioState.high if start_state == GpioState.low else GpioState.low)


class ObsGpioInput(ObsGpio):

    def __init__(self, number: int, pull_down_active: bool, edge: str = "rising"):
        super().__init__(number)
        self.pull_down: bool = pull_down_active
        self.edge: str = edge
        self.history: list [InputTimestamp] = [] # Initialize history list empty

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(number, GPIO.IN, pull_up_down=GPIO.PUD_DOWN if pull_down_active else GPIO.PUD_UP)
        GPIO.add_event_detect(number, self._map_edge(edge), callback=self.on_change)

    def _map_edge(self, edge: str):
        if edge == "rising":
            return GPIO.RISING
        if edge == "falling":
            return GPIO.FALLING
        return GPIO.BOTH

    def on_change(self, channel):  # Callback function for GPIO event detection
        value = GPIO.input(channel)
        measurement = InputTimestamp(
            value=value,
            state=bool(value),
            timestamp=time_ns(),
        )
        self.history.append(measurement)
        self.state = GpioState.high if measurement.state else GpioState.low

    def clear_history(self):
        """
        Clears the history. Can be useful if you want to measure a frequency and want clean results.
        """
        self.history = []


    def get_last_measurement(self) -> InputTimestamp | None:
        """
        Returns the last measurement if available, otherwise None.
        """
        return self.history[-1] if self.history else None

    def calculate_frequency(self) -> float:
        """
        Calculates the frequency of state changes based on the history.
        Returns the frequency in Hz. If there are not enough measurements, returns 0.0.
        """
        if len(self.history) < 2:
            return 0.0
        time_diffs = [
            (self.history[i].timestamp - self.history[i - 1].timestamp)
            for i in range(1, len(self.history))
        ]
        avg_time_diff_ns = sum(time_diffs) / len(time_diffs)
        avg_time_diff_s = avg_time_diff_ns / 1_000_000_000  # Convert nanoseconds to seconds
        return round(1.0 / avg_time_diff_s, 3) if avg_time_diff_s > 0 else 0.0

    def calculate_duty_cycle(self) -> float:
        """
        Calculates the duty cycle (the fraction of time the GPIO is high) based on the history.
        Returns the duty cycle as a float between 0.0 and 1.0. If there are not enough measurements, returns 0.0.
        """
        if len(self.history) < 2:  # If no changes were made in the history
            return 0.0 if not self.state else 100.0 # Either 100% or 0% depending on the current state
     
        high_time = 0
        for i in range(1, len(self.history)): # Sum up the high time intervals
            if self.history[i - 1].state:
                high_time += self.history[i].timestamp - self.history[i - 1].timestamp
        total_time = self.history[-1].timestamp - self.history[0].timestamp # Get the total time
        duty_cycle = high_time / total_time if total_time > 0 else 0.0
        return round(duty_cycle, 3)
        