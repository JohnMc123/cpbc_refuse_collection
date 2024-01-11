import logging
from homeassistant.helpers.entity import Entity
from datetime import datetime, timedelta
from homeassistant.util.dt import as_local, utcnow
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up CPBC Refuse Collection Sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    async_add_entities([CpbcRefuseCollectionSensor(coordinator)], True)
    validation_sensor = CpbcRefuseCollectionValidationSensor(coordinator, entry)
    async_add_entities([validation_sensor], True)

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
            end_time = as_local(event["end"])
            if start_time.date() >= current_time.date() and end_time >= current_time:
                self._state = event["description"]
                days_until = (start_time.date() - current_time.date()).days
                self._attributes = {
                    "collection_date": start_time.date(),
                    "collection_type": event["description"],
                    "days_until": days_until,
                    "type": event["summary"]
                }
                break

class CpbcRefuseCollectionValidationSensor(SensorEntity):
    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.entry = entry
        self._state = "Unknown"
        self._unique_id = f"cpbc_refuse_collection_validation_{entry.entry_id}"
        self._attributes = {}

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return "CPBC Refuse Collection Validation"

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

    async def async_validate_road_details(self, *_):
        """Validate road details against fetched data."""
        road_id = self.entry.data.get("road_id")
        road_name = self.entry.data.get("road_name")
        road_names_and_ids = await self.coordinator._fetch_road_names_and_ids()
        validation_timestamp = as_local(datetime.now())
        _LOGGER.debug("Expecting: %s:%s", road_id, road_name)
        search_road = next(((r_name, r_id) for r_name, r_id in road_names_and_ids if r_id == road_id and r_name == road_name), None)
        _LOGGER.debug("Got: %s", search_road)
        if search_road != None:
            _LOGGER.debug("Road ID and Name validation passed")
            self._state = "pass"
            self._attributes = {
                "road_validation": "PASSED",
                "last_validated": validation_timestamp
                }
        else:
            _LOGGER.debug("Road ID and Name validation failed")
            self._state = "failed"
            self._attributes = {
                "road_validation": "FAILED",
                "last_validated": validation_timestamp
                }

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # perform initial validation check at integration start
        await self.async_validate_road_details()
        # Set up a periodic check
        async_track_time_interval(self.hass, self.async_validate_road_details, timedelta(days=7))

    async def async_update(self):
        """Update the sensor."""