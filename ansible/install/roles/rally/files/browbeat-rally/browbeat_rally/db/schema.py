#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
import tempfile
from sqlalchemy import schema
from oslo_db import options as db_options
from browbeat_rally.db import models
from rally.common import cfg
from oslo_db.sqlalchemy import session as db_session


CONF = cfg.CONF

# rally.conf always uses stack.sqlite database
db_options.set_defaults(
            CONF, connection="sqlite:///%s/stack.sqlite" % tempfile.gettempdir())


def _create_facade_lazily():
    return db_session.EngineFacade.from_config(CONF)


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


# alternate way to create engine is
# from oslo_db.sqlalchemy import engines
# engine = engines.create_engine("sqlite:///%s/stack.sqlite" % tempfile.gettempdir())
def schema_create():
    engine = get_engine()
    metadata = schema.MetaData()
    table = schema.Table("rallylocks", metadata)
    # delete rallylocks table
    models.BASE.metadata.drop_all(engine, [table], checkfirst=True)
    # recreate rallylocks table
    models.BASE.metadata.create_all(engine)
