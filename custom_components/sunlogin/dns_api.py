import requests
import functools
import json
from urllib.parse import urlencode
import logging

API_URL_IP33 = "http://api.ip33.com/dns/resolver"
API_URL_NSLOOKUP_IO = "https://www.nslookup.io/api/v1/records"
TIMEOUT = 15

_LOGGER = logging.getLogger(__name__)

async def async_query_by_nslookup_io(hass, domain, dns_server='cloudflare'):
    headers={"Content-Type": "application/json"}
    data = {"domain": domain, "dnsServer": dns_server}
    func = functools.partial(requests.post, API_URL_NSLOOKUP_IO, headers=headers, data=json.dumps(data), timeout=TIMEOUT)
    resp = await hass.async_add_executor_job(func)
    return resp

async def async_query_by_ip33(hass, domain, dns_server='114.114.114.114', query_type='A'):
    headers={"Content-Type": "application/x-www-form-urlencoded"}
    data = {"domain": domain, "dns": dns_server, "type": query_type}
    func = functools.partial(requests.post, API_URL_IP33, headers=headers, data=urlencode(data), timeout=TIMEOUT)
    resp = await hass.async_add_executor_job(func)
    return resp

async def async_dns_query(hass, domain, server='ip33'):
    result = None

    if server == "ip33":
        try:
            resp = await async_query_by_ip33(hass, domain)
            r_json = resp.json()
            result = r_json['record'][0]['ip']
        except: pass
    elif server == 'nslookupio':
        try:
            resp = await async_query_by_nslookup_io(hass, domain)
            r_json = resp.json()
            r = r_json['records']['a']['response']['answer']
            for record in r:
                record_type = record['record']['recordType']
                if record_type == 'A':
                    result = record['record']['ipv4']
        except: pass

    return result

class DNS():
    cache = dict()

    def __init__(self, hass, server) -> None:
        self.hass = hass
        self.server = server

    def set_domain(self, domain, ip=None):
        self.cache.update({domain: ip})

    async def async_query(self, domain):
        ip = await async_dns_query(self.hass, domain=domain, server=self.server)
        if ip is not None:
            self.cache.update({domain: ip})

    async def async_update(self):
        for domain in list(self.cache.keys()):
            await self.async_query(domain)