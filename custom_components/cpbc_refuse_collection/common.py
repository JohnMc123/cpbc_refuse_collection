from aiohttp import ClientSession
from bs4 import BeautifulSoup

async def fetch_road_names_and_ids():
    """Fetch road names and IDs from the web page."""
    url = 'https://apps.castlepoint.gov.uk/cpapps/index.cfm?fa=wastecalendar' 
    async with ClientSession() as session:
        async with session.get(url) as response:
            data = await response.text() 
    soup = BeautifulSoup(data, 'html.parser')
    road_options = soup.find("select", {"name": "roadID"}).findAll("option")
    road_names_and_ids = []
    for road in road_options:
        road_name = road.text
        road_id = road["value"]
        road_names_and_ids.append((road_name, road_id))
    return road_names_and_ids
