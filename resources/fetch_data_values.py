#! python
# -*- coding: utf-8 -*-
"""..this will be faster than manually copying all of the minecraft item info
from the website, and it will allow us to update in the future as things
change.
"""

from bs4 import BeautifulSoup
from urllib import urlopen
from collections import namedtuple

ADDRESS = "http://www.minecraftwiki.net/wiki/Data_values"

# compared against table.tr.text.split()
item_data_identifier = 'Icon Dec Hex Item'.split()
block_data_identifier = 'Icon Dec Hex Block type'.split()
entity_data_identifier = 'Id Hex Icon Egg Entity Savegame ID'.split()
entity_table_subtitles = [u'Drops',
                          u'Immobile & projectiles',
                          u'Blocks',
                          u'Vehicles',
                          u'Generic',
                          u'Hostile mobs',
                          u'Passive mobs',
                          u'NPCs',
                          u'Other']


ItemData = namedtuple('ItemData', 'image_url number name props')
EntityData = namedtuple('EntityData', 'number name')


def parse_block_data(table):
    """parse_block_data(block_data_table) -> list of ItemData objects
    Takes a block data table, returns the block data from that table as a list
    of ItemData objects.
    """
    result = []
    for t in table('tr'):
        if t.text.split() == block_data_identifier:
            continue
        data = t('td')
        image_url = data[0].img['src'] if data[0].img else ''
        number = int(data[1].text)
        name = data[3].text
        props = ''.join(data[3].sup.stripped_strings) if data[3].sup else ''
        if props:
            name = name.rsplit(props, 1)[0].strip()
        result.append(ItemData(image_url, number, name, props))
    return result


def get_block_data(tables):
    """Takes a list of tables, returns a list of item data."""
    item_tables = [table for table in tables
                   if table.tr.text.split() == block_data_identifier]
    result = []
    for table in item_tables:
        result.extend(parse_block_data(table))
    return result


def parse_entity_data(table):
    """parse_entity_data(entity_data_table) -> list of EntityData objects
    Takes a block data table, returns the entity data from that table as a list
    of EntityData objects.
    """
    result = []
    for t in table('tr'):
        if t.text.split() == entity_data_identifier:
            continue
        if t.text.strip() in entity_table_subtitles:
            continue
        data = t('td')
        number = int(data[0].text)
        name = data[4].text
        from time import time
        result.append(EntityData(number, name))
    return result


def get_entity_data(tables):
    """Takes a list of tables, returns a list of EntityData objects."""
    item_tables = [table for table in tables
                   if table.tr.text.split() == entity_data_identifier]
    result = []
    for table in item_tables:
        result.extend(parse_entity_data(table))
    return result


def parse_item_data(table):
    """parse_item_data(item_data_table) -> list of ItemData objects
    Takes an item data table, returns the item data from that table as a list of
    ItemData objects."""
    result = []
    for t in table('tr'):
        if t.text.split() == item_data_identifier:
            continue
        data = t('td')
        image_url = data[0].img['src']
        number = int(data[1].text)
        name = data[3].text
        props = ''.join(data[3].sup.stripped_strings) if data[3].sup else ''
        if props:
            name = name.rsplit(props, 1)[0].strip()
        result.append(ItemData(image_url, number, name, props))
    return result


def get_item_data(tables):
    """Takes a list of tables, returns a list of item data."""
    item_tables = [table for table in tables
                   if table.tr.text.split() == item_data_identifier]
    result = []
    for table in item_tables:
        result.extend(parse_item_data(table))
    return result


def update_data(filename, noisy=True, fmt='json'):
    """Grab the data from the minecraft site, and store it in the given file,
    using the given format.
    fmt := The format to use.  Should be one of: pickle, json, repr or python
    repr will write an 'eval'able item, and python will write an importable
    module.
    """
    items, entities = fetch_data(noisy=noisy)
    if fmt == 'pickle':
        with open(filename, 'wb') as f:
            try:
                import cPickle as pickle
            except ImportError:
                import pickle
            p = pickle.Pickler(f)
            p.dump(items)
            p.dump(entities)
    elif fmt == 'json':
        import json
        with open(filename, 'w') as f:
            data = {
                'items': [dict(i.__dict__) for i in items],
                'entities': [dict(i.__dict__) for i in entities]}
            f.write(json.dumps(data, indent=4))
    elif fmt == 'repr':
        from pprint import pformat
        data = {
            'items': [dict(i.__dict__) for i in items],
            'entities': [dict(i.__dict__) for i in entities]}
        with open(filename, 'w') as f:
            f.write(pformat(data, indent=4))
    elif fmt == 'python':
        from pprint import pformat
        f = open(filename, 'w')
        f.write("\n")
        f.write("# autogenerated file\n\n")
        f.write("from collections import namedtuple\n")
        e = "EntityData = namedtuple('EntityData', 'number name')"
        i = "ItemData = namedtuple('ItemData', 'image_url number name props')"
        f.write("%s\n%s\n\n" % (e, i))
        f.write("items = %s\n" % pformat(items, indent=4))
        f.write("entities = %s\n" % pformat(entities, indent=4))
        f.close()
    else:
        raise ValueError("Unrecognized format: "+fmt)
    if noisy:
        print "Fetch complete."

def download_soup(url, noisy=True):
    if noisy:
        print "Fetching name data.."
    page_data = urlopen(url).read()
    if noisy:
        print "Parsing data.."
    soup = BeautifulSoup(page_data)
    return soup

def fetch_data(noisy=True):
    tables = download_soup(ADDRESS)('table')
    item_data = get_item_data(tables)
    block_data = get_block_data(tables)
    entity_data = get_entity_data(tables)
    return block_data + item_data, entity_data


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
        elif fname.lower().endswith(('.pkl', '.pickle'):
            fmt = 'pickle'
        elif fname.lower().endswith('.eval'):
            fmt = 'repr'
        else:
            fmt = 'json'
        update_data(sys.argv[1], noisy=True, fmt=fmt)
        exit(0)
    item_data, entity_data = fetch_data(noisy=True)
    for line in item_data:
        print line
    for line in entity_data:
        print line


if __name__ == "__main__":
    main()

