import requests
import functools
import json
from urllib.parse import urlencode
import logging
from .sunlogin_api import HTTPRequest
import base64

_LOGGER = logging.getLogger(__name__)

DEFAULT_DNS_SERVER = '223.5.5.5'

DNS_Q = 0
DNS_R = 1

# Opcodes
DNS_QUERY = 0
DNS_IQUERY = 1
DNS_STATUS = 2
DNS_NOTIFY = 4
DNS_UPDATE = 5

# Flags
DNS_CD = 0x0010 # checking disabled
DNS_AD = 0x0020 # authenticated data
DNS_Z =  0x0040 # unused
DNS_RA = 0x0080 # recursion available
DNS_RD = 0x0100 # recursion desired
DNS_TC = 0x0200 # truncated
DNS_AA = 0x0400 # authoritative answer

# Response codes
DNS_RCODE_NOERR = 0
DNS_RCODE_FORMERR = 1
DNS_RCODE_SERVFAIL = 2
DNS_RCODE_NXDOMAIN = 3
DNS_RCODE_NOTIMP = 4
DNS_RCODE_REFUSED = 5
DNS_RCODE_YXDOMAIN = 6
DNS_RCODE_YXRRSET = 7
DNS_RCODE_NXRRSET = 8
DNS_RCODE_NOTAUTH = 9
DNS_RCODE_NOTZONE = 10

# RR types
DNS_A = 1
DNS_NS = 2
DNS_CNAME = 5
DNS_SOA = 6
DNS_PTR = 12
DNS_HINFO = 13
DNS_MX = 15
DNS_TXT = 16
DNS_AAAA = 28
DNS_SRV = 33

# RR classes
DNS_IN = 1
DNS_CHAOS = 3
DNS_HESIOD = 4
DNS_ANY = 255

def check_dns_server(dns_server):
    ip = dns_server.split('.')
    if dns_server == DEFAULT_DNS_SERVER:
        return
    if len(ip) != 4:
        return
    for i in ip:
        if not i.isdigit() or int(i) < 0 or int(i) > 255:
            return
    if int(ip[0]) < 1 or int(ip[0]) == 255:
        return

def change_dns_server(dns_server):
    global DEFAULT_DNS_SERVER
    dns_server = dns_server.strip()
    
    DEFAULT_DNS_SERVER = dns_server
    _LOGGER.debug("DNS API: DNS server changed to %s", dns_server)


