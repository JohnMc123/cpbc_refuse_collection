import logging
from homeassistant.helpers.entity import Entity
from datetime import datetime
from homeassistant.util.dt import as_local, utcnow

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up CPBC Refuse Collection Sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    async_add_entities([CpbcRefuseCollectionSensor(coordinator)], True)

class CpbcRefuseCollectionSensor(Entity):
    def __init__(self, coordinator):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._state = None
        self._attributes = {}
        self._unique_id = f"cpbc_refuse_collection_next_event_{coordinator.road_id}"

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return "CPBC Next Refuse Collection"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes or {"initial": "No data yet"}

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes or {"initial": "No data yet"}

    async def async_update(self):
        """Update the sensor."""
        events = self.coordinator.data.get("events", [])
        current_time = as_local(utcnow())

        for event in events:
            start_time = as_local(event["start"])
            if start_time.date() >= current_time.date():
                self._state = event["summary"]
                days_until = (start_time.date() - current_time.date()).days
                self._attributes = {
                    "collection_date": start_time.date(),
                    "collection_type": event["description"],
                    "days_until": days_until
                }
                break
