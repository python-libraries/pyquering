from pyquering.query import q, Query
from pyquering.query_parsers import JSONParser, SQLParser, SQLParserWrap

filters=None
table_id='teste'
max_results=60
orders=['-datetime', 'nome']
filters=q(x=1) & q(y=2)

filters = Query(
    filters=filters,
    table=table_id,
    column_delimiter=None,
    limit=max_results,
    orders=orders
).parse(SQLParserWrap)

print(filters)