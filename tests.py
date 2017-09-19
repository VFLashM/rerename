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

    def full_test(self, desc, **kwargs):
        before, rename, after = desc.split('@')
        self.create(before)
        rerename.rename(self.root, parse(rename), **kwargs)
        self.check(after)

    def full_test_fail(self, desc, etype, **kwargs):
        before, rename = desc.split('@')
        self.create(before)
        with self.assertRaises(etype):
            rerename.rename(self.root, parse(rename), **kwargs)
        self.check(before)

    def setUp(self):
        self.root_obj = tempfile.TemporaryDirectory()
        self.root = self.root_obj.name

    def tearDown(self):
        self.root_obj.cleanup()
        self.root_obj = None
        self.root = None
    
    def test_files(self):
        self.full_test('''
            a
            b
            c
            d
        @            
            a = 1
            b = 2
            c = 3
        @
            1 = a
            2 = b
            3 = c
            d
        ''')

    def test_files_overwrite(self):
        self.full_test('''
            a
            b
        @            
            a = b
        @
            b = a
        ''', overwrite=True)

    def test_fail_empty(self):
        self.full_test_fail('''
            a
            b
            c
            d
        @     
            b=1
            c=
        ''', ValueError)

    def test_fail_dup(self):
        self.full_test_fail('''
            a
            b
            c
            d
        @     
            a = b
            c = 1
            d = 1
        ''', ValueError, overwrite=True)

    def test_fail_overwrite(self):
        self.full_test_fail('''
            a
            b
            c
            d
        @     
            b=1
            c=d
        ''', OSError)
        

    def _test_dirs(self, before, after):
        self.full_test('''
            e/
            f/

            g/g1
            g/g2

            h/h1
            h/h2
        @
            e{before} = 4{after}
            g{before} = 5{after}
        @
            4/
            f/

            5/g1
            5/g2

            h/h1
            h/h2
        '''.format(before=before, after=after))

    # ensure dirs rename works regardless of trailing slash
    def test_dirs_nn(self):
        self._test_dirs('', '')
    def test_dirs_sn(self):
        self._test_dirs('/', '')
    def test_dirs_ns(self):
        self._test_dirs('', '/')
    def test_dirs_ss(self):
        self._test_dirs('/', '/')
                

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
    #     @
    #         a = b
    #         c = d
    #         e = f
    #     @
    #         b = a

    #         d/

    #         f/e1
    #         f/e2

    #         f/h1
    #         f/h2
    #     ''')
