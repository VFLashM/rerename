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

def iterslash(desc):
    if '?' not in desc:
        yield desc
        return
    for res in iterslash(desc.replace('?', '/', 1)):
        yield res
    for res in iterslash(desc.replace('?', '', 1)):
        yield res

class RenameTest(unittest.TestCase):

    def create(self, desc):
        return create(self.root, desc)

    def check(self, desc):
        parsed_desc = dict(parse(desc))
        for key in parsed_desc:
            if not key.endswith('/'):
                if parsed_desc[key] is None:
                    parsed_desc[key] = os.path.basename(key)
        self.assertEqual(parsed_desc, dict(walk(self.root)))

    def full_test_fail(self, desc, etype, **kwargs):
        before, rename = desc.split('@')
        self.create(before)
        with self.assertRaises(etype):
            rerename.rename(self.root, parse(rename), **kwargs)
        self.check(before)

    def full_test(self, desc, **kwargs):
        before, rename, after = desc.split('@')
        self.create(before)
        rerename.rename(self.root, parse(rename), **kwargs)
        self.check(after)

        # ensure that same mapping with error at the end
        # cleans up properly
        self.root = os.path.join(self.root, 'cleanup_test')
        os.mkdir(self.root)
        self.create(before)
        mapping = list(parse(rename))
        mapping.append(('missing', 'irrelevant'))
        with self.assertRaises(FileNotFoundError):
            rerename.rename(self.root, mapping, **kwargs)

    def full_test_slash(self, desc, **kwargs):
        assert '?' in desc
        base_root = self.root
        for idx, subdesc in enumerate(iterslash(desc)):
            self.root = os.path.join(base_root, str(idx))
            os.mkdir(self.root)
            self.full_test(subdesc, **kwargs)

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

    def test_files_missing(self):
        self.full_test_fail('''
            a
            b
        @        
            a = b
            d = e
        ''', FileNotFoundError, overwrite=True)


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
        ''', FileExistsError)
        

    def test_dirs(self):
        self.full_test_slash('''
            e/
            f/

            g/g1
            g/g2

            h/h1
            h/h2
        @
            e? = 4?
            g? = 5?
        @
            4/
            f/

            5/g1
            5/g2

            h/h1
            h/h2
        ''')

    def test_dirs_overwrite(self):
        self.full_test_slash('''
            c/
            d/

            e/e1
            e/e2

            f/f1
            f/f2
        @
            c? = d?
            e? = f?
        @
            d/

            f/e1
            f/e2

            f/f1
            f/f2
        ''', overwrite=True)

    def test_create_missing(self):
        self.full_test_slash('''
            a
            c/
        @
            a = b/a
            c? = d/c?
        @
            b/a
            d/c/
        ''', create_missing=True)

    def test_delete_empty(self):
        self.full_test_slash('''
            a/a1
            a/a2
      
            b/b1
            b/b2
 
            c/c1/

            d/
        @
            a/a1 = a1
            a/a2 = a2
            b/b1 = b1
            c/c1? = c1?
        @
            a1
            a2
            b1
            b/b2
            c1/
            d/
        ''', delete_empty=True)

    def test_fail_wrong_trailing_slash(self):
        self.create('a')
        with self.assertRaises(NotADirectoryError):
            rerename.rename(self.root, parse('a/ = b'))
        with self.assertRaises(NotADirectoryError):
            rerename.rename(self.root, parse('a = b/'))
        with self.assertRaises(NotADirectoryError):
            rerename.rename(self.root, parse('a/ = b/'))
        self.check('a')

    def test_fail_mixup(self):
        src = '''
            a
            b/
        '''
        self.create(src)
        with self.assertRaises(IsADirectoryError):
            rerename.rename(self.root, parse('a = b'), overwrite=True)
        self.check(src)
        for subdesc in iterslash('b? = a?'):
            with self.assertRaises(NotADirectoryError):
                rerename.rename(self.root, parse(subdesc), overwrite=True)
            self.check(src)
            
