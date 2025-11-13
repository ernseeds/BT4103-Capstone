import os, subprocess
import uvicorn
import threading
import time
from pathlib import Path

def start_vue():
    # use absolute path so cwd is always correct
    root = Path(__file__).resolve().parent
    frontend_dir = root / "frontend"

    if not frontend_dir.exists():
        print(f"[Vue] ERROR: frontend folder not found at {frontend_dir}")
        return

    print(f"[Vue] starting Vue dev server in {frontend_dir} ...")

    # windows
    try:
        subprocess.run(
            ["npm.cmd", "run", "dev"],
            cwd=str(frontend_dir),
            check=True,
        )
        return
    except FileNotFoundError:
        # mac/linux
        try:
            subprocess.run(
                ["npm", "run", "dev"],
                cwd=str(frontend_dir),
                check=True,
            )
            return
        except FileNotFoundError:
            # shell=True
            try:
                subprocess.run(
                    "npm run dev",
                    cwd=str(frontend_dir),
                    shell=True,
                    check=True,
                )
                return
            except Exception as e:
                print(f"[Vue] ERROR: could not run npm: {e}")
        except subprocess.CalledProcessError as e:
            print(f"[Vue] ERROR: npm run dev failed with exit code {e.returncode}")
    except subprocess.CalledProcessError as e:
        print(f"[Vue] ERROR: npm run dev failed with exit code {e.returncode}")


def start_fastapi():
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)

# ----------- I think the code below works to replace start_fastapi()
# SECRET_NAME = "GCP_SA_JSON"
# APP_TARGET  = "backend.app:app"   # change if your app path is different
# HOST, PORT  = "0.0.0.0", 8000
# RELOAD      = True

# def _ensure_secret():
#     # Skip if already provided by your shell/CI
#     if os.environ.get(SECRET_NAME):
#         return
#     try:
#         # Requires: gcloud installed + Secret Manager access
#         val = subprocess.check_output(
#             ["gcloud", "secrets", "versions", "access", "latest", f"--secret={SECRET_NAME}"],
#             text=True
#         ).strip()
#         if val:
#             os.environ[SECRET_NAME] = val
#             print(f"[ok] Loaded {SECRET_NAME} from Secret Manager")
#     except Exception as e:
#         print(f"[warn] Could not load {SECRET_NAME} via gcloud ({e}). "
#               f"Proceeding without it. Set {SECRET_NAME} in your env if required.")

# def start_fastapi():
#     # run from this file's folder (optional)
#     os.chdir(Path(__file__).resolve().parent)
#     _ensure_secret()
#     uvicorn.run(APP_TARGET, host=HOST, port=PORT, reload=RELOAD)

if __name__ == "__main__":
    print("")
    print("Starting frontend (Vue) on http://localhost:8080/ ...")
    t = threading.Thread(target=start_vue, daemon=True)
    t.start()

    time.sleep(2)

    print("Starting backend (FastAPI) on http://localhost:8000/ ...")
    start_fastapi()