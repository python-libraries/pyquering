from .query import q


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


    def _value(value):
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

        if type(values) is list or type(values) is tuple:
            values = ','.join([_value(value) for value in values])

        if cmp == 'isnull':
            return symbols[cmp][str(values)] % field
        else:
            return symbols[cmp] % (field, values)


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


    def _mount_sql_json(self, factors, factor=None):
        if not factor:
            fac = [self._mount_sql_json(factors, factor) for factor in factors]

        if type(factor) is str:
            for value in factors:
                return factors[value[1:]]

        if type(factor) is dict:
            dict_key = factor.__iter__().__next__()
            self._mount_sql_json(factors, factor['dict_key'])

        return factors


    def parse(self, table, fields, filters):
        filters = self._parse_filters(filters)

        if not fields:
            fields = '*'
        else:
            fields = ','.join(['`%s`' % field for field in fields])

        return 'SELECT %s FROM %s WHERE %s' % (fields, table, filters)


    def reverse(self, sql):
        sql = self._sql_where(sql)
        factors = self._sql_factors(sql)
        factors = self._sql_split_operations(factors)
        json = self._mount_sql_json(factors)
        return self._reverse(json)


class JSONParser(QParser):


    def _list(self, filters, connector):
        return {connector: filters}


    def _tuple(self, field, cmp, values):
        return self._parser(cmp, field, values)


    def _parser(self, cmp, field, values):
        return {'%s__%s' % (field, cmp): values}


    def parse(self, table, fields, filters):
        json = {}

        if table:
            json.update({'table': table})
        if fields:
            json.update({'fields': fields})

        filters = self._parse_filters(filters)

        json.update({'filters': filters})

        return json


    def reverse(self, filters):
        return self._reverse(filters)