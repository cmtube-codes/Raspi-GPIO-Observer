"""Application entrypoint for Raspi GPIO Observer."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from webserver.routers.api_router import router as api_router
from webserver.routers.web_router import router as web_router


app = FastAPI(
    title="Raspi GPIO Observer",
    description="Web app and API for configuring and observing Raspberry Pi GPIOs.",
    version="1.2.0",
)

app.mount("/static", StaticFiles(directory="webserver/static"), name="static")
app.include_router(web_router)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
