from typing import Optional, Union, List
from pydantic import BaseModel, field_validator, ConfigDict


class StateChanges(BaseModel):
    model_config = ConfigDict(extra="allow")

    wounds: Optional[Union[int, str]] = None
    fate: Optional[Union[int, str]] = None
    xp: Optional[Union[int, str]] = None
    money: Optional[Union[int, str]] = None
    location: Optional[str] = None
    date: Optional[str] = None
    journal: Optional[Union[str, List[str]]] = None
    equipment_add: Optional[Union[str, List[str]]] = None
    equipment_remove: Optional[Union[str, List[str]]] = None
    inventory_add: Optional[Union[str, List[str]]] = None
    inventory_remove: Optional[Union[str, List[str]]] = None
    weapon_add: Optional[Union[str, List[str]]] = None
    weapon_lost: Optional[Union[str, List[str]]] = None
    npc_add: Optional[Union[str, List[str]]] = None
    npc_remove: Optional[Union[str, List[str]]] = None
    quest_add: Optional[Union[str, List[str]]] = None
    quest_remove: Optional[Union[str, List[str]]] = None
    companion_add: Optional[Union[str, List[str]]] = None
    companion_remove: Optional[Union[str, List[str]]] = None
    effect_add: Optional[Union[str, List[str]]] = None
    effect_remove: Optional[Union[str, List[str]]] = None
    insanity: Optional[Union[int, str]] = None
    corruption: Optional[Union[int, str]] = None
    rank: Optional[Union[int, str]] = None
    ship_hull: Optional[str] = None
    ship_crew: Optional[str] = None
    ship_status: Optional[str] = None
    ship_note: Optional[str] = None
    ship_acquired: Optional[str] = None
    ship_lost: Optional[str] = None
    armour_equip: Optional[Union[str, List[str]]] = None
    armour_unequip: Optional[Union[str, List[str]]] = None

    @field_validator('wounds', 'fate', 'xp', 'money', 'insanity', 'corruption', 'rank', mode='before')
    @classmethod
    def validate_deltas(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            s = v.strip()
            if not (s.startswith('+') or s.startswith('-') or s.isdigit()):
                raise ValueError("Must be int or delta string (+/-)")
            return s
        return v
