# pyquery
it is useful for creating queries and to convert it to any syntax

# Creating queries

If you want 'SELECT ... FROM ... WHERE `foo = "BAR" OR bar = "FOO"`', do this:

```
from pyquery.query import q

q(foo="BAR") | q(bar="FOO")
```

Let's do one most complicated. 'SELECT ... FROM ... WHERE `(shirt = "orange" AND pants = "red") OR ((shirt = "black" OR pants = "dark gray") AND age >= 18)`':

```
from pyquery.query import q

q(shirt="orange", pants="red") | q(q(q(shirt="black") | q(pants="dark gray")) & q(age__gte=18))
```

**Available operators:** `=` as `eq`, `>=` as `gte`, `<=` as `lte`, `IN` as `in`, `IS NULL` as `isnull=True`, `IS NOT NULL` as `isnull=False`

# Converting

**To SQL:**

```
from pyquery.query import q, Query
from utils.helpers.query_parsers import SQLParser

obj = q(foo="BAR") | q(bar="FOO")

Query('table', obj).parse(SQLParser)
```

Result:

```
SELECT * FROM table WHERE (`for`="BAR") OR (`bar`="FOO")
```

**To JSON:**

```
from pyquery.query import q, Query
from utils.helpers.query_parsers import JSONParser

obj = q(foo="BAR") | q(bar="FOO")

Query(obj).parse(JSONParser)
```

Result:

```
{'filters': {'OR': [{'foo__eq': 'BAR'}, {'bar__eq': 'FOO'}]}}
```

# Reverting

**From JSON:**

```
from pyquery.query import q, Query
from utils.helpers.query_parsers import JSONParser

obj = {'filters': {'OR': [{'foo__eq': 'BAR'}, {'bar__eq': 'FOO'}]}}

Query(obj).reverse(JSONParser)
```

**From SQL:**

```
from pyquery.query import q, Query
from utils.helpers.query_parsers import SQLParser

Query(obj).reverse(SQLParser)
```

# About the class Query

It has three attributes which are, `fields`, `table` and `filters`. You can initiliaze like this `Query(<string: table_name>, <list: fields>, <InstanceOf q: filters>)`, in any order will works, but you can specify all arguments like this `Query(table='Table Name', fields=['field1', 'field2'], filters=q)`.

This class has only two method wich are `reverse` and `parse`, that were showed and examplified before.