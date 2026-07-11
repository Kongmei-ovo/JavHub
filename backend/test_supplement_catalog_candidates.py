from __future__ import annotations

import services.supplement_candidates as candidates


def test_catalog_candidates_include_native_canonical_films(monkeypatch):
    created = []
    events = []

    def fake_upsert(**kwargs):
        created.append(kwargs)
        return {"id": 91, "was_inserted": True}

    monkeypatch.setattr(candidates, "upsert_candidate_from_video", fake_upsert)
    monkeypatch.setattr(candidates, "add_download_candidate_event", lambda *args: events.append(args))
    monkeypatch.setattr(candidates, "is_video_exempt", lambda code: False)

    result = candidates.generate_download_candidates_from_catalog(
        [
            {
                "canonical_number": "JUR-418",
                "display_code": "JUR-418",
                "title": "Native work",
                "release_date": "2025-10-01",
                "cover_url": "cover.jpg",
                "origin": "native",
                "funnel_stage": "find_source",
                "candidate_ids": [],
            },
            {
                "canonical_number": "DONE-1",
                "funnel_stage": "complete",
                "candidate_ids": [],
            },
        ],
        actress_id=1020504,
        actress_name="Actor",
    )

    assert result == {
        "checked": 1,
        "created": 1,
        "existing": 0,
        "skipped": 0,
        "candidate_ids": [91],
    }
    assert created[0]["video"]["content_id"] == "JUR-418"
    assert created[0]["source"] == "supplement"
    assert created[0]["reason"] == "catalog_acquisition_gap"
    assert events[0][1] == "catalog_imported"


def test_catalog_candidates_reuse_any_existing_candidate(monkeypatch):
    monkeypatch.setattr(
        candidates,
        "upsert_candidate_from_video",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not create duplicate")),
    )

    result = candidates.generate_download_candidates_from_catalog(
        [{
            "canonical_number": "JUR-418",
            "funnel_stage": "find_source",
            "candidate_ids": [10, 11],
        }],
        actress_id=1020504,
    )

    assert result["created"] == 0
    assert result["existing"] == 1
    assert result["candidate_ids"] == [10, 11]


def test_catalog_candidates_can_target_one_canonical_number(monkeypatch):
    seen = []

    def fake_upsert(**kwargs):
        seen.append(kwargs["video"]["content_id"])
        return {"id": 7, "was_inserted": False}

    monkeypatch.setattr(candidates, "upsert_candidate_from_video", fake_upsert)
    monkeypatch.setattr(candidates, "is_video_exempt", lambda code: False)

    result = candidates.generate_download_candidates_from_catalog(
        [
            {"canonical_number": "ABC-1", "funnel_stage": "find_source", "candidate_ids": []},
            {"canonical_number": "ABC-2", "funnel_stage": "find_source", "candidate_ids": []},
        ],
        actress_id=1,
        canonical_number="abc-2",
    )

    assert seen == ["ABC-2"]
    assert result["checked"] == 1
    assert result["existing"] == 1
