import uvicorn

if __name__ == "__main__":
    # El 8001 lo usa pami en esta misma máquina.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8002, reload=True)
