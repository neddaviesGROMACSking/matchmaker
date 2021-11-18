from matchmaker.query_engine.types.query import PaperSearchQuery

d = {
    'query':{
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
}

print(PaperSearchQuery)
pq = PaperSearchQuery.parse_obj(d)
print(pq.dict())
