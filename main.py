from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum

app = FastAPI()

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool | None = None


class VibeTag(str, Enum):
    loved_it = "loved it"
    mixed = "mixed"
    never_again = "never_Again"
    neutral = "neutral"

class StrangerTip(BaseModel):
    tip :str
    is_public: bool  

class Trip(BaseModel):
    # core identity
    user_id: int
    # where
    country: str       # Place has name, lat, lng, category
    
    # when
    duration_days: int           # computed from dates
    
    # feelings + memory
    vibe: VibeTag                # loved_it / mixed / never_again / neutral

    # social
    tips: list[StrangerTip]      # tips this user added for this destination
    is_public: bool              # can others see this trip

# List of Trip instances for demonstration
Trips = [
    Trip(
        user_id=1,
        country="France",
        duration_days=7,
        vibe=VibeTag.loved_it,
        tips=[StrangerTip(tip="Pack light", is_public=True)],
        is_public=True,
    ),
    Trip(
        user_id=1,
        country="Germany",
        duration_days=4,
        vibe=VibeTag.mixed,
        tips=[StrangerTip(tip="Nude beaches", is_public=True)],
        is_public=True,
    ),
    Trip(
        user_id=2,
        country="India",
        duration_days=3,
        vibe=VibeTag.never_again,
        tips=[StrangerTip(tip="Food better place", is_public=True)],
        is_public=True,
    ),
    Trip(
        user_id=3,
        country="Thailand",
        duration_days=10,
        vibe=VibeTag.neutral,
        tips=[StrangerTip(tip="Loot", is_public=True)],
        is_public=False,
    )
]

@app.get("/trips")
def get_all_trips():
    return Trips

@app.get("/trips/{id}")
def get_all_trips(id: int):
    if id < len(Trips):
        return Trips[id]
    return {"Error" : "No Trips"}


@app.post("/trip")
def add_trip(trip: Trip):
    if Trips.append(trip):
        return {"Status" : "Done"}
    return {"Status" : "Failed"}



@app.put("/trips/{id}")
def update_trip(id: int, trip: Trip):
    if id >= len(Trips):
        return {"Error" : "No Trip with given Id"}
    Trips[id] = trip
    return {"Status" : "Done"}

@app.delete("/trips/{id}")
def delete_trip(id:int):
    if id >= len(Trips):
        return {"Error" : "No Trip with given Id"}
    if Trips.pop(id):
        return {"Status" : "Deleted"}
    return {"Status" : "Failed"}



