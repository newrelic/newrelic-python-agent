# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# TODO: Put in validators
# TODO: Set up trusted certs in github actions


def test_user_read_and_permissions(user, container, permission):
    user.read()
    user.list_permissions()
    user.query_permissions("SELECT * FROM c WHERE c.id = 'test_permission'")
    user.get_permission("test_permission")
    user.replace_permission(
        "test_permission",
        {"id": "test_permission", "permissionMode": "All", "resource": container.container_link},
    )
    user.upsert_permission(
        {"id": "test_permission", "permissionMode": "Read", "resource": container.container_link},
    )


def test_async_user_read_and_permissions(loop, async_user, async_container, async_permission):
    async def _test_async_user_read_and_permissions():
        await async_user.read()
        async_user.list_permissions()
        async_user.query_permissions("SELECT * FROM c WHERE c.id = 'test_permission'")
        await async_user.get_permission("test_permission")
        await async_user.replace_permission(
            "test_permission",
            {"id": "test_permission", "permissionMode": "All", "resource": async_container.container_link},
        )
        await async_user.upsert_permission(
            {"id": "test_permission", "permissionMode": "Read", "resource": async_container.container_link},
        )
    loop.run_until_complete(_test_async_user_read_and_permissions())
