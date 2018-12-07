from newrelic.core.attribute import (process_user_attribute,
        create_agent_attributes)
from newrelic.core.attribute_filter import DST_SPAN_EVENTS


class GenericNodeMixin(object):

    def resolve_agent_attributes(self, attribute_filter):
        if hasattr(self, '_agent_attributes_resolved'):
            return self._agent_attributes_resolved

        self._agent_attributes_resolved = create_agent_attributes(
                self.agent_attributes, attribute_filter)
        return self._agent_attributes_resolved

    def span_event(
            self, settings, base_attrs=None, parent_guid=None):
        i_attrs = base_attrs and base_attrs.copy() or {}
        i_attrs['type'] = 'Span'
        i_attrs['name'] = self.name
        i_attrs['guid'] = self.guid
        i_attrs['timestamp'] = int(self.start_time * 1000)
        i_attrs['duration'] = self.duration
        i_attrs['category'] = 'generic'

        if parent_guid:
            i_attrs['parentId'] = parent_guid

        agent_attributes = self.resolve_agent_attributes(
                settings.attribute_filter)

        a_attrs = {}
        for attr in agent_attributes:
            if attr.destinations & DST_SPAN_EVENTS:
                a_attrs[attr.name] = attr.value

        return [i_attrs, {}, a_attrs]  # intrinsics, user attrs, agent attrs

    def span_events(self,
            settings, base_attrs=None, parent_guid=None):

        yield self.span_event(
                settings,
                base_attrs=base_attrs,
                parent_guid=parent_guid)

        for child in self.children:
            for event in child.span_events(
                    settings,
                    base_attrs=base_attrs,
                    parent_guid=self.guid):
                yield event


class DatastoreNodeMixin(GenericNodeMixin):

    @property
    def name(self):
        product = self.product
        target = self.target
        operation = self.operation or 'other'

        if target:
            name = 'Datastore/statement/%s/%s/%s' % (product, target,
                    operation)
        else:
            name = 'Datastore/operation/%s/%s' % (product, operation)

        return name

    def span_event(self, *args, **kwargs):
        attrs = super(DatastoreNodeMixin, self).span_event(*args, **kwargs)
        i_attrs = attrs[0]

        i_attrs['category'] = 'datastore'
        i_attrs['component'] = self.product
        i_attrs['span.kind'] = 'client'

        if self.database_name:
            _, i_attrs['db.instance'] = process_user_attribute(
                    'db.instance', self.database_name)
        else:
            i_attrs['db.instance'] = 'Unknown'

        if self.instance_hostname:
            _, i_attrs['peer.hostname'] = process_user_attribute(
                    'peer.hostname', self.instance_hostname)
        else:
            i_attrs['peer.hostname'] = 'Unknown'

        peer_address = '%s:%s' % (
                self.instance_hostname or 'Unknown',
                self.port_path_or_id or 'Unknown')

        _, i_attrs['peer.address'] = process_user_attribute(
                'peer.address', peer_address)

        return attrs


class ExternalNodeMixin(GenericNodeMixin):

    @property
    def name(self):
        return 'External/%s/%s/%s' % (
                self.netloc, self.library, self.method or '')

    def resolve_agent_attributes(self, *args, **kwargs):
        _, self.agent_attributes['http.url'] = process_user_attribute(
                'http.url', self.url_with_path)
        return super(ExternalNodeMixin, self).resolve_agent_attributes(
                *args, **kwargs)

    def span_event(self, *args, **kwargs):
        attrs = super(ExternalNodeMixin, self).span_event(*args, **kwargs)
        i_attrs = attrs[0]

        i_attrs['category'] = 'http'
        i_attrs['span.kind'] = 'client'
        _, i_attrs['component'] = process_user_attribute(
                'component', self.library)

        if self.method:
            _, i_attrs['http.method'] = process_user_attribute(
                'http.method', self.method)

        return attrs
