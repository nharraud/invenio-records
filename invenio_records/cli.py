# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Click command-line interface for record management."""

from __future__ import absolute_import, print_function

import sys

import click

from flask import current_app
from flask_cli import with_appcontext
from invenio_db import db


def _convert_marcxml(source):
    """Convert MARC XML to JSON."""
    from dojson.contrib.marc21 import marc21
    from dojson.contrib.marc21.utils import create_record, split_blob

    for data in split_blob(source.read()):
        yield marc21.do(create_record(data))


#
# Record management commands
#

@click.group()
def records():
    """Record management commands."""


@records.command()
@click.argument('source', type=click.File('r'), default=sys.stdin, nargs='?')
@click.option('-s/--schema', default=None)
@click.option('-t/--input-type', default='json')
@click.option('--force', is_flag=True, default=False)
@with_appcontext
def create(source, schema=None, input_type='json', force=False):
    """Create new bibliographic record(s)."""
    from .tasks.api import create_record
    processor = current_app.config['RECORD_PROCESSORS'][input_type]
    if isinstance(processor, six.string_types):
        processor = import_string(processor)
    data = processor(source)

    if isinstance(data, dict):
        create_record.delay(json=data, force=force)
    else:
        from celery import group
        job = group([create_record.s(json=item, force=force) for item in data])
        result = job.apply_async()


@records.command()
@click.option('-p', '--patch', type=click.File('r'), default=sys.stdin,
              nargs='?')
@click.argument('recid', nargs='+', type=int)
@click.option('-s/--schema', default=None,
              help="URL or path to a JSON Schema.")
@with_appcontext
def patch(patch, recid=None, schema=None, input_type='jsonpatch'):
    """Patch existing bibliographic record."""
    from .api import Record

    patch_content = data.read()

    for r in recid or []:
        Record.get_record(r).patch(patch_content).commit()

    db.session.commit()
