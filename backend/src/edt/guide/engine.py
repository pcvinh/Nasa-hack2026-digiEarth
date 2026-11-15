"""Rules-based Detective Guide: suggests variables and whitelisted actions; no numbers."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from edt.catalogue import variables
from edt.regions.select import presets

RULES_PATH = Path(__file__).with_name("rules.yaml")
MAX_SUGGESTIONS = 3


@lru_cache
def rules() -> dict:
    return yaml.safe_load(RULES_PATH.read_text())


def _keyword_hits(message: str) -> list[str]:
    words = set(re.findall(r"[a-z]+", message.lower()))
    hits = []
    for vid, kws in rules()["keywords"].items():
        if words & set(kws):
            hits.append(vid)
    return hits


def chat(message: str, region_id: str | None, variable_id: str | None, topic: str | None) -> dict:
    r = rules()
    names = {vid: v["name"] for vid, v in variables().items()}
    region = presets().get(region_id) if region_id else None

    for u in r["unsupported"]:
        if re.search(u["pattern"], message, flags=re.IGNORECASE):
            return _response(u["reply"], _region_suggestions(region)[:2], region, names, run=False)

    if topic == "air_quality" or re.search(r"\b(air quality|pollution|smog|no2)\b", message, re.I):
        return _response(
            r["airQualityReply"], _region_suggestions(region)[:2], region, names, run=False
        )

    suggestions: list[dict] = []
    seen: set[str] = set()

    def add(vid: str, reason: str) -> None:
        if vid in names and vid not in seen and len(suggestions) < MAX_SUGGESTIONS:
            seen.add(vid)
            suggestions.append({"variableId": vid, "reason": reason})

    for vid in _keyword_hits(message):
        add(vid, f"Your question mentions something {names[vid].lower()} can show.")
    if topic:
        for vid in r["topics"].get(topic, []):
            add(vid, f"{names[vid]} is a {topic} variable.")
    if variable_id and variable_id in names and not suggestions:
        add(variable_id, f"You are already looking at {names[variable_id].lower()}.")
    for s in _region_suggestions(region):
        add(s["variableId"], s["reason"])

    where = f" for {region['name']}" if region else ""
    if suggestions:
        first = names[suggestions[0]["variableId"]].lower()
        reply = (
            f"Good detective question. Start with {first}{where}: run the analysis to see "
            "the time series, the trend and whether it is statistically significant."
        )
    else:
        reply = "Pick a place on the globe or a preset region, then choose a variable to explore."
    return _response(reply, suggestions, region, names, run=True)


def _region_suggestions(region: dict | None) -> list[dict]:
    rtype = region["regionType"] if region else "other"
    return [dict(s) for s in rules()["regionTypes"].get(rtype, rules()["regionTypes"]["other"])]


def _response(
    reply: str, suggestions: list[dict], region: dict | None, names: dict, run: bool
) -> dict:
    actions: list[dict] = []
    if suggestions:
        vid = suggestions[0]["variableId"]
        actions.append({"type": "select_variable", "payload": {"variableId": vid}})
        if region:
            actions.append({"type": "select_region", "payload": {"presetId": region["id"]}})
            if run:
                actions.append(
                    {
                        "type": "run_analysis",
                        "payload": {"variableId": vid, "region": {"presetId": region["id"]}},
                    }
                )
        actions.append({"type": "show_trend_map", "payload": {"variableId": vid}})
    return {"reply": reply, "suggestions": suggestions, "actions": actions, "mode": "rules"}
