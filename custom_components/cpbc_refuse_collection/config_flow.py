import logging
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

import voluptuous as vol
from aiohttp import ClientSession
from bs4 import BeautifulSoup

class CpbcRefuseCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CPBC Refuse Collection Calendar."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is not None:
            # Validation or processing of user input
            valid = await self._validate_input(user_input)
            if valid:
                # Here, only save the road_id in the configuration entry
                return self.async_create_entry(
                    title="Castle Point Borough Council Refuse Collection Calendar",
                    data={"road_id": user_input["road_id"]}
                )
            else:
                errors["base"] = "invalid_input"

        # Fetch road names and IDs from the web page
        road_names_and_ids = await self._fetch_road_names_and_ids()

        # Schema for the form
        data_schema = vol.Schema({
            vol.Required("road_id"): vol.In({road_id: road_name for road_name, road_id in road_names_and_ids}),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def _validate_input(self, user_input):
        """Validate user input."""
        road_id = user_input.get("road_id")
        road_names_and_ids = await self._fetch_road_names_and_ids()
        if road_id not in [road_id for _, road_id in road_names_and_ids]:
            return False
        return True

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return CpbcRefuseCollectionCalendarOptionsFlow(config_entry)
    
    async def _fetch_road_names_and_ids(self):
        """Fetch road names and IDs from the web page."""
        url = 'https://apps.castlepoint.gov.uk/cpapps/index.cfm?fa=wastecalendar' 
        async with ClientSession() as session:
            async with session.get(url) as response:
                data = await response.text() 
        soup = BeautifulSoup(data, 'html.parser')
        road_options = soup.find("select",{"name":"roadID"}).findAll("option")
        road_names_and_ids = []
        for road in road_options:
            road_name = road.text
            road_id = road["value"]
            road_names_and_ids.append((road_name, road_id))
        return road_names_and_ids
    
    async def async_step_options(self, user_input=None):
        """Handle options."""
        _LOGGER.debug("User input for options: %s", user_input)
        current_road_id = self.config_entry.data.get("road_id")
        if user_input is not None:
            selected_road_name = user_input.get("road_id")
            new_road_id = next(item[1] for item in await self._fetch_road_names_and_ids() if item[0] == selected_road_name)
            _LOGGER.debug("ROAD ID: %s", new_road_id)
             
            if current_road_id != new_road_id:
                # Only update if there's a change
                return self.async_create_entry(title="", data={"road_id": new_road_id})
            # No change, return without creating a new entry
            return self.async_abort(reason="road_id unchanged")
        # Fetch road names and IDs from the web page
        road_names_and_ids = await self._fetch_road_names_and_ids()
        _LOGGER.debug("Showing options form with data: %s", road_names_and_ids)
        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema({
                vol.Required("road_id", default=current_road_id): vol.In([road[0] for road in road_names_and_ids]),
            }, extra=vol.ALLOW_EXTRA),
            description_placeholders={
                "description": "Please select your road from the dropdown for options."
            },
        )

class CpbcRefuseCollectionCalendarOptionsFlow(config_entries.OptionsFlow):
    """Handle options for CPBC Refuse Collection Calendar."""
    def __init__(self, config_entry):
        """Initialize CPBC Refuse Collection Calendar options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the CPBC Refuse Collection Calendar options."""
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )
