import os
import unittest
import tempfile

import rerename

def parse(desc):
    for line in desc.splitlines():
        if line.strip():
            if '=' in line:
                key, value = line.split('=')
                yield key.strip(), value.strip()
            else:
                yield line.strip(), None

def create(root, desc):
    for name, content in parse(desc):
        path = os.path.join(root, name)
        dir = os.path.dirname(path)
        if not os.path.exists(dir):
            os.makedirs(dir)
        if path.endswith('/'):
            os.mkdir(path)
        else:
            with open(path, 'w') as f:
                f.write(content or name)

def walk(root_path):
    for root, dirs, files in os.walk(root_path):
        for name in files:
            path = os.path.join(root, name)
            rel_path = os.path.relpath(root_path, path)
            with open(path) as f:
                content = f.read()
            yield rel_path, content
        for name in dirs:
            path = os.path.join(root, name)
            rel_path = os.path.relpath(root_path, path)
            yield rel_path + '/', None

def check(root, desc):
    return dict(parse(desc)) == dict(walk(root))
    

class RenameTest(unittest.TestCase):

    def create(self, desc):
        return create(self.root, desc)

    def check(self, desc):
        return check(self.root, desc)

    def setUp(self):
        self.root_obj = tempfile.TemporaryDirectory()
        self.root = self.root_obj.name

    def tearDown(self):
        self.root_obj.cleanup()
        self.root_obj = None
        self.root = None
    
    def test_simple(self):
        self.create('''
            a
            b
            c
        ''')
        rerename.rename(self.root, parse('''
            a = 1
            b = 2
            c = 3
        '''), False)
        self.check('''
            1 = a
            2 = b
            3 = c
        ''')
