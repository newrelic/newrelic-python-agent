from newrelic.core.attribute import process_user_attribute


class GenericNodeMixin(object):

    def span_event(
            self, base_attrs=None, parent_guid=None):
        i_attrs = base_attrs and base_attrs.copy() or {}
        i_attrs['type'] = 'Span'
        i_attrs['name'] = self.name
        i_attrs['guid'] = self.guid
        i_attrs['timestamp'] = int(self.start_time * 1000)
        i_attrs['duration'] = self.duration
        i_attrs['category'] = 'generic'

        if parent_guid:
            i_attrs['parentId'] = parent_guid

        return [i_attrs, {}, {}]  # intrinsics, agent attrs, user attrs

    def span_events(self,
            stats, base_attrs=None, parent_guid=None):

        yield self.span_event(
                base_attrs=base_attrs,
                parent_guid=parent_guid)

        for child in self.children:
            for event in child.span_events(
                    stats,
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

    def span_event(self, *args, **kwargs):
        attrs = super(ExternalNodeMixin, self).span_event(*args, **kwargs)
        i_attrs = attrs[0]

        i_attrs['category'] = 'http'
        i_attrs['span.kind'] = 'client'
        _, i_attrs['http.url'] = process_user_attribute(
                'http.url', self.url_with_path)
        _, i_attrs['component'] = process_user_attribute(
                'component', self.library)

        if self.method:
            _, i_attrs['http.method'] = process_user_attribute(
                'http.method', self.method)

        return attrs
