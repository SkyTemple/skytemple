"""
Module that contains profiling contexts. They are based on Sentry's transactions and spans.
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
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Protocol, ClassVar, TYPE_CHECKING, Iterable, Any

logger = logging.getLogger(__name__)


class TaggableContext(AbstractContextManager, Protocol):
    def set_tag(self, key: str, value: Any):
        ...


def record_transaction(
    name: str, tags: dict[str, Any] | None = None
) -> TaggableContext:
    return _Ctx(True, name, None, tags)


def record_span(
    op: str, description: str, tags: dict[str, Any] | None = None
) -> TaggableContext:
    return _Ctx(False, description, op, tags)


def reset_impls_cache():
    _Ctx.impls = None


class _ProfilingImplementation(ABC):
    @classmethod
    @abstractmethod
    def new(cls) -> _ProfilingImplementation | None:
        ...

    @abstractmethod
    def make_transaction(
        self, name: str, tags: dict[str, Any] | None
    ) -> TaggableContext | None:
        ...

    @abstractmethod
    def make_span(
        self, op: str, description: str, tags: dict[str, Any] | None
    ) -> TaggableContext | None:
        ...


class _LogImpl(_ProfilingImplementation):
    class LogCtx(TaggableContext):
        def __init__(self, typ: str, desc: str):
            self.typ = typ
            self.desc = desc

        def set_tag(self, key: str, value: Any):
            try:
                value_try = str(value)
            except Exception:
                value_try = "<failed __str__>"
            logger.debug(f"{self.typ}<{self.desc}> tagged: {key}={value_try}")

        def __enter__(self):
            logger.debug(f"start {self.typ}<{self.desc}>")

        def __exit__(self, __exc_type, __exc_value, __traceback):
            logger.debug(f"end {self.typ}<{self.desc}>")

    @classmethod
    def new(cls) -> _LogImpl | None:
        return _LogImpl()

    def make_transaction(
        self, name: str, tags: dict[str, Any] | None
    ) -> TaggableContext | None:
        x = self.__class__.LogCtx("transaction", name)
        if tags is not None:
            for k, v in tags.items():
                x.set_tag(k, v)
        return x

    def make_span(
        self, op: str, description: str, tags: dict[str, Any] | None
    ) -> TaggableContext | None:
        x = self.__class__.LogCtx("span", f"{op}->{description}")
        if tags is not None:
            for k, v in tags.items():
                x.set_tag(k, v)
        return x


class _SentryImpl(_ProfilingImplementation):
    import sentry_sdk
    from skytemple.core import sentry as skytemple_sentry

    @classmethod
    def new(cls) -> _SentryImpl | None:
        if cls.skytemple_sentry.is_enabled():
            return cls()
        return None

    def make_transaction(
        self, name: str, tags: dict[str, Any] | None
    ) -> TaggableContext | None:
        transact = self.sentry_sdk.start_transaction(name=name)
        if tags is not None:
            for k, v in tags.items():
                transact.set_tag(k, v)
        return transact

    def make_span(
        self, op: str, description: str, tags: dict[str, Any] | None
    ) -> TaggableContext | None:
        span = self.sentry_sdk.start_span(op=op, description=description)
        if tags is not None:
            for k, v in tags.items():
                span.set_tag(k, v)
        return span


class _Ctx(TaggableContext):
    impls: ClassVar[Iterable[_ProfilingImplementation] | None] = None

    def __init__(
        self,
        is_transaction: bool,
        name_or_desc: str,
        op: str | None,
        tags: dict[str, str] | None,
    ):
        super().__init__()
        self.is_transaction = is_transaction
        self.name_or_desc = name_or_desc
        self.op = op
        self.tags = tags
        self._entered: list[TaggableContext | None] = []
        if self.__class__.impls is None:
            self.__class__.impls = list(filter(notnone, make_impls()))
        self.instance_impls = self.__class__.impls

    def set_tag(self, key: str, value: Any):
        for entered in self._entered:
            if entered is not None:
                entered.set_tag(key, value)

    def __enter__(self):
        if self.is_transaction:
            self._entered = [
                impl.make_transaction(self.name_or_desc, self.tags)
                for impl in self.instance_impls
            ]

        else:
            if TYPE_CHECKING:
                assert self.op is not None
            self._entered = [
                impl.make_span(self.op, self.name_or_desc, self.tags)
                for impl in self.instance_impls
            ]

        for entered in self._entered:
            if entered is not None:
                entered.__enter__()

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ):
        ret_val = False
        for entered in self._entered:
            if entered is not None:
                exit_res = entered.__exit__(exc_type, exc_value, traceback)
                if exit_res is True:
                    ret_val = True
        return ret_val


def notnone(x):
    return x is not None


def make_impls():
    # return [_LogImpl(), _SentryImpl()]
    return [_SentryImpl()]
