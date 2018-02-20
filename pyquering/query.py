from . import tree


class q(tree.Node):


    AND = 'AND'
    OR = 'OR'
    default = AND


    def _add(self, data, conn_type):
        self.children.extend(data.children)


    def _combine(self, other, conn):
        if not isinstance(other, q):
            raise TypeError(other)
        obj = type(self)()
        obj.connector = conn
        obj.add(self, conn)
        obj.add(other, conn)
        return obj


    def __or__(self,  other):
        return self._combine(other, self.OR)


    def __and__(self, other):
        return self._combine(other, self.AND)


    def __init__(self, *args, **kwargs):
        super(q, self).__init__(children=list(args) + list(kwargs.items()))


class Query:


    fields = None
    table = None
    filters = None
    limit = None
    orders = None
    column_delimiter = None


    def __init__(self, table=None, fields=None, filters=None, limit=None, orders=None, column_delimiter=True):
        self.table = table
        self.fields = fields
        self.filters = filters
        self.limit = limit
        self.orders = orders
        self.column_delimiter = column_delimiter


    def parse(self, query_parser):
        query = query_parser().parse(self.table, self.fields, self.filters, self.limit, self.orders, self.column_delimiter)

        return query


    def reverse(self, query_parser):
        query = query_parser().reverse(self.filters)

        return query