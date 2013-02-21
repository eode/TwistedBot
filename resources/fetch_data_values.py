#! python
# -*- coding: utf-8 -*-
"""..this will be faster than manually copying all of the minecraft item info
from the website, and it will allow us to update in the future as things
change.
"""

from bs4 import BeautifulSoup
from urllib import urlopen
from collections import namedtuple

ITEM_ADDRESS = "http://www.minecraftwiki.net/wiki/Data_values"
ENTITY_ADDRESS = "http://www.wiki.vg/Entities"

# compared against table.tr.text.split()
entity_mob_identifier = 'Type Name x, z y'.split()
entity_object_identifier = 'Type Name x, z y'.split()
item_identifier = 'Icon Dec Hex Item'.split()
item_block_identifier = 'Icon Dec Hex Block type'.split()


EntityData = namedtuple('EntityData', 'number name width height')
ItemData = namedtuple('ItemData', 'number name props')


def download_soup(url, noisy=True):
    if noisy:
        print "Fetching name data.."
    page_data = urlopen(url).read()
    if noisy:
        print "Parsing data.."
    soup = BeautifulSoup(page_data)
    return soup


class item_page_handler(object):
    """Organizational.  Holds methods for grabbing items from the minecraft
    items page."""
    def __init__(self, address=ITEM_ADDRESS, noisy=True):
        self.address = address
        self.tables = download_soup(address, noisy)('table')
        self.blocks = self._get_block_data()
        self.items = self._get_item_data()
        self.all = self.blocks + self.items

    def _parse_item_block_data(self, table):
        """parse_block_data(block_data_table) -> list of ItemData objects
        Takes a block data table, returns the block data from that table as a
        list of ItemData objects.
        """
        result = []
        for block in table('tr'):
            if block.text.split() == item_block_identifier:
                continue
            data = block('td')
            number = int(data[1].text)
            name = data[3].text
            prop_data = data[3].sup.stripped_strings if data[3].sup else []
            props = ''.join(prop_data)
            if props:
                name = name.rsplit(props, 1)[0].strip()
            result.append(ItemData(number, name, props))
        return result

    def _get_block_data(self):
        """Takes a list of tables, returns a list of item data."""
        item_tables = [table for table in self.tables
                       if table.tr.text.split() == item_block_identifier]
        result = []
        for table in item_tables:
            result.extend(self._parse_item_block_data(table))
        return result

    def _parse_item_data(self, table):
        """parse_item_data(item_data_table) -> list of ItemData objects
        Takes an item data table, returns the item data from that table as a
        list of ItemData objects."""
        result = []
        for item in table('tr'):
            if item.text.split() == item_identifier:
                continue
            data = item('td')
            number = int(data[1].text)
            name = data[3].text
            prop_data = data[3].sup.stripped_strings if data[3].sup else []
            props = ''.join(prop_data)
            if props:
                name = name.rsplit(props, 1)[0].strip()
            result.append(ItemData(number, name, props))
        return result

    def _get_item_data(self):
        """Takes a list of tables, returns a list of item data."""
        item_tables = [table for table in self.tables
                       if table.tr.text.split() == item_identifier]
        result = []
        for table in item_tables:
            result.extend(self._parse_item_data(table))
        return result


class entity_page_handler(object):
    def __init__(self, address=ENTITY_ADDRESS, noisy=True):
        self.address = address
        self.tables = download_soup(address, noisy)('table')
        self.mobs = self._get_mob_data()
        self.objects = self._get_object_data()
        self.all = self.mobs + self.objects

    def _parse_mob_data(self, table):
        """parse_mob_entity_data(entity_data_table) -> EntityData objects list
        Takes a block data table, returns the entity data from that table as a
        list of EntityData objects.
        """
        result = []
        for t in table('tr'):
            if t.text.split() == entity_mob_identifier:
                continue
            data = t('td')
            number = int(data[0].text.strip())
            name = data[1].text.strip()
            width_text = data[2].text.split(' *')[0].rstrip('?').strip()
            width = float(width_text) if width_text else None
            height_text = data[3].text.split(' *')[0].rstrip('?').strip()
            height = float(height_text) if height_text else None
            result.append(EntityData(number, name, width, height))
        return result

    def _get_mob_data(self):
        """Takes a list of tables, returns a list of EntityData objects."""
        item_tables = [table for table in self.tables
                       if table.tr.text.split() == entity_mob_identifier]
        result = []
        for table in item_tables:
            result.extend(self._parse_mob_data(table))
        return result

    def _parse_object_data(self, table):
        """_parse_object_data(object_data_table) -> EntityData object list
        objects Takes an item data table, returns the item data from that table
        as a list of EntityData objects."""
        result = []
        for t in table('tr'):
            if t.text.split() == entity_object_identifier:
                continue
            data = t('td')
            number = int(data[0].text.strip())
            name = data[1].text.strip()
            width_text = data[2].text.split(' *')[0].rstrip('?').strip()
            width = float(width_text) if width_text else None
            height_text = data[3].text.split(' *')[0].rstrip('?').strip()
            height = float(height_text) if height_text else None
            result.append(EntityData(number, name, width, height))
        return result

    def _get_object_data(self):
        """Takes a list of tables, returns a list of item data."""
        item_tables = [table for table in self.tables
                       if table.tr.text.split() == entity_object_identifier]
        result = []
        for table in item_tables:
            result.extend(self._parse_object_data(table))
        return result


