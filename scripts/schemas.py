from pydantic import BaseModel, Field
from typing import Optional, List


class TrailMetadata(BaseModel):
    id: str
    name: Optional[str] = None
    source_url: Optional[str] = None
    region: Optional[str] = None

    distance_km: Optional[float] = None
    duration_hours: Optional[float] = None
    elevation_gain_m: Optional[int] = None
    max_altitude_m: Optional[int] = None

    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    technical_difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    fitness_difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    exposure: Optional[int] = Field(default=None, ge=0, le=5)

    trail_type: Optional[str] = None
    route_type: Optional[str] = None

    suitable_for_beginners: Optional[bool] = None
    suitable_for_children: Optional[bool] = None
    suitable_for_families: Optional[bool] = None
    suitable_for_winter: Optional[bool] = None

    requires_experience: Optional[bool] = None
    requires_equipment: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)

    main_attractions: List[str] = Field(default_factory=list)
    recommended_season: List[str] = Field(default_factory=list)

    start_point: Optional[str] = None
    end_point: Optional[str] = None

    short_summary: Optional[str] = None
    description: str