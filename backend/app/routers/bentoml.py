import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import asyncssh
import socket
from app.database import get_db
from app.models import BentoMLConnection, VM
from app.schemas import BentoMLDeployRequest
from app.security import get_current_user

router = APIRouter()

@router.get("")
async def get_bentoml_connections(db: Session = Depends(get_db)):
    return db.query(BentoMLConnection).all()

@router.post("/{conn_id}/deploy")
async def deploy_service(
    conn_id: int, 
    body: BentoMLDeployRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    bentoml_conn = db.query(BentoMLConnection).filter(BentoMLConnection.id == conn_id).first()
    if not bentoml_conn:
        raise HTTPException(status_code=404, detail="BentoML Connection not found")

    vm = db.query(VM).filter(VM.id == bentoml_conn.vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")

    connect_kwargs = {
        "host": vm.host,
        "port": vm.port,
        "username": vm.username,
        "password": vm.password,
        "known_hosts": None
    }

    # Debug: Check if port is open before connecting
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            if s.connect_ex((vm.host, vm.port)) != 0:
                print(f"DEBUG: Host {vm.host}:{vm.port} is not reachable")
    except: pass

    try:
        async with asyncssh.connect(**connect_kwargs) as conn:
            print("DEBUG: SSH Connected. Checking for BentoML...")
            
            # 1. Try your specific absolute path first
            aladdin_path = "/data/data/com.termux/files/home/ai-gateway/ai-automation/services/aggregator/agents/.venv_ubuntu/bin/bentoml"
            check = await conn.run(f"{aladdin_path} --version", timeout=10)
            
            bentoml_bin = "bentoml"
            venv_prefix = ""

            if check.exit_status == 0:
                print(f"DEBUG: BentoML found at {aladdin_path}")
                bentoml_bin = aladdin_path
            else:
                print(f"DEBUG: Absolute path check failed with status {check.exit_status}. Error: {check.stderr}")
                # 2. Try default venv
                venv_prefix = "source ~/.venv/bin/activate 2>/dev/null || source ~/venv/bin/activate 2>/dev/null; "
                check = await conn.run(f"{venv_prefix}bentoml --version", timeout=10)
                
                if check.exit_status != 0:
                    print("DEBUG: BentoML not found, installing...")
                    await conn.run("pkg install -y clang python-dev make libffi-dev openssl-dev || true", timeout=60)
                    install = await conn.run(
                        "pip install bentoml --break-system-packages || pip3 install bentoml --break-system-packages", 
                        timeout=600
                    )
                    if install.exit_status != 0:
                        return {"status": "error", "message": "Failed to install BentoML"}

            # 3. Cleanup and Start
            await conn.run("pkg install -y lsof || apt-get install -y lsof", timeout=30)
            await conn.run(f"kill $(lsof -t -i :{body.port}) 2>/dev/null || true", timeout=5)

            print(f"DEBUG: Starting BentoML serve {body.service_name}")
            start_cmd = (
                f"nohup bash -c '{venv_prefix}{bentoml_bin} serve {body.service_name} "
                f"--host 0.0.0.0 --port {body.port}' "
                f"> /tmp/bentoml_{body.port}.log 2>&1 &"
            )
            await conn.run(start_cmd, timeout=10)

            # Update DB
            bentoml_conn.endpoint_url = f"http://{vm.host}:{body.port}"
            bentoml_conn.status = "deployed"
            await db.commit()
            
            return {"status": "success", "message": f"Deployed to {bentoml_conn.endpoint_url}"}

    except Exception as e:
        print(f"DEBUG: Deploy error: {str(e)}")
        return {"status": "error", "message": str(e)}
