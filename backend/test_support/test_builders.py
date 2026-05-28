from __future__ import annotations

from test_support.builders import page_response


def test_page_response_defaults_totals_from_data_length():
    response = page_response([{"id": 1}, {"id": 2}], page_size=10)

    assert response == {
        "data": [{"id": 1}, {"id": 2}],
        "page": 1,
        "page_size": 10,
        "total_count": 2,
        "total_pages": 1,
    }


def test_page_response_allows_explicit_totals():
    response = page_response([{"id": 1}], page=2, page_size=10, total_count=30, total_pages=3)

    assert response["page"] == 2
    assert response["total_count"] == 30
    assert response["total_pages"] == 3
