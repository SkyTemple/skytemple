"""
Sentry extensions for user feedback. Can be removed and replaced by if
https://github.com/getsentry/sentry-python/pull/2442 is merged and released.
"""
#  Copyright 2020-2023 Capypara and the SkyTemple Contributors
#
#  This file is part of SkyTemple.
#
#  SkyTemple is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SkyTemple is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SkyTemple.  If not, see <https://www.gnu.org/licenses/>.
from datetime import datetime, timezone
from typing import TypedDict

from sentry_sdk import Hub
from sentry_sdk.envelope import Envelope, Item, PayloadRef
from sentry_sdk.utils import format_timestamp


class UserFeedback(TypedDict):
    event_id: str
    email: str
    name: str
    comments: str


def capture_user_feedback(feedback: UserFeedback):
    headers = {
        "event_id": feedback["event_id"],
        "sent_at": format_timestamp(datetime.now(timezone.utc)),
    }
    envelope = Envelope(headers=headers)
    envelope.add_item(Item(payload=PayloadRef(json=feedback), type="user_report"))
    client = Hub.current.client
    if client is not None:
        transport = client.transport
        if transport is not None:
            transport.capture_envelope(envelope)
