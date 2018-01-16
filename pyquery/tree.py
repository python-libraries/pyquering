import copy


class Node(object):

    def __init__(self, children=None, connector=None, negated=False):
        self.children = children[:] if children else []
        self.connector = connector or self.default
        self.negated = negated

    @classmethod
    def _new_instance(cls, children=None, connector=None, negated=False):
        obj = Node(children, connector, negated)
        obj.__class__ = cls
        return obj

    def __str__(self):
        if self.negated:
            return '(NOT (%s: %s))' % (self.connector, ', '.join(str(c) for c
                    in self.children))
        return '(%s: %s)' % (self.connector, ', '.join(str(c) for c in
                self.children))

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self)

    def __deepcopy__(self, memodict):
        obj = Node(connector=self.connector, negated=self.negated)
        obj.__class__ = self.__class__
        obj.children = copy.deepcopy(self.children, memodict)
        return obj

    def __len__(self):
        return len(self.children)

    def __bool__(self):
        return bool(self.children)

    def __nonzero__(self):
        return type(self).__bool__(self)

    def __contains__(self, other):
        return other in self.children

    def add(self, data, conn_type, squash=True):
        if data in self.children:
            return data
        if not squash:
            self.children.append(data)
            return data
        if self.connector == conn_type:
            if (isinstance(data, Node) and not data.negated
                    and (data.connector == conn_type or len(data) == 1)):
                self.children.extend(data.children)
                return self
            else:
                self.children.append(data)
                return data
        else:
            obj = self._new_instance(self.children, self.connector,
                                     self.negated)
            self.connector = conn_type
            self.children = [obj, data]
            return data

    def negate(self):
        self.negated = not self.negated