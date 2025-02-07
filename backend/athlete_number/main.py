import os

import uvicorn
from athlete_number.routers.detect_bib_numbers import router as detect_router
from athlete_number.routers.extract_bib_numbers import router as athlete_router
from athlete_number.routers.extract_numbers import router as extract_router
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
app = FastAPI()


@app.get("/")
async def read_main():
    return {"message": "Welcome!"}


app.include_router(extract_router)
app.include_router(detect_router)
app.include_router(athlete_router)


def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5566))
    reload = os.getenv("RELOAD", "TRUE").lower() == "true"

    uvicorn.run("file_translator.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
