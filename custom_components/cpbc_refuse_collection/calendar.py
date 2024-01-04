import logging
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from homeassistant.util.dt import start_of_local_day, as_utc, as_local

from datetime import datetime, timedelta
from .const import DOMAIN
from zoneinfo import ZoneInfo

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the calendar entries."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    async_add_entities([CpbcRefuseCollectionCalendar(coordinator)], True)
    
    road_id = config_entry.data.get("road_id")

    if road_id is None:
        _LOGGER.error("No road_id found in configuration entry")
        return

class CpbcRefuseCollectionCalendar(CalendarEntity, CoordinatorEntity):
    """A calendar entity."""
    def __init__(self, coordinator):
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._name = "Castle Point Refuse Collection Calendar"
        self._unique_id = "cpbc_refuse_collection_unique_id"
        self._event = None

    @property
    def name(self) -> str:
        """Return the name of the calendar entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID for the calendar entity."""
        return self._unique_id

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.coordinator.async_add_listener(self._handle_coordinator_update)

    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def event(self) -> CalendarEvent:
        """Return the next upcoming event."""
        if self.coordinator.data:
            events = self.coordinator.data.get("events", [])
            _LOGGER.debug("Events data: %s", events)

            # Find the next upcoming event
            current_time = as_local(datetime.now())
            next_event = None
            for event in events:
                start_time = as_local(event["start"])
                if start_time >= current_time:
                    if next_event is None or start_time < next_event["start"]:
                        next_event = event

            if next_event:
                _LOGGER.debug("Next Event: %s", next_event)
                return CalendarEvent(
                    summary=next_event["summary"],
                    start=next_event["start"],
                    end=next_event["end"],
                    location=next_event.get("location", ""),  # Add default if no location
                    description=next_event.get("description", "")  # Add default if no description
                )
        return None

    def _get_datetime(self, time_str):
        """Convert a time string to a datetime object."""
        try:
            naive_datetime = datetime.fromisoformat(time_str)
            aware_datetime = naive_datetime.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            return aware_datetime
        except ValueError as e:
            _LOGGER.error(f"Error parsing date string: {time_str} - Error: {e}")
            return None

    async def async_get_events(self, hass, start_date, end_date):
        """Return calendar events within a datetime range."""
        events = []
        for event_data in self.coordinator.data.get("events", []):
            event_start = event_data["start"]
            event_end = event_data["end"]
            
            if start_date <= event_start <= end_date:
                events.append(CalendarEvent(
                    summary=event_data["summary"],
                    start=event_start,
                    end=event_end
                ))

        return events