class DNSMessage:
    _transaction_id = None
    _flags = None
    _qdcount = None
    _ancount = None
    _nscount = None
    _arcount = None
    _qname = None
    _qtype = None
    _qclass = None
    _rname = None
    _rtype = None
    _rclass = None
    _ttl = None
    _rdlength = None
    _rdata = None
    _raw = None
    allow_name = None

    def __init__(self):
        self.allow_name = list()
    
    @property
    def transaction_id(self):
        return int.from_bytes(self._transaction_id, byteorder='big', signed=False)
    
    @transaction_id.setter
    def transaction_id(self, value):
        self._transaction_id = value.to_bytes(length=2, byteorder='big', signed=False)

    @property
    def flags(self):
        return int.from_bytes(self._flags, byteorder='big', signed=False)

    @flags.setter
    def flags(self, value):
        self._flags = value.to_bytes(length=2, byteorder='big', signed=False)

    @property
    def qr(self):
        return (self.flags >> 15) & 1
    
    @qr.setter
    def qr(self, value):
        self.flags = self.flags | (1 << 15) if value else self.flags & ~(1 << 15)

    @property
    def opcode(self):
        return (self.flags >> 11) & 0xf
    
    @opcode.setter
    def opcode(self, value):
        self.flags = (self.flags & 0x87ff) | ((value & 0xf) << 11)

    @property
    def rd(self):
        return (self.flags >> 8) & 1
    
    @rd.setter
    def rd(self, value):
        self.flags = self.flags | (1 << 8) if value else self.flags & ~(1 << 8)

    @property
    def qdcount(self):
        return int.from_bytes(self._qdcount, byteorder='big', signed=False)

    @qdcount.setter
    def qdcount(self, value):
        self._qdcount = value.to_bytes(length=2, byteorder='big', signed=False)

    @property
    def ancount(self):
        return int.from_bytes(self._ancount, byteorder='big', signed=False)

    @ancount.setter
    def ancount(self, value):
        self._ancount = value.to_bytes(length=2, byteorder='big', signed=False)

    @property
    def nscount(self):
        return int.from_bytes(self._nscount, byteorder='big', signed=False)

    @nscount.setter
    def nscount(self, value):
        self._nscount = value.to_bytes(length=2, byteorder='big', signed=False)

    @property
    def arcount(self):
        return int.from_bytes(self._arcount, byteorder='big', signed=False)

    @arcount.setter
    def arcount(self, value):
        self._arcount = value.to_bytes(length=2, byteorder='big', signed=False)

    @property
    def qtype(self):
        return int.from_bytes(self._qtype, byteorder='big', signed=False)
    
    @qtype.setter
    def qtype(self, value):
        self._qtype = value.to_bytes(length=2, byteorder='big', signed=False)
    
    @property
    def qclass(self):
        return int.from_bytes(self._qclass, byteorder='big', signed=False)
    
    @qclass.setter
    def qclass(self, value):
        self._qclass = value.to_bytes(length=2, byteorder='big', signed=False)

    @property
    def rtype(self):
        return int.from_bytes(self._rtype, byteorder='big', signed=False)

    @rtype.setter
    def rtype(self, value):
        self._rtype = value.to_bytes(length=2, byteorder='big', signed=False)

    @property
    def rclass(self):
        return int.from_bytes(self._rclass, byteorder='big', signed=False)
    
    @rclass.setter
    def rclass(self, value):
        self._rclass = value.to_bytes(length=2, byteorder='big', signed=False)

    @property
    def ttl(self):
        return int.from_bytes(self._ttl, byteorder='big', signed=False)
    
    @ttl.setter
    def ttl(self, value):
        self._ttl = value.to_bytes(length=4, byteorder='big', signed=False)

    @property
    def rdlength(self):
        return int.from_bytes(self._rdlength, byteorder='big', signed=False)
    
    @rdlength.setter
    def rdlength(self, value):
        self._rdlength = value.to_bytes(length=2, byteorder='big', signed=False)

    @property
    def rdata(self):
        if self.rtype == DNS_A:
            return '.'.join(map(str, list(self._rdata)))  # A record
        elif self.rtype == DNS_CNAME:
            return self.parse_bytes_name(self._rdata)  # CNAME record
        elif self.rtype == DNS_AAAA:
            pass  # AAAA record
        else:
            pass  # Unsupported record type

    @rdata.setter
    def rdata(self, value):
        self._rdata = value

    @property
    def qname(self):
        if self._qname is None:
            return None
        return self.parse_bytes_name(self._qname)

    @qname.setter
    def qname(self, name):
        if name is None:
            return
        qname = bytes()
        name = name.split('.')
        for part in name:
            qname += bytes([len(part)])
            qname += bytes(part, 'utf-8')
        qname += b'\x00'
        self._qname = qname
        self.transaction_id = 32902
        self.flags = 0x0100
        self.qdcount = 1
        self.ancount = 0
        self.nscount = 0
        self.arcount = 0
        self.qtype = DNS_A
        self.qclass = DNS_IN

    @property
    def raw(self):
        if self._raw is None:
            message = bytes()
            message += self._transaction_id
            message += self._flags
            message += self._qdcount
            message += self._ancount
            message += self._nscount
            message += self._arcount
            message += self._qname
            message += self._qtype
            message += self._qclass
            return message
        return self._raw
    
    @raw.setter
    def raw(self, value):
        self._raw = value
        self._transaction_id = value[:2]
        self._flags = value[2:4]
        self._qdcount = value[4:6]
        self._ancount = value[6:8]
        self._nscount = value[8:10]
        self._arcount = value[10:12]

        qname_length = 12 + value[12:].index(b'\x00')+1
        self._qname = value[12:qname_length]
        self.allow_name.append(self.qname)

        value = value[qname_length:]
        self._qtype = value[:2]
        self._qclass = value[2:4]

        if self.qr == DNS_Q:
            return
        
        value = value[4:]
        # offset = len(self._raw) - len(value)
        for _ in range(self.ancount):
            offset = 0
            rname, value = self.parse_bytes_name(value, offset)
            self._rtype = value[:2]
            self._rclass = value[2:4]
            self._ttl = value[4:8]
            self._rdlength = value[8:10]        
            self._rdata = value[10:10+self.rdlength]
            if self.rtype == DNS_CNAME:
                self.allow_name.append(self.rdata)
            elif self.rtype == DNS_A or self.rtype == DNS_AAAA:
                if rname in self.allow_name:
                    return
            value = value[10+self.rdlength:]

    @property
    def base64(self):
        return base64.b64encode(self.raw).decode('utf-8')
    
    def parse_bytes_name(self, bytes_name, offset=0):
        name = list()
        _offset = -1
        data = bytes_name
        
        while (length := data[offset]) != 0:
            if length & 0xc0 == 0xc0:
                _offset = offset
                offset = int.from_bytes(data[offset:offset+2], byteorder='big', signed=False) & 0x3fff
                data = self.raw
                continue
            offset += 1
            part = data[offset:offset+length].decode('utf-8')
            name.append(part)
            offset += length

        name = '.'.join(name)
        if _offset != -1:
            offset = _offset + 2
        else:
            offset += 1

        if offset == len(bytes_name):
            return name
        return name, bytes_name[offset:]

    def parse_string_name(self, name):
        pass


class DNS(HTTPRequest):
    cache = dict()

    def __init__(self, hass, server='') -> None:
        self.hass = hass
        self.session = requests.Session()
        # self.server = server

    def set_domain(self, domain, ip=None):
        self.cache[domain] = ip

    def get_ip(self, domain):
        return self.cache.get(domain)

    async def async_query(self, domain):
        dns_message = DNSMessage()
        dns_message.qname = domain
        url = 'https://{}/dns-query'.format(DEFAULT_DNS_SERVER)
        headers = {'Accept': 'application/dns-message', 'Content-Type': 'application/dns-message'}
        resp = await self.async_make_request_by_requests('POST', url, data=dns_message.raw, headers=headers)
        
        if not resp.ok:
            _LOGGER.error("DNS API: Failed to query DNS server %s, status code: %s", DEFAULT_DNS_SERVER, resp.status_code)
            return
        dns_message.raw = resp.content

        ip = dns_message.rdata
        if ip is not None:
            self.cache[domain] = ip
        return ip

    async def async_update(self):
        for domain in list(self.cache.keys()):
            await self.async_query(domain)

    async def async_make_request_by_requests(self, method, url, data=None, headers=None, **kwargs):
        # session = self.session
        if method == "POST":
            func = functools.partial(
                self.session.post,
                url,
                headers=headers,
                data=data,
                verify=self.verify,
                timeout=self.timeout,
                proxies=self.proxies,
                **kwargs
            )

        resp = await self.hass.async_add_executor_job(func)
        return resp