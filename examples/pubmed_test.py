from matchmaker.query_engine.backends.pubmed import PaperSearchQueryEngine
from matchmaker.query_engine.query_types import PaperSearchQuery

d = {
    'query':{
        'tag': 'or',
        'fields_': [
            {
                'tag': 'author',
                'operator': {
                    'tag': 'equal',
                    'value': 'Jeremy Green'
                }
            },
            {
                'tag': 'year',
                'operator': {
                    'tag': 'range',
                    'lower_bound': '2001',
                    'upper_bound': '2012'
                }
            }
        ]
    }
}

pub_searcher = PaperSearchQueryEngine()

test = pub_searcher._query_to_native(PaperSearchQuery(**d))
print(test)
results = pub_searcher._run_native_query(test)
print(results)