from .query import q
import re


class QParser:


    def _parse_filters(self, filter, connector=None):
        if hasattr(filter, 'connector'):
            return self._parse_filters(filter.children, filter.connector)
        elif type(filter) is list:
            return self._parse_list(filter, connector)
        else:
            return self._parse_tuple(filter)


    def _parse_list(self, filters, connector):
        return self._list([self._parse_filters(filter) for filter in filters], connector)


    def _parse_tuple(self, filter):
        field, values = filter

        if '__' in field:
            field, cmp = field.split('__')
        else:
            field, cmp = [field, 'eq']

        return self._tuple(field, cmp, values)


    def _reverse_connection(self, connector, values):
        filter = None

        for value in values:
            if not filter:
                filter = value
            else:
                if connector == 'AND':
                    filter = filter & value
                if connector == 'OR':
                    filter = filter | value

        return filter


    def _reverse_dict(self, filters):
        first_value_key, first_value_values = filters.items().__iter__().__next__()

        if first_value_key in ('AND', 'OR'):
            new_values = self._reverse(first_value_values)
            return self._reverse_connection(first_value_key, new_values)
        else:
            return q(**filters)


    def _reverse_list(self, filters):
        return [self._reverse(filter) for filter in filters]


    def _reverse(self, filters):
        if type(filters) is dict:
            return self._reverse_dict(filters)

        if type(filters) is list:
            return self._reverse_list(filters)


