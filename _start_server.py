import uvicorn
uvicorn.run("app.api:app", host="127.0.0.1", port=8002, log_level="debug")

