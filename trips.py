from pydantic import BaseModel

class Trip(BaseModel):
    # core identity
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    # where
    country: str
    city: str                    # primary city
    places: list[Place]          # Place has name, lat, lng, category
    
    # when
    start_date: date
    end_date: date
    duration_days: int           # computed from dates
    
    # media
    photos: list[Photo]          # Photo has url, caption, taken_at
    audio_notes: list[AudioNote] # AudioNote has url, duration, transcript
    
    # feelings + memory
    vibe: VibeTag                # loved_it / mixed / never_again / neutral
    highlight: str               # one sentence — best moment
    lowlight: str                # one sentence — worst moment
    notes: str                   # long form journal entry
    tags: list[str]              # ["street food", "solo", "budget", "hiking"]
    would_return: bool
    
    # context
    travel_style: TravelStyle    # solo / couple / group / family
    budget_level: BudgetLevel    # backpacker / mid / luxury
    trip_type: list[TripType]    # adventure / food / culture / nature / party
    season: str                  # monsoon, winter, summer — auto from dates
    
    # social
    tips: list[StrangerTip]      # tips this user added for this destination
    is_public: bool              # can others see this trip