class SQLParser(QParser):


    symbols = {
        'eq': '`%s`=%s',
        'in': '`%s` IN(%s)',
        'gte': '`%s`>= %s',
        'lte': '`%s`<= %s',
        'isnull': {
            'True': '`%s` IS NULL',
            'False': '`%s` IS NOT NULL'
        }
    }


    def _value(self, value):
        _value_type = type(value)

        if _value_type is str:
            if value.isdigit():
                value = int(value)
                _value_type = type(value)

        if _value_type is not int and _value_type is not float:
            value = '"%s"' % value
        else:
            value = str(value)

        return value


    def _list(self, filters, connector):
        filters = (' ' + connector + ' ').join(filters)
        return '(' + filters + ')'


    def _tuple(self, field, cmp, values):
        return self._parser(cmp, field, values)


    def _parser(self, cmp, field, values):
        if type(values) is list or type(values) is tuple:
            values = ','.join([self._value(value) for value in values])

        if cmp == 'isnull':
            return self.symbols[cmp][str(values)] % field
        else:
            return self.symbols[cmp] % (field, self._value(values))


    def _parser_reverse(self, cmp, field, values):
        return {'%s__%s' % (field, cmp): values}


    def _parse_orders(self, orders):
        orders = ['%s DESC' % order[1:] if order[0] == '-' else '%s ASC' % order for order in orders]
        if len(orders) == 1:
            return orders[0]
        else:
            return ', '.join(orders)


    def _sql_where(self, sql):
        return sql.split('WHERE ')[1]


    def _sql_factor(self, sql, pos):
        end = sql.find(')')
        start = sql[:end].rfind('(')
        factor = sql[start + 1:end]
        sql = sql[:start] + '$%s' % pos + sql[end + 1:]
        return [sql, factor]


    def _sql_factors(self, sql):
        factors = []
        pos = 0

        while sql != ('$%s' % (int(pos)-1)):
            sql, factor = self._sql_factor(sql, pos)
            factors.append(factor)
            pos += 1

        return factors


    def _sql_split_operations(self, factors):
        if type(factors) is not list:
            if ' AND ' in factors:
                return {'AND': factors.split(' AND ')}
            if ' OR ' in factors:
                return {'OR': factors.split('OR')}

        factors = [self._sql_split_operations(factor) for factor in factors]
        return factors


    def _format_json_get_field_comparator_value(self, operation):
        operation = operation.strip()

        for comparator, pattern in self.symbols.items():

            if type(pattern) is dict:
                for value, pattern in pattern.items():
                    value = bool(value)
                    pattern = pattern.replace('`%s`', '`([\S]+)`')
                    match = re.match(pattern, operation)

                    if match:
                        matched = match.group(0).strip()

                        if matched == operation:
                            field = match.group(1)
                            return comparator, field, value

            pattern = pattern.replace('`%s`', '`([\S]+)`').replace('%s', '([\S]+)')
            match = re.match(pattern, operation)

            if match:
                matched = match.group(0).strip()

                if matched == operation:
                    field = match.group(1).strip()
                    value = match.group(2).strip()
                    return comparator, field, value


    def _format_json_operation_format(self, operation):
        comparator, field, value = self._format_json_get_field_comparator_value(operation)
        return self._parser_reverse(comparator, field, value)


    def _format_json_operation(self, operation, json):
        dollar_pos = operation.find('$')

        if dollar_pos >= 0:
            dollar_val = int(operation[dollar_pos+1])
            value = json[dollar_val]
        else:
            value = self._format_json_operation_format(operation)

        return value


    def _format_json(self, factor, json):
        OR = factor.get('OR')
        AND = factor.get('AND')
        operation_list = AND if AND else OR
        json = [self._format_json_operation(operation, json) for operation in operation_list]
        json = {factor.__iter__().__next__(): json}
        return json


    def _mount_sql_json(self, factors, factor=None):
        json = []
        for factor in factors:
            json.append(self._format_json(factor, json))
        return json[-1]


    def _column_delimiter(self, delimiter):
        if not delimiter:
            for cmp, symbol in self.symbols.items():
                if type(symbol) is str:
                    self.symbols[cmp] = symbol.replace('`%s`', '%s')
                else:
                    for value, isnull in symbol.items():
                        self.symbols[cmp][value] = isnull.replace('`%s`', '%s')


    def parse(self, table, fields, filters, limit, orders, column_delimiter):
        self._column_delimiter(column_delimiter)

        if filters:
            filters = self._parse_filters(filters)

        if orders:
            orders = self._parse_orders(orders)

        if not fields:
            fields = '*'
        else:
            fields = ','.join(['`%s`' % field for field in fields])

        sql = 'SELECT %s FROM %s' % (fields, table)

        if filters:
            sql += ' WHERE %s' % filters

        if orders:
            sql += ' ORDER BY %s' % orders

        if limit:
            sql += ' LIMIT %s' % limit

        return sql


    def reverse(self, sql):
        sql = self._sql_where(sql)
        factors = self._sql_factors(sql)
        factors = self._sql_split_operations(factors)
        json = self._mount_sql_json(factors)
        return self._reverse(json)


class SQLParserWrap(SQLParser):


    table = None
    fields = None
    orders = None
    limit = None
    where = None
    sql = None


    def parse(self, table, fields, filters, limit, orders, column_delimiter):
        if filters:
            self.where = self._parse_filters(filters)

        if orders:
            self.orders = self._parse_orders(orders)

        if not fields:
            self.fields = '*'
        else:
            self.fields = ','.join(['`%s`' % field for field in fields])

        self.table = table
        self.limit = limit

        self.sql = super(SQLParserWrap, self).parse(table, fields, filters, limit, orders, column_delimiter)

        return self


class JSONParser(QParser):


    def _list(self, filters, connector):
        return {connector: filters}


    def _tuple(self, field, cmp, values):
        return self._parser(cmp, field, values)


    def _parser(self, cmp, field, values):
        return {'%s__%s' % (field, cmp): values}


    def parse(self, table, fields, filters, limit, orders, column_delimiter):
        json = {}

        if table:
            json.update({'table': table})
        if fields:
            json.update({'fields': fields})
        if limit:
            json.update({'limit': limit})
        if orders:
            json.update({'orders': orders})

        filters = self._parse_filters(filters)

        json.update({'filters': filters})

        return json


    def reverse(self, filters):
        return self._reverse(filters)