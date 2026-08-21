import logging
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI


logger = logging.getLogger("uvicorn.error")


class SimilarItems:
    def __init__(self):
        self.similar_items = None

    def load(self, path):
        logger.info(f"Loading similar items from {path}")

        self.similar_items = pd.read_parquet(
            path,
            columns=["item_id_1", "item_id_2", "score"],
        )

        self.similar_items = self.similar_items.set_index("item_id_1")

        logger.info(
            f"Loaded {len(self.similar_items)} similar item pairs"
        )

    def get(self, item_id: int, k: int = 10):
        try:
            similar = self.similar_items.loc[item_id]

            similar = (
                similar
                .sort_values("score", ascending=False)
                .head(k)
            )

            return {
                "item_id": similar["item_id_2"].tolist(),
                "score": similar["score"].tolist(),
            }

        except KeyError:
            logger.warning(
                f"No similar items found for item {item_id}"
            )

            return {
                "item_id": [],
                "score": [],
            }


similar_items_store = SimilarItems()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting similar items service")

    similar_items_store.load("similar.parquet")

    logger.info("Similar items service is ready")

    yield

    logger.info("Stopping similar items service")


app = FastAPI(
    title="similar-items",
    lifespan=lifespan,
)


@app.post("/similar_items")
async def similar_items(item_id: int, k: int = 10):
    """
    Возвращает k похожих объектов для item_id.
    """

    return similar_items_store.get(item_id, k)