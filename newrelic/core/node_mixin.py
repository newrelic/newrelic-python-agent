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

from newrelic.core import attribute
from newrelic.core.attribute_filter import DST_SPAN_EVENTS, DST_TRANSACTION_SEGMENTS


class GenericNodeMixin:
    @property
    def processed_user_attributes(self):
        if hasattr(self, "_processed_user_attributes"):
            return self._processed_user_attributes

        self._processed_user_attributes = u_attrs = {}
        user_attributes = getattr(self, "user_attributes", u_attrs)
        for k, v in user_attributes.items():
            k, v = attribute.process_user_attribute(k, v)
            # Only record the attribute if it passes processing.
            # Failures return (None, None).
            if k:
                u_attrs[k] = v
        return u_attrs

    def get_trace_segment_params(self, settings, params=None):
        _params = attribute.resolve_agent_attributes(
            self.agent_attributes, settings.attribute_filter, DST_TRANSACTION_SEGMENTS
        )

        if params:
            _params.update(params)

        _params.update(
            attribute.resolve_user_attributes(
                self.processed_user_attributes, settings.attribute_filter, DST_TRANSACTION_SEGMENTS
            )
        )

        _params["exclusive_duration_millis"] = 1000.0 * self.exclusive
        return _params

    def _span_event_full_granularity(
        self, settings, base_attrs=None, parent_guid=None, attr_class=dict, ct_exit_spans=None
    ):
        i_attrs = (base_attrs and base_attrs.copy()) or attr_class()
        i_attrs["type"] = "Span"
        i_attrs["name"] = i_attrs.get("name") or self.name
        i_attrs["guid"] = self.guid
        i_attrs["timestamp"] = int(self.start_time * 1000)
        i_attrs["duration"] = self.duration
        i_attrs["category"] = i_attrs.get("category") or "generic"

        if parent_guid:
            i_attrs["parentId"] = parent_guid

        a_attrs = attribute.resolve_agent_attributes(
            self.agent_attributes, settings.attribute_filter, DST_SPAN_EVENTS, attr_class=attr_class
        )

        u_attrs = attribute.resolve_user_attributes(
            self.processed_user_attributes, settings.attribute_filter, DST_SPAN_EVENTS, attr_class=attr_class
        )
        # intrinsics, user attrs, agent attrs
        return [i_attrs, u_attrs, a_attrs]

    def _span_event_partial_granularity_reduced(
        self, settings, base_attrs=None, parent_guid=None, attr_class=dict, ct_exit_spans=None
    ):
        if ct_exit_spans is None:
            ct_exit_spans = {"instrumented": 0, "kept": 0, "dropped_ids": 0}

        ct_exit_spans["instrumented"] += 1

        i_attrs = (base_attrs and base_attrs.copy()) or attr_class()
        i_attrs["type"] = "Span"
        i_attrs["name"] = i_attrs.get("name") or self.name
        i_attrs["guid"] = self.guid
        i_attrs["timestamp"] = int(self.start_time * 1000)
        i_attrs["duration"] = self.duration
        i_attrs["category"] = i_attrs.get("category") or "generic"

        if parent_guid:
            i_attrs["parentId"] = parent_guid

        a_attrs = attribute.resolve_agent_attributes(
            self.agent_attributes, settings.attribute_filter, DST_SPAN_EVENTS, attr_class=attr_class
        )
        u_attrs = attribute.resolve_user_attributes(
            self.processed_user_attributes, settings.attribute_filter, DST_SPAN_EVENTS, attr_class=attr_class
        )

        # If this is an entry span, add `nr.pg` to indicate transaction is partial
        # granularity sampled.
        if i_attrs.get("nr.entryPoint"):
            i_attrs["nr.pg"] = True
        # If this is the entry node or an LLM span always return it.
        if i_attrs.get("nr.entryPoint") or i_attrs["name"].startswith("Llm/"):
            ct_exit_spans["kept"] += 1
            return [i_attrs, u_attrs, a_attrs]
        exit_span_attrs_present = attribute.SPAN_ENTITY_RELATIONSHIP_ATTRIBUTES & set(a_attrs)
        # If the span is not an exit span, skip it by returning None.
        if not exit_span_attrs_present:
            return None
        # If the span is an exit span and we are in reduced mode (meaning no attribute dropping),
        # just return the exit span as is.
        ct_exit_spans["kept"] += 1
        return [i_attrs, u_attrs, a_attrs]

    def _span_event_partial_granularity_essential(
        self, settings, base_attrs=None, parent_guid=None, attr_class=dict, ct_exit_spans=None
    ):
        if ct_exit_spans is None:
            ct_exit_spans = {"instrumented": 0, "kept": 0, "dropped_ids": 0}

        ct_exit_spans["instrumented"] += 1

        i_attrs = (base_attrs and base_attrs.copy()) or attr_class()
        i_attrs["type"] = "Span"
        i_attrs["name"] = i_attrs.get("name") or self.name
        i_attrs["guid"] = self.guid
        i_attrs["timestamp"] = int(self.start_time * 1000)
        i_attrs["duration"] = self.duration
        i_attrs["category"] = i_attrs.get("category") or "generic"

        if parent_guid:
            i_attrs["parentId"] = parent_guid

        a_attrs = self.agent_attributes

        a_attrs_set = set(a_attrs)
        exit_span_attrs_present = attribute.SPAN_ENTITY_RELATIONSHIP_ATTRIBUTES & a_attrs_set
        exit_span_error_attrs_present = attribute.SPAN_ERROR_ATTRIBUTES & a_attrs_set
        # If this is an entry span, add `nr.pg` to indicate transaction is partial
        # granularity sampled.
        if i_attrs.get("nr.entryPoint"):
            i_attrs["nr.pg"] = True
        # If this is the entry node or an LLM span always return it.
        if i_attrs.get("nr.entryPoint") or i_attrs["name"].startswith("Llm/"):
            ct_exit_spans["kept"] += 1
            # Only keep entity-synthesis and error agent attributes, and intrinsics.
            a_minimized_attrs = attribute.resolve_agent_attributes(
                {key: a_attrs[key] for key in exit_span_attrs_present | exit_span_error_attrs_present},
                settings.attribute_filter,
                DST_SPAN_EVENTS,
                attr_class=attr_class,
            )
            return [i_attrs, {}, a_minimized_attrs]
        # If the span is not an exit span, skip it by returning None.
        if not exit_span_attrs_present:
            return None
        ct_exit_spans["kept"] += 1
        # Only keep entity-synthesis, and error agent attributes, and intrinsics.
        a_minimized_attrs = attribute.resolve_agent_attributes(
            {key: a_attrs[key] for key in exit_span_attrs_present | exit_span_error_attrs_present},
            settings.attribute_filter,
            DST_SPAN_EVENTS,
            attr_class=attr_class,
        )
        return [i_attrs, {}, a_minimized_attrs]

    def _span_event_partial_granularity_compact(
        self, settings, base_attrs=None, parent_guid=None, attr_class=dict, ct_exit_spans=None
    ):
        if ct_exit_spans is None:
            ct_exit_spans = {"instrumented": 0, "kept": 0, "dropped_ids": 0}

        ct_exit_spans["instrumented"] += 1

        i_attrs = (base_attrs and base_attrs.copy()) or attr_class()
        i_attrs["type"] = "Span"
        i_attrs["name"] = i_attrs.get("name") or self.name
        i_attrs["guid"] = self.guid
        i_attrs["timestamp"] = int(self.start_time * 1000)
        i_attrs["duration"] = self.duration
        i_attrs["category"] = i_attrs.get("category") or "generic"

        if parent_guid:
            i_attrs["parentId"] = parent_guid

        a_attrs = self.agent_attributes

        a_attrs_set = set(a_attrs)
        exit_span_attrs_present = attribute.SPAN_ENTITY_RELATIONSHIP_ATTRIBUTES & a_attrs_set
        exit_span_error_attrs_present = attribute.SPAN_ERROR_ATTRIBUTES & a_attrs_set
        # If this is an entry span, add `nr.pg` to indicate transaction is partial
        # granularity sampled.
        if i_attrs.get("nr.entryPoint"):
            i_attrs["nr.pg"] = True
        # If this is the entry node or an LLM span always return it.
        if i_attrs.get("nr.entryPoint") or i_attrs["name"].startswith("Llm/"):
            ct_exit_spans["kept"] += 1
            # Only keep entity-synthesis and error agent attributes, and intrinsics.
            a_minimized_attrs = attribute.resolve_agent_attributes(
                {key: a_attrs[key] for key in exit_span_attrs_present | exit_span_error_attrs_present},
                settings.attribute_filter,
                DST_SPAN_EVENTS,
                attr_class=attr_class,
            )
            return [i_attrs, {}, a_minimized_attrs]
        # If the span is not an exit span, skip it by returning None.
        if not exit_span_attrs_present:
            return None
        a_minimized_attrs = attribute.resolve_agent_attributes(
            {key: a_attrs[key] for key in exit_span_attrs_present | exit_span_error_attrs_present},
            settings.attribute_filter,
            DST_SPAN_EVENTS,
            attr_class=attr_class,
        )

        # If the span is an exit span but span compression (compact) is enabled,
        # we need to check for uniqueness before returning it.
        # Combine all the entity relationship attr values into a frozenset of tuples to be
        # used as the hash to check for uniqueness.
        span_attrs_hash = hash(frozenset((key, a_minimized_attrs[key]) for key in exit_span_attrs_present if key in a_minimized_attrs))
        # If this is a new exit span, add it to the known ct_exit_spans and
        # return it.
        if span_attrs_hash not in ct_exit_spans:
            # nr.ids is the list of span guids that share this unqiue exit span.
            i_attrs["nr.ids"] = []
            i_attrs["nr.durations"] = self.duration
            ct_exit_spans[span_attrs_hash] = [i_attrs, a_minimized_attrs]
            ct_exit_spans["kept"] += 1
            # Only keep entity-synthesis, and error agent attributes, and intrinsics.
            return [i_attrs, {}, a_minimized_attrs]
        # If this is an exit span we've already seen, add the error attributes
        # (last occurring error takes precedence), add it's guid to the list
        # of ids on the seen span, compute the new duration & start time, and
        # return None.
        exit_span = ct_exit_spans[span_attrs_hash]
        exit_span[1].update(
            attr_class(
                {key: a_minimized_attrs[key] for key in exit_span_error_attrs_present if key in a_minimized_attrs}
            )
        )
        # Max size for `nr.ids` = 1024. Max length = 63 (each span id is 16 bytes + 8 bytes for list type).
        if len(exit_span[0]["nr.ids"]) < 63:
            exit_span[0]["nr.ids"].append(self.guid)
        else:
            ct_exit_spans["dropped_ids"] += 1

        # Compute the new start and end time for all compressed spans and use
        # that to set the duration for all compressed spans.
        current_start_time = exit_span[0]["timestamp"]
        current_end_time = (
            exit_span[0]["timestamp"] / 1000 + exit_span[0]["nr.durations"]
        )
        new_start_time = i_attrs["timestamp"]
        new_end_time = i_attrs["timestamp"] / 1000 + i_attrs["duration"]
        set_start_time = min(new_start_time, current_start_time)
        # If the new span starts after the old span's end time or the new span
        # ends before the current span starts; add the durations.
        if current_end_time < new_start_time / 1000 or new_end_time < current_start_time / 1000:
            set_duration = exit_span[0]["nr.durations"] + i_attrs["duration"]
        # Otherwise, if the new and old span's overlap in time, use the newest
        # end time and subtract the start time from it to calculate the new
        # duration.
        else:
            set_duration = max(current_end_time, new_end_time) - set_start_time / 1000
        exit_span[0]["timestamp"] = set_start_time
        exit_span[0]["nr.durations"] = set_duration

    PARTIAL_GRANULARITY_SPAN_EVENT_METHODS = {  # noqa: RUF012
        "reduced": _span_event_partial_granularity_reduced,
        "essential": _span_event_partial_granularity_essential,
        "compact": _span_event_partial_granularity_compact,
    }

    def span_event(
        self,
        settings,
        base_attrs=None,
        parent_guid=None,
        attr_class=dict,
        partial_granularity_sampled=False,
        ct_exit_spans=None,
    ):
        if partial_granularity_sampled:
            partial_type = settings.distributed_tracing.sampler.partial_granularity.type
            return self.PARTIAL_GRANULARITY_SPAN_EVENT_METHODS.get(partial_type, PARTIAL_GRANULARITY_SPAN_EVENT_METHODS["essential"])(
                self=self,
                settings=settings,
                base_attrs=base_attrs,
                parent_guid=parent_guid,
                attr_class=attr_class,
                ct_exit_spans=ct_exit_spans,
            )

        return self._span_event_full_granularity(
            settings=settings,
            base_attrs=base_attrs,
            parent_guid=parent_guid,
            attr_class=attr_class,
            ct_exit_spans=ct_exit_spans,
        )

    def span_events(
        self,
        settings,
        base_attrs=None,
        parent_guid=None,
        attr_class=dict,
        partial_granularity_sampled=False,
        ct_exit_spans=None,
    ):
        span = self.span_event(
            settings,
            base_attrs=base_attrs,
            parent_guid=parent_guid,
            attr_class=attr_class,
            partial_granularity_sampled=partial_granularity_sampled,
            ct_exit_spans=ct_exit_spans,
        )
        parent_id = parent_guid
        if span:  # In partial granularity tracing, span will be None if the span is an inprocess span or repeated exit span.
            yield span
            # Compressed spans are always reparented onto the entry span.
            if settings.distributed_tracing.sampler.partial_granularity.type != "compact" or span[0].get(
                "nr.entryPoint"
            ):
                parent_id = self.guid
        for child in self.children:
            for event in child.span_events(
                settings,
                base_attrs=base_attrs,
                parent_guid=parent_id,
                attr_class=attr_class,
                partial_granularity_sampled=partial_granularity_sampled,
                ct_exit_spans=ct_exit_spans,
            ):
                if event:  # event will be None if the span is an inprocess span or repeated exit span.
                    yield event


