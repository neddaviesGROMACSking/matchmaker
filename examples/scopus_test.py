from matchmaker.query_engine.backends.scopus import test_scopus_search, test_scopus_get_institution_id, test_scopus_get_authors

results = test_scopus_search()
import json
#print(json.dumps([i.dict() for i in results], indent=2))

#results = test_scopus_get_authors_from_institution()
#print(json.dumps([i.dict() for i in results], indent=2))
results = test_scopus_get_institution_id()
#print(json.dumps([i.dict() for i in results], indent=2))
#print(results)
results = test_scopus_get_authors()
#print(results)
#print(json.dumps(results, indent=2))
print(json.dumps([i.dict() for i in results], indent=2))