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
from rally.common import db

from browbeat_rally.db import models


@db.with_session
def get_lock(session, lock_uuid):
    lock = models.RallyLock(lock_uuid=lock_uuid)
    session.add(lock)
    session.commit()
    lock = lock.as_dict()
    return lock


@db.with_session
def lock_list(session):
    locks = []
    query = session.query(models.RallyLock)
    for lock in query.all():
        locks.append(lock.as_dict())
    return locks


@db.with_session
def release_lock(session, lock_uuid):
    session.query(models.RallyLock).filter_by(
        lock_uuid=lock_uuid).delete(
        synchronize_session=False)
