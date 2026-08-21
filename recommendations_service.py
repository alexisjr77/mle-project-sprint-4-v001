import logging
from contextlib import asynccontextmanager

import pandas as pd
import requests
from fastapi import FastAPI


logger = logging.getLogger("uvicorn.error")

FEATURES_STORE_URL = "http://127.0.0.1:8010"
EVENTS_STORE_URL = "http://127.0.0.1:8020"


class Recommendations:
    def __init__(self):
        self.recommendations = None
        self.default_recommendations = None

    def load(self, path):
        logger.info(f"Loading recommendations from {path}")

        self.recommendations = pd.read_parquet(
            path,
            columns=["user_id", "item_id", "cb_score"],
        )

        self.recommendations = self.recommendations.set_index("user_id")

        self.default_recommendations = pd.read_parquet(
            "top_popular.parquet",
            columns=["item_id", "popularity_score"],
        )

        logger.info(
            f"Loaded {len(self.recommendations)} personal recommendations"
        )
        logger.info(
            f"Loaded {len(self.default_recommendations)} popular items"
        )

    def get(self, user_id: int, k: int = 10):
        try:
            user_recommendations = self.recommendations.loc[user_id]

            user_recommendations = (
                user_recommendations
                .sort_values("cb_score", ascending=False)
                .head(k)
            )

            return user_recommendations["item_id"].tolist()

        except KeyError:
            return self.default_recommendations["item_id"].head(k).tolist()


recommendations_store = Recommendations()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting recommendations service")

    recommendations_store.load("final_recommendations.parquet")

    logger.info("Recommendations service is ready")

    yield

    logger.info("Stopping recommendations service")


app = FastAPI(
    title="recommendations",
    lifespan=lifespan,
)


def dedup_ids(ids):
    """Удаляет дубликаты, сохраняя исходный порядок."""
    seen = set()
    result = []

    for item_id in ids:
        if item_id not in seen:
            seen.add(item_id)
            result.append(item_id)

    return result


@app.post("/recommendations_offline")
async def recommendations_offline(user_id: int, k: int = 10):
    """
    Возвращает offline-рекомендации для пользователя.

    Если есть персональные рекомендации, используются они.
    Иначе возвращаются популярные объекты.
    """

    recs = recommendations_store.get(user_id, k)

    return {"recs": dedup_ids(recs)[:k]}


@app.post("/recommendations_online")
async def recommendations_online(user_id: int, k: int = 10):
    """
    Возвращает online-рекомендации на основе истории пользователя.
    """

    headers = {
        "Content-type": "application/json",
        "Accept": "text/plain",
    }

    try:
        response = requests.post(
            f"{EVENTS_STORE_URL}/get",
            headers=headers,
            params={
                "user_id": user_id,
                "k": 3,
            },
            timeout=5,
        )
        response.raise_for_status()

        events = response.json()["events"]

    except requests.RequestException:
        logger.exception("Failed to get user events")
        return {"recs": []}

    if not events:
        return {"recs": []}

    candidates = []

    for item_id in events:
        try:
            response = requests.post(
                f"{FEATURES_STORE_URL}/similar_items",
                headers=headers,
                params={
                    "item_id": item_id,
                    "k": k,
                },
                timeout=5,
            )
            response.raise_for_status()

            similar_items = response.json()

            items = similar_items.get("item_id", [])
            scores = similar_items.get("score", [])

            candidates.extend(zip(items, scores))

        except requests.RequestException:
            logger.exception(
                f"Failed to get similar items for item {item_id}"
            )

    candidates.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    recs = [
        item_id
        for item_id, _ in candidates
        if item_id not in events
    ]

    recs = dedup_ids(recs)[:k]

    return {"recs": recs}


@app.post("/recommendations")
async def recommendations(user_id: int, k: int = 10):
    """
    Возвращает итоговые рекомендации,
    смешивая online- и offline-рекомендации.
    """

    offline_response = await recommendations_offline(user_id, k)
    online_response = await recommendations_online(user_id, k)

    recs_offline = offline_response["recs"]
    recs_online = online_response["recs"]

    # Сначала чередуем online и offline рекомендации.
    recs_blended = []

    max_length = max(
        len(recs_online),
        len(recs_offline),
    )

    for i in range(max_length):
        if i < len(recs_online):
            recs_blended.append(recs_online[i])

        if i < len(recs_offline):
            recs_blended.append(recs_offline[i])

    # Убираем дубликаты и ограничиваем количество
    recs_blended = dedup_ids(recs_blended)[:k]

    return {"recs": recs_blended}