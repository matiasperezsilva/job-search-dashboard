from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
PROFILE_EXAMPLE = ROOT / 'config' / 'perfil.example.json'


def perfil_demo():
    with PROFILE_EXAMPLE.open(encoding='utf-8') as f:
        return json.load(f)
