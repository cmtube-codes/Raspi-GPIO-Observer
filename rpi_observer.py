"""
This file contains the actual observer. It runs via GPIO interrupt functions. You can configure the observer via the API.
Available configurations are rising/falling/both edge detections.
For each GPIO an object will be created and fed with the current state, a history, timestamps and literally everything you might
want to know about this IO.
"""
from time import time_ns

try:
    import RPi.GPIO as GPIO
except ImportError:  # pragma: no cover - only used on non-RPi machines
    class _FallbackGPIO:
        BOARD = "BOARD"
        IN = "IN"
        OUT = "OUT"
        PUD_UP = "PUD_UP"
        PUD_DOWN = "PUD_DOWN"
        RISING = "RISING"
        FALLING = "FALLING"
        BOTH = "BOTH"
        HIGH = 1
        LOW = 0

        @staticmethod
        def setmode(mode):
            return None

        @staticmethod
        def setup(channel, direction, pull_up_down=None):
            return None

        @staticmethod
        def input(channel):
            return 0

        @staticmethod
        def output(channel, value):
            return None

        @staticmethod
        def add_event_detect(channel, edge, callback=None, bouncetime=None):
            return None

        @staticmethod
        def remove_event_detect(channel):
            return None

    GPIO = _FallbackGPIO()

from classes import ObsGpioInput, ObsGpioOutput, InputTimestamp

GPIO.setmode(GPIO.BOARD)

IOs: dict[int, object] = {}


def add_gpio_input(number: int, pull_down_active: bool, edge: str):
    if number in IOs:
        return
    IOs[number] = ObsGpioInput(number, pull_down_active, edge)


def add_gpio_output(number: int):
    if number in IOs:
        return
    IOs[number] = ObsGpioOutput(number)


def remove_gpio(number: int):
    if number not in IOs:
        return
    if isinstance(IOs[number], ObsGpioInput):
        GPIO.remove_event_detect(number)
    del IOs[number]

