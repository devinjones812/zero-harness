from zero_harness import jobs

SCHEMA = {
    "type": "function",
    "name": "job",
    "description": (
        "Check output of, or kill, a background job started with bash background=true. "
        "You get a [background] message automatically when a job finishes."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "job_id": {"type": "integer"},
            "action": {"type": "string", "enum": ["status", "kill"]},
        },
        "required": ["job_id", "action"],
    },
}


def run(job_id: int, action: str) -> str:
    return jobs.status(job_id) if action == "status" else jobs.kill(job_id)
