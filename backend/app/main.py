from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .block_registry import SPECS
from .contracts import BlockExecutionError
from .engine import gpu_status, run_once, validate_graph
from .jobs import manager
from .models import Graph, SimulationRequest

app = FastAPI(title="SignalLab API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "gpu": gpu_status()}


@app.get("/api/blocks")
def blocks():
    return [spec.to_dict() for spec in SPECS]


@app.post("/api/validate")
def validate(graph: Graph):
    return validate_graph(graph)


@app.post("/api/jobs", status_code=202)
def create_job(request: SimulationRequest):
    validation = validate_graph(request.graph)
    if not validation.valid:
        raise HTTPException(422, detail={"message": "; ".join(validation.errors), "node_errors": validation.node_errors})
    return {"job_id": manager.create(request)}


@app.post("/api/run-once")
def execute_once(request: SimulationRequest):
    validation = validate_graph(request.graph)
    if not validation.valid:
        raise HTTPException(422, detail={"message": "; ".join(validation.errors), "node_errors": validation.node_errors})
    try:
        return run_once(request.graph, request.config)
    except BlockExecutionError as exc:
        raise HTTPException(422, detail={
            "message": str(exc),
            "node_errors": {exc.node_id: [exc.reason]},
            "node_id": exc.node_id,
            "node_label": exc.node_label,
        }) from exc
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = manager.get(job_id)
    if not job:
        raise HTTPException(404, detail="Job not found")
    return job


@app.delete("/api/jobs/{job_id}")
def cancel_job(job_id: str):
    if not manager.cancel(job_id):
        raise HTTPException(404, detail="Job not found")
    return {"status": "cancellation_requested"}
