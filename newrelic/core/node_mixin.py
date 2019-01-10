import newrelic.core.attribute as attribute
from newrelic.core.attribute_filter import DST_SPAN_EVENTS


class GenericNodeMixin(object):
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

        a_attrs = attribute.resolve_agent_attributes(
                self.agent_attributes,
                settings.attribute_filter,
                DST_SPAN_EVENTS)

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

    @property
    def db_instance(self):
        if hasattr(self, '_db_instance'):
            return self._db_instance

        db_instance_attr = None
        if self.database_name:
            _, db_instance_attr = attribute.process_user_attribute(
                    'db.instance', self.database_name)

        self._db_instance = db_instance_attr
        return db_instance_attr

    def span_event(self, *args, **kwargs):
        self.agent_attributes['db.instance'] = self.db_instance
        attrs = super(DatastoreNodeMixin, self).span_event(*args, **kwargs)
        i_attrs = attrs[0]

        i_attrs['category'] = 'datastore'
        i_attrs['component'] = self.product
        i_attrs['span.kind'] = 'client'

        if self.instance_hostname:
            _, i_attrs['peer.hostname'] = attribute.process_user_attribute(
                    'peer.hostname', self.instance_hostname)
        else:
            i_attrs['peer.hostname'] = 'Unknown'

        peer_address = '%s:%s' % (
                self.instance_hostname or 'Unknown',
                self.port_path_or_id or 'Unknown')

        _, i_attrs['peer.address'] = attribute.process_user_attribute(
                'peer.address', peer_address)

        return attrs
