class GenericNodeMixin(object):

    def span_event(
            self, base_attrs=None, parent_guid=None):
        i_attrs = base_attrs and base_attrs.copy() or {}
        i_attrs['type'] = 'Span'
        i_attrs['name'] = self.name
        i_attrs['guid'] = self.guid
        i_attrs['timestamp'] = self.start_time
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
        i_attrs['db.instance'] = self.database_name or 'Unknown'
        i_attrs['peer.address'] = '%s:%s' % (
                self.instance_hostname or 'Unknown',
                self.port_path_or_id or 'Unknown')
        i_attrs['peer.hostname'] = self.instance_hostname or 'Unknown'
        i_attrs['span.kind'] = 'client'

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
        i_attrs['http.url'] = self.url_with_path
        i_attrs['component'] = self.library

        if self.method:
            i_attrs['http.method'] = self.method

        return attrs