def update_data(filename, noisy=True, fmt='json'):
    """Grab the data from the minecraft site, and store it in the given file,
    using the given format.
    fmt := The format to use.  Should be one of: pickle, json, repr or python
    repr will write an 'eval'able item, and python will write an importable
    module.
    """
    items, ents = fetch_data(noisy=noisy)
    data = {'block_items': [dict(i.__dict__) for i in items.blocks],
            'nonblock_items': [dict(i.__dict__) for i in items.items],
            'mob_entities': [dict(i.__dict__) for i in ents.mobs],
            'object_entities': [dict(i.__dict__) for i in ents.objects],
            }
    if fmt == 'pickle':
        with open(filename, 'wb') as f:
            try:
                import cPickle as pickle
            except ImportError:
                import pickle
            p = pickle.Pickler(f)
            p.dump(data)
    elif fmt == 'json':
        import json
        with open(filename, 'w') as f:
            f.write(json.dumps(data, indent=4))
    elif fmt == 'repr':
        from pprint import pformat
        with open(filename, 'w') as f:
            f.write(pformat(data, indent=4))
    elif fmt == 'python':
        from pprint import pformat
        f = open(filename, 'w')
        f.write("\n")
        f.write("# autogenerated file\n\n")
        f.write("from collections import namedtuple\n")
        i = ("ItemData = namedtuple('EntityData',"
             " 'number name props')")
        e = ("EntityData = namedtuple('EntityData',"
             " 'number name width height')")
        f.write("%s\n%s\n\n" % (i, e))
        f.write("block_items = %s\n" % pformat(items.blocks, indent=4))
        f.write("nonblock_items = %s\n" % pformat(items.items, indent=4))
        f.write("mob_entities = %s\n" % pformat(ents.mobs, indent=4))
        f.write("object_entities = %s\n" % pformat(ents.objects, indent=4))
        f.close()
    else:
        raise ValueError("Unrecognized format: " + fmt)
    if noisy:
        print "Fetch complete."


def fetch_data(noisy=True):
    """fetch_data() -> ([blocks], [items], [mobs], [objects])"""
    items = item_page_handler(noisy=noisy)
    ents = entity_page_handler(noisy=noisy)
    return items, ents


def main():
    import sys
    USAGE = """Fetch the item list from the minecraft wiki.
    Usage:
        {} [filename]
    If filename is given, write to that, using the extension to guess type:
        .py: importable python module
        .json: json
        .pkl, .pickle: python pickle
        .eval: python data parsable with 'eval'
        Anything else: use json
    If not, print the information to the screen.
    """
    if len(sys.argv) > 2:
        print USAGE
        exit(1)
    elif len(sys.argv) == 2:
        for arg in sys.argv[1:]:
            if arg.lower() in ['--help', 'help', '/?', '-?', '/help']:
                print USAGE
                exit(0)
        fname = sys.argv[1]
        if fname.lower().endswith('.py'):
            fmt = 'python'
        elif fname.lower().endswith('.json'):
            fmt = 'json'
        elif fname.lower().endswith(('.pkl', '.pickle')):
            fmt = 'pickle'
        elif fname.lower().endswith('.eval'):
            fmt = 'repr'
        else:
            fmt = 'json'
        update_data(sys.argv[1], noisy=True, fmt=fmt)
        exit(0)
    object_data, entity_data = fetch_data(noisy=True)
    for line in object_data:
        print line
    for line in entity_data:
        print line


if __name__ == "__main__":
    main()

