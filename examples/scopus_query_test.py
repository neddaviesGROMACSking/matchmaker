from matchmaker.query_engine.backends.scopus_api_new import query_to_term, ScopusSearchQuery

d = {
    'tag': 'and',
    'fields_': [
        {
            'tag': 'year',
            'operator': {
                'tag': 'equal',
                'value': 1996
            }
        }
    ]
}

d = {
    'tag': 'and',
    'fields_': [
        {
            'tag': 'publisher',
            'operator': {
                'tag': 'equal',
                'value': 'penguin'
            }
        },
        {
            'tag': 'year',
            'operator': {
                'tag': 'equal',
                'value': 1996
            }
        }
    ]
}

pq = ScopusSearchQuery.parse_obj(d)
print(query_to_term(pq.dict()['__root__']))
print(pq.dict())
