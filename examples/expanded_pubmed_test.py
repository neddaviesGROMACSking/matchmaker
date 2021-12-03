from matchmaker.query_engine.backends import expanded_pubmed_meta
from matchmaker.query_engine.backends.expanded_pubmed_meta import ExpandedPubmedMeta
from matchmaker.query_engine.backends.pubmed import PubmedBackend
from secret import pubmed_api_key
from matchmaker.query_engine.types.query import AuthorSearchQuery
import asyncio
expanded_pub = ExpandedPubmedMeta(PubmedBackend(
    pubmed_api_key
))
engine = expanded_pub.author_search_engine()
author_search = AuthorSearchQuery.parse_obj({
    'query':{
        'tag': 'and',
        'fields_': [
            {
                'tag': 'author',
                'operator': {
                    'tag': 'equal',
                    'value': 'Jeremy Green'
                }
            }
        ]
    },
    'selector': {'preferred_name': {
        'surname': True,
        'given_names': True}, 'institution_current': {'name': True}}
})
async def main():
    data_iter = await engine(author_search)
    return [i async for i in data_iter]
pub_author_results = asyncio.run(main())
print(pub_author_results)