class DatastoreNodeMixin(GenericNodeMixin):
    @property
    def name(self):
        product = self.product
        target = self.target
        operation = self.operation or "other"

        if target:
            name = f"Datastore/statement/{product}/{target}/{operation}"
        else:
            name = f"Datastore/operation/{product}/{operation}"

        return name

    @property
    def db_instance(self):
        if hasattr(self, "_db_instance"):
            return self._db_instance

        db_instance_attr = None
        if self.database_name:
            _, db_instance_attr = attribute.process_user_attribute("db.instance", self.database_name)

        self._db_instance = db_instance_attr
        return db_instance_attr

    def span_event(
        self,
        settings,
        base_attrs=None,
        parent_guid=None,
        attr_class=dict,
        partial_granularity_sampled=False,
        ct_exit_spans=None,
    ):
        a_attrs = self.agent_attributes
        a_attrs["db.instance"] = self.db_instance
        i_attrs = (base_attrs and base_attrs.copy()) or attr_class()

        i_attrs["category"] = "datastore"
        i_attrs["span.kind"] = "client"

        if self.product:
            i_attrs["component"] = a_attrs["db.system"] = attribute.process_user_attribute("db.system", self.product)[1]
        if self.operation:
            a_attrs["db.operation"] = attribute.process_user_attribute("db.operation", self.operation)[1]
        if self.target:
            a_attrs["db.collection"] = attribute.process_user_attribute("db.collection", self.target)[1]

        if self.instance_hostname:
            peer_hostname = attribute.process_user_attribute("peer.hostname", self.instance_hostname)[1]
        else:
            peer_hostname = "Unknown"

        a_attrs["peer.hostname"] = a_attrs["server.address"] = peer_hostname

        peer_address = f"{peer_hostname}:{self.port_path_or_id or 'Unknown'}"

        a_attrs["peer.address"] = attribute.process_user_attribute("peer.address", peer_address)[1]

        # Attempt to treat port_path_or_id as an integer, fallback to not including it
        try:
            a_attrs["server.port"] = int(self.port_path_or_id)
        except Exception:
            pass

        base_span_event = super().span_event(
            settings,
            base_attrs=i_attrs,
            parent_guid=parent_guid,
            attr_class=attr_class,
            partial_granularity_sampled=partial_granularity_sampled,
            ct_exit_spans=ct_exit_spans,
        )

        if self.span_link_events or self.span_event_events:
            return [base_span_event, self.span_link_events, self.span_event_events]
        return base_span_event
