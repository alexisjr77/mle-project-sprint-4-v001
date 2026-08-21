from fastapi import FastAPI


class EventStore:
    def __init__(self, max_events_per_user=10):
        self.events = {}
        self.max_events_per_user = max_events_per_user

    def put(self, user_id: int, item_id: int):
        user_events = self.events.get(user_id, [])

        self.events[user_id] = (
            [item_id] + user_events
        )[:self.max_events_per_user]

    def get(self, user_id: int, k: int = 3):
        return self.events.get(user_id, [])[:k]


events_store = EventStore()

app = FastAPI(title="events")


@app.post("/put")
async def put(user_id: int, item_id: int):
    """
    Сохраняет событие пользователя.
    """

    events_store.put(user_id, item_id)

    return {"result": "ok"}


@app.post("/get")
async def get(user_id: int, k: int = 3):
    """
    Возвращает последние события пользователя.
    """

    events = events_store.get(user_id, k)

    return {"events": events}