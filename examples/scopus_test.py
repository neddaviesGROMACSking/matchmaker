from matchmaker.query_engine.backends.scopus_api import test_scopus_search, test_scopus_get_institutions, test_scopus_get_authors
import json
results = test_scopus_search()
#print(json.dumps([i.dict() for i in results], indent=2))
results = test_scopus_get_institutions()
#print(json.dumps([i.dict() for i in results], indent=2))
results = test_scopus_get_authors()
print(json.dumps([i.dict() for i in results], indent=2))
