import os
import mimetypes
import base64

import sys
from google.cloud import storage
from pathlib import Path
import jinja2

APP_NAME = 'Bucket Indexer'
APP_URL = 'https://github.com/ph20/bucket-indexer'
APP_VERSION = '0.1'


GOOGLE_STORAGE = 'gs://'


class Node:
    def __init__(self, name, parent=None):
        self._name = name
        self._parent = parent
        self._modified = None

    def __repr__(self):
        return "<Node name='{}' path='{}'>".format(self._name, self.path())

    def name(self):
        return self._name

    def set_parent(self, parent):
        self._parent = parent

    def parent(self):
        return self._parent

    def set_modified(self, modified):
        self._modified = modified

    def modified(self):
        return self._modified

    def path(self):
        node_ = self
        path_str = self.name()
        while True:
            node_ = node_.parent()
            if not node_:
                return path_str
            path_str = node_.name() + '/' + path_str


class File(Node):
    def __init__(self, name, parent=None, size=0, modified=None, mime=None):
        super().__init__(name=name, parent=parent)
        self._modified = modified
        self._size = size
        self._mime = mime

    def mime(self):
        return self._mime

    def size(self):
        return self._size


class Dir(Node):
    def __init__(self, name, parent=None):
        super().__init__(name=name, parent=parent)
        self._child = []

    def __iter__(self):
        return iter(self._child)

    def add(self, node):
        node.set_parent(parent=self)
        self._child.append(node)

    def _filter(self, name=None, type_=None):
        node_list = []
        for nod in self._child:
            if type_ is None or isinstance(nod, type_):
                if name is None or name == nod.name():
                    node_list.append(nod)
        return node_list

    def size(self):
        return sum([_.size() for _ in self._filter()])

    def files(self):
        return self._filter(type_=File)

    def dirs(self):
        return self._filter(type_=Dir)

    def get_or_create(self, name: str, type_=None):
        type_ = type_ or Dir
        filtered = self._filter(name=name, type_=type_)
        if not filtered:
            node = type_(name=name)
            self.add(node)
        else:
            node = filtered[0]
        return node


class BlobObj:
    def __init__(self, name, size=0, mime=None, modified=None):
        self.name = name
        self.mime = mime
        self.modified = modified
        self.size = size

    def path(self):
        return Path(self.name)


def generate_tree(blob_list):
    root_node = Dir('')
    for blob in blob_list:
        # wrap blob obj
        parts = blob.name.split('/')[:-1]
        dir_obj = blob.name.endswith('/')

        node_ = root_node
        for dir_name in parts:
            node_ = node_.get_or_create(name=dir_name, type_=Dir)

        if dir_obj:
            node_.set_modified(blob.modified)
        else:
            node_.add(File(name=blob.path().name, mime=blob.mime, size=blob.size, modified=blob.modified))
    return root_node


def gen_node_dict(node, icon='papirus'):
    attr = ['path', 'name', 'size', 'modified', 'mime']
    dict_ = {'icon': icon, 'isDir': isinstance(node, Dir)}
    for item in attr:
        fun = getattr(node, item, None)
        if callable(fun):
            var = fun()
        elif fun is None:
            var = None
        else:
            var = fun
        dict_[item] = var
    return dict_


def gen_dir_dict(dir_node: Dir):
    dir_listing = []
    for item in dir_node:
        dict_ = gen_node_dict(item)
        dir_listing.append(dict_)
    return dir_listing


def render_fabric(theme='default', entry='index.html'):
    environment = jinja2.Environment(
        loader=jinja2.PackageLoader('bucket_indexer', 'templates/' + theme),
        autoescape=jinja2.select_autoescape(['html', 'htm'])
    )
    template = environment.get_template(entry)
    return lambda root, filelist: template.render(ig={
        'root': root,
        'files': filelist,
        'generator': {
            'name': APP_NAME,
            'version': APP_VERSION,
            'url': APP_URL
        }
    })


def main(bucket_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob_list = [BlobObj(name=_.name, mime=_.content_type, modified=_.updated, size=_.size) for _ in bucket.list_blobs()]
    tree = generate_tree(blob_list)
    render_html = render_fabric()

    def walk_and_gen(dir_node: Dir):
        dir_list = gen_dir_dict(dir_node)
        htm_index = render_html(dir_node.path(), dir_list)
        dir_path = (dir_node.path() + '/').lstrip('/')
        index_path = dir_path + 'index.html'
        print('Uploading {}'.format(index_path))
        blob = bucket.blob(index_path)
        blob.upload_from_string(htm_index, content_type='text/html')
        for dir_obj in dir_node.dirs():
            walk_and_gen(dir_obj)

    walk_and_gen(tree)


if __name__ == "__main__":
    path = sys.argv[1]
    if not path.startswith(GOOGLE_STORAGE):
        print('Incorrect schema. Suppoertd shema is {}'.format(GOOGLE_STORAGE))
        exit(1)
    main(path[len(GOOGLE_STORAGE):])
