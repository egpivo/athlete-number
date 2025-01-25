from fastapi import FastAPI

from athlete_number.routers.ocr import router as ocr_router

app = FastAPI()


@app.get("/")
async def read_main():
    return {"message": "Welcome!"}


app.include_router(ocr_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
