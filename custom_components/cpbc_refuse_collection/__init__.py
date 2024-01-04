import logging
from datetime import datetime, timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import start_of_local_day, as_utc, parse_datetime

from .const import DOMAIN
from .calendar import CpbcRefuseCollectionCalendar

from bs4 import BeautifulSoup
import voluptuous as vol
from aiohttp import ClientSession
import re
import calendar

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the CPBC Refuse Collection Calendar component."""
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up CPBC Refuse Collection Calendar from a config entry."""
    road_id = entry.data.get("road_id")
    if not road_id:
        _LOGGER.error("No road_id found in config entry")
        return False
    try:
        coordinator = CpbcRefuseCollectionCalendarDataCoordinator(hass, road_id)
        await coordinator.async_refresh()
    except Exception as e:
        _LOGGER.error(f"Error setting up coordinator: {e}")
        return False

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "calendar": CpbcRefuseCollectionCalendar(coordinator)
    }

    hass.async_add_job(
        hass.config_entries.async_forward_entry_setup(entry, "calendar")
    )
    return True

class CpbcRefuseCollectionCalendarDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching CPBC Refuse Collection Calendar data."""

    def __init__(self, hass, road_id):
        """Initialize."""
        self.road_id = road_id
        update_interval = timedelta(days=1)  # Update every 1 day

        super().__init__(
            hass,
            _LOGGER,
            name="Castle Point Borough Council Refuse Collection Calendar",
            update_method=self._async_update_data,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Fetch data."""
        collection_events = []
        _LOGGER.debug("Coordinator update road ID: %s", self.road_id)
        
        try:
            url = f'https://apps.castlepoint.gov.uk/cpapps/index.cfm?fa=wastecalendar.displayDetails&roadID={self.road_id}'
            _LOGGER.debug("Coordinator update URL: %s", url)
            try:
                async with ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            _LOGGER.error("Error fetching data: URL: %s, Status: %s", url, response.status)
                            return {"events": []}
                        html_content = await response.text()
        
                soup = BeautifulSoup(html_content, 'html.parser') 
                collection_months = soup.find_all(class_="calendarContainer")
                dedup_collection_months = []
                    
                for outer_range, outer_value in enumerate(collection_months):
                    try:
                        if outer_value:
                            soup = BeautifulSoup(str(outer_value), 'html.parser')
                            outer_month = soup.find("h2")
                            for inner_range in range(outer_range + 1, len(collection_months)):
                                soup = BeautifulSoup(str(collection_months[inner_range]), 'html.parser')
                                inner_month = soup.find("h2")

                                if outer_month == inner_month:
                                    dedup_collection_months.append(outer_value)
                    except Exception as outer_exc:
                        print(f"Error in outer loop ({outer_range}): {outer_exc}")

                for month in dedup_collection_months:
                    soup = BeautifulSoup(str(month), 'html.parser')
                    rex_search = re.search("<h2>(?P<month>.+)\s(?P<year>\d+)<\/h2>", str(soup.find("h2")))
                    collection_month = f"{list(calendar.month_name).index(str(rex_search.group('month'))):02d}"
                    collection_year = int(rex_search.group('year'))
                    scheduled_collections = soup.find_all(class_=["pink","normal"])
                    
                    for scheduled_collection in scheduled_collections:
                        rex_search = re.search("<td.+?class=\"(?P<class>.+?)\".+?(?P<day>\d+)<.+", str(scheduled_collection))
                        collection_class = str(rex_search.group('class'))
                        collection_days = f"{int(rex_search.group('day')):02d}"
                        start_string = str(collection_year) + "-" + str(collection_month) + "-" + str(collection_days)
                        end_string = str(collection_year) + "-" + str(collection_month) + "-" + str(int(collection_days)+1)
                        start_datetime = parse_datetime(start_string)
                        end_datetime = parse_datetime(end_string)

                        if start_datetime and end_datetime:
                            collection_events.append({ "summary": str(collection_class), "start": as_utc(start_of_local_day(start_datetime)), "end": as_utc(start_of_local_day(end_datetime)),})
                        else:
                            _LOGGER.error(f"Invalid date format: {start_string} to {end_string}")
                _LOGGER.debug("Events: %s", collection_events)
                return {"events": collection_events}
            except Exception as e:
                _LOGGER.error("Error fetching data: URL: %s, Exception: %s", url, e)
                raise UpdateFailed(f"Error updating data: {e}")        
        except Exception as e:
            raise UpdateFailed(f"Error updating data: {e}")

    async def async_get_events(self, hass, start_date, end_date):
        """Return calendar events within a datetime range."""
        # Filter and return events from self.coordinator.data that fall within
        # the range defined by start_date and end_date.
        return [
            event for event in self.coordinator.data.get("events", [])
            if start_date <= self._get_datetime(event["start"]) <= end_date
        ]
        