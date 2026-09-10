from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {
        "message": "Cost-Aware Multi-Model Router API",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


