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
        parent = os.path.dirname(path)
        if path.endswith('/'):
            parent = os.path.dirname(parent)
        if not os.path.exists(parent):
            os.makedirs(parent)
        if path.endswith('/'):
            os.mkdir(path)
        else:
            with open(path, 'w') as f:
                f.write(content or os.path.basename(name))

def walk(root_path):
    for root, dirs, files in os.walk(root_path):
        for name in files:
            path = os.path.join(root, name)
            rel_path = os.path.relpath(path, root_path)
            with open(path) as f:
                content = f.read()
            yield rel_path.replace('\\', '/'), content
        for name in dirs:
            path = os.path.join(root, name)
            if not os.listdir(path):
                rel_path = os.path.relpath(path, root_path)
                yield rel_path.replace('\\', '/') + '/', None
    

class RenameTest(unittest.TestCase):

    def create(self, desc):
        return create(self.root, desc)

    def check(self, desc):
        return check(self.root, desc)

    def check(self, desc):
        parsed_desc = dict(parse(desc))
        for key in parsed_desc:
            if not key.endswith('/'):
                if parsed_desc[key] is None:
                    parsed_desc[key] = os.path.basename(key)
        self.assertEqual(parsed_desc, dict(walk(self.root)))

    def setUp(self):
        self.root_obj = tempfile.TemporaryDirectory()
        self.root = self.root_obj.name

    def tearDown(self):
        self.root_obj.cleanup()
        self.root_obj = None
        self.root = None
    
    def test_files(self):
        self.create('''
            a
            b
            c
            d
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
            d
        ''')

    def test_dirs(self):
        src = '''
            e/
            f/

            g/g1
            g/g2

            h/h1
            h/h2
        '''
        self.create(src)

        # without tail slash
        rerename.rename(self.root, parse('''
            e = 4
            g = 5
        '''), False)
        self.check('''
            4/
            f/

            5/g1
            5/g2

            h/h1
            h/h2
        ''')

        # with tail slash
        rerename.rename(self.root, parse('''
            4/ = e
            5/ = g
        '''), False)
        self.check(src)

    # def test_overwrite(self):
    #     self.create('''
    #         a
    #         b

    #         c/
    #         d/

    #         e/e1
    #         e/e2

    #         f/f1
    #         f/f2
    #     ''')
    #     rerename.rename(self.root, parse('''
    #         a = b
    #         c = d
    #         e = f
    #     '''), True)
    #     self.check('''
    #         b = a
    #         d = c

    #         f/e1
    #         f/e2

    #         f/h1
    #         f/h2
    #     ''')
