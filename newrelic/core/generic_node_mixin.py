class GenericNodeMixin(object):

    def span_event(
            self, base_attrs=None, parent_guid=None, grandparent_guid=None):
        i_attrs = base_attrs and base_attrs.copy() or {}
        i_attrs['type'] = 'Span'
        i_attrs['name'] = self.name
        i_attrs['guid'] = self.guid
        i_attrs['timestamp'] = self.start_time
        i_attrs['duration'] = self.duration
        i_attrs['category'] = 'generic'

        if parent_guid:
            i_attrs['parentId'] = parent_guid

        if grandparent_guid:
            i_attrs['grandparentId'] = grandparent_guid

        return [i_attrs, {}, {}]  # intrinsics, agent attrs, user attrs

    def span_events(self,
            stats, base_attrs=None, parent_guid=None, grandparent_guid=None):

        yield self.span_event(
                base_attrs,
                parent_guid=parent_guid,
                grandparent_guid=grandparent_guid)

        for child in self.children:
            for event in child.span_events(
                    stats,
                    base_attrs,
                    parent_guid=self.guid,
                    grandparent_guid=parent_guid):
                yield event
