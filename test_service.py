import requests


BASE_URL = "http://127.0.0.1:8000"
EVENTS_URL = "http://127.0.0.1:8020"

HEADERS = {
    "Content-type": "application/json",
    "Accept": "text/plain",
}


def get_recommendations(user_id, k=10):
    response = requests.post(
        f"{BASE_URL}/recommendations",
        headers=HEADERS,
        params={
            "user_id": user_id,
            "k": k,
        },
        timeout=10,
    )

    response.raise_for_status()

    return response.json()["recs"]


def add_event(user_id, item_id):
    response = requests.post(
        f"{EVENTS_URL}/put",
        headers=HEADERS,
        params={
            "user_id": user_id,
            "item_id": item_id,
        },
        timeout=10,
    )

    response.raise_for_status()


def check_recommendations(recs, k=10):
    assert isinstance(recs, list)
    assert len(recs) <= k
    assert len(recs) == len(set(recs))


print("1. User without personal recommendations")

user_id = 2_000_000

recs = get_recommendations(user_id)

print("user_id:", user_id)
print("recommendations:", recs)
print("count:", len(recs))
print()


print("2. User with personal recommendations and without online history")

user_id = 3

recs = get_recommendations(user_id)

print("user_id:", user_id)
print("recommendations:", recs)
print("count:", len(recs))

check_recommendations(recs)

print()


print("3. User with personal recommendations and online history")

user_id = 1_111_111

event_item_ids = [
    33311009,
    63591534,
    53404,
]

for item_id in event_item_ids:
    add_event(user_id, item_id)

recs = get_recommendations(user_id)

print("user_id:", user_id)
print("events:", event_item_ids)
print("recommendations:", recs)
print("count:", len(recs))

check_recommendations(recs)

print()


print("All tests passed!")