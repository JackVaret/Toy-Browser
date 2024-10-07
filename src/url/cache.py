import time

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
