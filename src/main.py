import socket
import ssl
import os
import time
import re
import zlib
import tkinter
working_directory = os.getcwd()
server_socket_dict = dict()
redirect_count = 0
WIDTH,HEIGHT = 800,600
class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()
    def load(self,url):
        self.canvas.create_rectangle(10,20,400,300)
        self.canvas.create_oval(100, 100, 150, 150)
        self.canvas.create_text(200, 150, text="Hi!")
class URL:
    def __init__(self, url):
        self.full_url = url
        self.scheme, url = url.split(":",1)
        assert self.scheme in {'http', 'https','file', 'data', 'view-source'}
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
        print('modifying content')
        content = b''.join(chunks)
        return content
    def request(self):
        global redirect_count
        cache = Cache()
        cached_resource = cache.get_resource(self.full_url)
        if cached_resource:
            if cache.is_resource_fresh(cached_resource):
                return cached_resource['headers']
            else:
                cache.delete_resource(self.full_url)
        if self.scheme == 'file':
            chosen_file = open(working_directory + self.path, 'r')
            return chosen_file.read()
        elif self.scheme == 'data':
            return self.data
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
        version, status, explanation = statusline.split(" ", 2)
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
def show(body, mode='r'):
    entity = ''
    creating_entity = False
    if mode =="r":
        in_tag = False
        for c in body:
            if c =='&':
                creating_entity = True
                entity+=c
            if c== "<":
                in_tag = True
            elif c == ">":
                in_tag = False
            elif not in_tag:
                    if creating_entity:
                        if c != 'l' and c != 'g':
                            creating_entity = False
                            print(entity + c,end="")
                            entity = ''
                        else:
                            entity+=c
                            if len(entity) ==4:
                                if entity == '&lt;':
                                    print('<')
                                    creating_entity = False
                                    entity = ''
                                elif entity == '&gt;':
                                    print('>')
                                    creating_entity = False
                                    entity = ''
                    else:
                        print(c, end="")
    elif mode =='s':
        print(body)

class Cache:
    def __init__(self):
        self.db = {}

    @staticmethod
    def is_resource_fresh(resource):
        return 'expires-at' in resource and resource['expires-at'] > time.time()

    def get_resource(self,url):
        return self.db[url] if url in self.db else None

    def set_resource(self,url, resource):
        self.db[url] = resource

    def delete_resource(self,url):
        del self.db[url]
def store_response_headers(response):
    response_headers = {}
    while True:
        line = response.readline().decode('utf8')
        if line == "\r\n":
            break
        header, value = line.split(":", 1)
        response_headers[header.casefold()] = value.strip()
    return response_headers
def load(url):
    global redirect_count
    body = url.request()
    if url.scheme == 'view-source':
        show(body,'s')
        redirect_count = 0
    else:
        show(body)
        redirect_count = 0

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for i in range(1,len(sys.argv)):
            load(URL(f"{sys.argv[i]}"))
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
