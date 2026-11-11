"""Phase 13e: the citizen's Map tab. The map screen only draws what these calls return, so a citizen must get nothing but their own
plots from every one of them. No new endpoint was needed: the map uses GET /plots, GET /construction-alerts and GET /plots/{ulpin}."""
import re

import pytest

ULPIN_LIKE = re.compile(r"\bMH\d{12}\b")
FILTERS = ({}, {"band": "green"}, {"band": "amber"}, {"band": "red"}, {"village": "Hinjewadi"}, {"village": "Baner"},
           {"conflict_type": "boundary_overlap"}, {"conflict_type": "unrecorded_construction"})


@pytest.mark.parametrize("who,other", [("citizen_a", "citizen_b"), ("citizen_b", "citizen_a")])
def test_citizen_map_only_own_plots(anon_client, auth, users, who, other):
    mine = set(users[who]["plots"])
    theirs = set(users[other]["plots"])
    assert mine and theirs and not (mine & theirs)

    # 1. the plot layer, with every filter the map's filter panel can send
    for params in FILTERS:
        response = anon_client.get("/plots", params=params, headers=auth(who))
        assert response.status_code == 200
        shown = {f["properties"]["ulpin"] for f in response.json()["features"]}
        assert shown <= mine, (params, shown - mine)
        assert not (set(ULPIN_LIKE.findall(response.text)) - mine), params   # no other plot id anywhere in the body

    # 2. the SIMULATED construction layer
    response = anon_client.get("/construction-alerts", headers=auth(who))
    assert response.status_code == 200
    assert {f["properties"]["ulpin"] for f in response.json()["features"]} <= mine
    assert not (set(ULPIN_LIKE.findall(response.text)) - mine)

    # 3. the passport that opens inside the card: their own works, somebody else's is "not found"
    for ulpin in mine:
        assert anon_client.get(f"/plots/{ulpin}", headers=auth(who)).status_code == 200
    for ulpin in theirs:
        assert anon_client.get(f"/plots/{ulpin}", headers=auth(who)).status_code == 404

    # 4. the map never asks for staff data, and a citizen cannot have it
    assert anon_client.get("/summary", headers=auth(who)).status_code == 403


def test_citizen_map_data_needs_a_login(anon_client):
    assert anon_client.get("/plots").status_code == 401
    assert anon_client.get("/construction-alerts").status_code == 401
