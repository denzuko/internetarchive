"""Retrieve and modify Archive.org metadata.

usage:
    ia metadata <identifier>... [--modify=<key:value>...] [--target=<target>]
                                [--priority=<priority>]
    ia metadata <identifier>... [--append=<key:value>...] [--priority=<priority>]
    ia metadata <identifier>... [--exists | --formats]
    ia metadata --spreadsheet=<metadata.csv> [--priority=<priority>]
                                             [--modify=<key:value>...]
    ia metadata --help

options:
    -h, --help
    -m, --modify=<key:value>          Modify the metadata of an item.
    -t, --target=<target>             The metadata target to modify.
    -a, --append=<key:value>          Append metadata to an element.
    -s, --spreadsheet=<metadata.csv>  Modify metadata in bulk using a spreadsheet as
                                      input.
    -e, --exists                      Check if an item exists
    -F, --formats                     Return the file-formats the given item contains.
    -p, --priority=<priority>         Set the task priority.
"""
from __future__ import absolute_import, unicode_literals, print_function
import sys
import os
try:
    import ujson as json
except ImportError:
    import json
import csv

from docopt import docopt, printable_usage
from schema import Schema, SchemaError, Or, And
import six

from internetarchive.cli.argparser import get_args_dict


def modify_metadata(item, metadata, args):
    append = True if args['--append'] else False
    r = item.modify_metadata(metadata, target=args['--target'], append=append,
                             priority=args['--priority'])
    if not r.json()['success']:
        error_msg = r.json()['error']
        sys.stderr.write(u'{0} - error ({1}): {2}\n'.format(item.identifier,
                                                            r.status_code, error_msg))
        return r
    sys.stdout.write('{0} - success: {1}\n'.format(item.identifier,
                                                   r.json()['log']))
    return r


def main(argv, session):
    args = docopt(__doc__, argv=argv)

    # Validate args.
    s = Schema({
        six.text_type: bool,
        '<identifier>': list,
        '--modify': list,
        '--append': list,
        '--spreadsheet': Or(None, And(lambda f: os.path.exists(f),
                            error='<file> should be a readable file or directory.')),
        '--target': Or(None, str),
        '--priority': None,
    })
    try:
        args = s.validate(args)
    except SchemaError as exc:
        print('{0}\n{1}'.format(str(exc), printable_usage(__doc__)), file=sys.stderr)
        sys.exit(1)

    formats = set()
    responses = []

    for i, identifier in enumerate(args['<identifier>']):
        item = session.get_item(identifier)

        # Check existence of item.
        if args['--exists']:
            if item.exists:
                responses.append(True)
                sys.stdout.write('{0} exists\n'.format(identifier))
            else:
                responses.append(False)
                sys.stderr.write('{0} does not exist\n'.format(identifier))
            if (i + 1) == len(args['<identifier>']):
                if all(r is True for r in responses):
                    sys.exit(0)
                else:
                    sys.exit(1)

        # Modify metadata.
        elif args['--modify'] or args['--append']:
            metadata_args = args['--modify'] if args['--modify'] else args['--append']
            metadata = get_args_dict(metadata_args)
            responses.append(modify_metadata(item, metadata, args))
            if (i + 1) == len(args['<identifier>']):
                if all(r.status_code == 200 for r in responses):
                    sys.exit(0)
                else:
                    sys.exit(1)

        # Get metadata.
        elif args['--formats']:
            for f in item.get_files():
                formats.add(f.format)
            if (i + 1) == len(args['<identifier>']):
                sys.stdout.write('\n'.join(formats) + '\n')

        # Dump JSON to stdout.
        else:
            metadata = json.dumps(item.item_metadata)
            sys.stdout.write(metadata + '\n')

    # Edit metadata for items in bulk, using a spreadsheet as input.
    if args['--spreadsheet']:
        if not args['--priority']:
            args['--priority'] = -5
        spreadsheet = csv.DictReader(open(args['--spreadsheet'], 'rU'))
        responses = []
        for row in spreadsheet:
            if not row['identifier']:
                continue
            item = session.get_item(row['identifier'])
            if row.get('file'):
                del row['file']
            metadata = dict((k.lower(), v) for (k, v) in row.items() if v)
            responses.append(modify_metadata(item, metadata, args))

        if all(r.status_code == 200 for r in responses):
            sys.exit(0)
        else:
            sys.exit(1)

    sys.exit(0)