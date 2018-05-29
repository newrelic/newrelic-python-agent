class GenericNodeMixin(object):

    def span_event(self, base_attrs=None):
        i_attrs = base_attrs and base_attrs.copy() or {}

        return [i_attrs, {}, {}]  # intrinsics, agent attrs, user attrs

    def span_events(self, stats, root=None):

        # root should only be None if this is the root transaction node

        root = root or self

        base_attrs = getattr(root, 'span_event_intrinsics', None)
        yield self.span_event(base_attrs)

        for child in self.children:
            for event in child.span_events(stats, root):
                yield event
