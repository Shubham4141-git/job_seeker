from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import shutil

from ..profile_manager import list_profiles, get_paths, create_profile, load_recipient_email
from ..preference_extractor import load_preferences
from ..utils import load_json

router = APIRouter(tags=["profiles"])


class CreateProfileRequest(BaseModel):
    name: str


@router.get("/profiles")
def get_profiles():
    names = list_profiles()
    result = []
    for name in names:
        paths = get_paths(name)
        result.append({
            "name": name,
            "has_resume": paths.resume_path is not None,
            "has_prefs": paths.preferences_path.exists(),
            "has_email": paths.config_path.exists(),
            "recipient_email": load_recipient_email(name),
        })
    return {"profiles": result}


@router.post("/profiles")
def create_new_profile(req: CreateProfileRequest):
    name = req.name.strip().replace(" ", "_")
    if not name:
        raise HTTPException(status_code=400, detail="Profile name cannot be empty")
    if name in list_profiles():
        raise HTTPException(status_code=409, detail=f"Profile '{name}' already exists")
    paths = create_profile(name)
    return {"name": name, "dir": str(paths.dir)}


@router.get("/profiles/{name}")
def get_profile(name: str):
    paths = get_paths(name)
    if not paths.dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")
    return {
        "name": name,
        "has_resume": paths.resume_path is not None,
        "has_prefs": paths.preferences_path.exists(),
        "has_email": paths.config_path.exists(),
        "recipient_email": load_recipient_email(name),
        "profile": load_json(paths.parsed_resume_path) if paths.parsed_resume_path.exists() else None,
        "preferences": load_preferences(str(paths.preferences_path)),
    }


@router.delete("/profiles/{name}")
def delete_profile(name: str):
    paths = get_paths(name)
    if not paths.dir.exists():
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")
    shutil.rmtree(paths.dir)
    return {"ok": True}
