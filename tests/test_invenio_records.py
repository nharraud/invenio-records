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


from __future__ import absolute_import, print_function

import pytest

from click.testing import CliRunner

from flask import Flask
from flask_cli import FlaskCLI, ScriptInfo

from invenio_db import InvenioDB, db

from invenio_records import Record
from invenio_records import cli


def test_version():
    """Test version import."""
    from invenio_records import __version__
    assert __version__


def test_db():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = \
        'mysql://invenio:my123p$ss@localhost:3306/invenio'
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_ECHO'] = True
    FlaskCLI(app)
    InvenioDB(app)

    data = {'recid': 1, 'title': 'Test'}
    from invenio_records.models import Record as RM

    with app.app_context():
        try:
            RM.__table__.drop(bind=db.engine)
        except Exception:
            db.session.rollback()
            db.session.remove()
        RM.__table__.create(bind=db.engine)
        db.session.commit()

    with app.app_context():
        # db.create_all()
        assert RM.query.count() == 0

        # db.drop_all()
        Record.create(data)
        # with db.session.begin_nested():
        #    db.session.add(RM(id=1, json=data))
        db.session.commit()

        assert RM.query.count() == 1
        db.session.commit()

    with app.app_context():
        record = Record.get_record(1)
        assert record.dumps() == data
        assert Record.get_record(2) == None
        record['field'] = True
        record = record.patch([
            {'op': 'add', 'path': '/hello', 'value': ['world']}
        ])
        assert record['hello'] == ['world']
        record.commit()
        db.session.commit()

    with app.app_context():
        record2 = Record.get_record(1)
        assert record2.model.version_id == 2
        assert record2['field']
        assert record2['hello'] == ['world']
        db.session.commit()

    with app.app_context():
        record3 = Record({'recid': 1})
        record3.commit()
        db.session.commit()

        record = Record.get_record(1)
        assert record.model.version_id == 3
        assert set(record.dumps().keys()) == set(['recid'])
        db.session.commit()

    with app.app_context():
        RM.__table__.drop(bind=db.engine)
        db.session.commit()


def test_cli():
    """Test CLI."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = \
        'mysql://invenio:my123p$ss@localhost:3306/invenio'
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    FlaskCLI(app)
    InvenioDB(app)

    runner = CliRunner()
    script_info = ScriptInfo(create_app=lambda info: app)

    assert len(db.metadata.tables) == 1

    # Test merging a base another file.
    with runner.isolated_filesystem():
        result = runner.invoke(cli.records, [], obj=script_info)
        assert result.exit_code == 0

        result = runner.invoke(cli.records, ['create'], obj=script_info)
        assert result.exit_code == -1

        result = runner.invoke(cli.records, ['patch'],
                               obj=script_info)
        assert result.exit_code == -1
