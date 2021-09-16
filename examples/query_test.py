from matchmaker.query_engine.query_types import PaperSearchQuery

d = {
    'query':{
        'tag': 'and',
        'fields_': [
            {
                'tag': 'year',
                'operator': {
                    'tag': 'lt',
                    'value': 1996
                }
            }
        ]
    }
}
print(PaperSearchQuery)
pq = PaperSearchQuery(**d)
print(pq)
