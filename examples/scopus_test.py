from matchmaker.query_engine.backends.scopus import test_scopus_search, test_scopus_get_authors_from_institution, test_scopus_get_institution_id

results = test_scopus_search()
import json
print(json.dumps([i.dict() for i in results], indent=2))

results = test_scopus_get_authors_from_institution()
print(json.dumps([i.dict() for i in results], indent=2))
results = test_scopus_get_institution_id()
print(json.dumps([i.dict() for i in results], indent=2))
#print(results)