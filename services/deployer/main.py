import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("SITE_ROUTER_PORT", 8080))
    uvicorn.run("services.deployer.site_router:app", host="0.0.0.0", port=port, reload=False)
