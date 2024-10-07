import time
import socket
import zlib
import re
import os
import ssl
from url import cache

working_directory = os.getcwd()
server_socket_dict = dict()
redirect_count = 0
class URL:
    def __init__(self, url):
        self.full_url = url
        self.scheme, url = url.split(":",1)
        assert self.scheme in {'http', 'https','file', 'data', 'view-source', 'about'}
        if self.scheme == 'http':
            self.port = 80
        elif self.scheme == 'https':
            self.port = 443
        if "/" not in url:
            url = url + "/"
        if self.scheme == 'http' or self.scheme == 'https':
            url = url[2:]
            self.host, url = url.split("/",1)
            if ":" in self.host:
                self.host, port = self.host.split(':',1)
                self.port = int(port)
            self.path = "/" + url
            self.request_headers = {
                "Host": f'Host: {self.host}\r\n',
                "Accept-Encoding": f'Accept-Encoding: gzip\r\n',
                'User-Agent': f'User-Agent: victor\r\n'
            }
        elif self.scheme == 'view-source':
            self.protocol, url = url.split("://")
            if self.protocol == 'http':
                self.port = 80
            elif self.protocol == 'https':
                self.port = 443
            self.host, url = url.split('/',1)
            if ":" in self.host:
                self.host, port = self.host.split(':',1)
                self.port = int(port)
            self.path = "/" + url
            self.request_headers = {
                "Host": f'Host: {self.host}\r\n',
                'Accept-Encoding': f'Accept-Encoding: gzip\r\n',
                'User-Agent': f'User-Agent: victor\r\n'
            }
        elif self.scheme=='file':
            self.path = url
        elif self.scheme == 'data':
            self.media_type, self.data = url.split(",",1)
    def handle_cache_control(self,response_headers,cache):
        match = re.search(r'max-age=\d+', response_headers['cache-control'])
        if match and 'no-store' not in response_headers['cache-control']:
                match_group = match.group()
                max_age = match_group.replace('max-age=', '')
                age = response_headers['age'] if 'age' in response_headers else 0

                cache.set_resource(self.full_url, {
                    'expires-at': int(time.time()) + int(max_age) - int(age),
                    'headers': response_headers,
                })
    def handle_transfer_encoding(self,response):
        chunks = []
        while True:
                chunk_len = response.readline().decode('utf8')
                chunk_len.replace('\r\n', '')
                chunk_len = int(chunk_len, 16)
                chunk = response.read(chunk_len)
                chunks.append(chunk)
                response.readline()
                if chunk_len == 0:
                    break
        content = b''.join(chunks)
        return content
    def request(self):
        global redirect_count
        browser_cache = cache.Cache()
        cached_resource = browser_cache.get_resource(self.full_url)
        if cached_resource:
            if browser_cache.is_resource_fresh(cached_resource):
                return cached_resource['headers']
            else:
                browser_cache.delete_resource(self.full_url)
        if self.scheme == 'file':
            chosen_file = open(working_directory + self.path, 'r')
            return chosen_file.read()
        elif self.scheme == 'data':
            return self.data
        elif self.scheme == 'about':
            return "Error! Malformed URL!"
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP
        )
        s.connect((self.host, self.port))
        if self.scheme == 'https':
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        elif self.scheme == 'view-source':
            if self.protocol == 'https':
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=self.host)
        request = f"GET {self.path} HTTP/1.0\r\n"
        for header in self.request_headers:
            request+= self.request_headers[header]
        request+= "\r\n"
        s.send(request.encode('utf8'))
        response = s.makefile("rb",newline='\r\n')
        statusline = response.readline().decode('utf8')
        status = statusline.split(" ", 2)[1]
        response_headers = store_response_headers(response)
        if 'cache-control' in response_headers:
            self.handle_cache_control(response_headers,cache)
        if 'transfer-encoding' in response_headers and response_headers['transfer-encoding'] == 'chunked':
            self.handle_transfer_encoding(response)
        else:
            if 'content-length' in response_headers:
                content = response.read(int(response_headers['content-length']))
            else:
                content = response.read()
        if 'content-encoding' in response_headers and response_headers['content-encoding'] == 'gzip':
            content = zlib.decompressobj(32).decompress(content).decode('utf8')
        else:
            content = content.decode('utf8')
        if int(status) >=300 and int(status) <400:
            redirect_location = response_headers['location']
            if redirect_location[0] == '/':
                if self.scheme == 'view-source':
                    redirect_location = f"{self.scheme}:{self.protocol}://{self.host}{self.path}"
                else:
                    redirect_location = f"{self.scheme}://{self.host}/{self.path}"
            redirect_count+=1
            if redirect_count < 10:
                new_url = URL(redirect_location)
                return new_url.request()
        s.close()
        return content
def store_response_headers(response):
    response_headers = {}
    while True:
        line = response.readline().decode('utf8')
        if line == "\r\n":
            break
        header, value = line.split(":", 1)
        response_headers[header.casefold()] = value.strip()
    return response_headers
