from matchmaker.query_engine.backends.scopus import ScopusBackend 
from matchmaker.query_engine.types.query import PaperSearchQuery, AuthorSearchQuery
import asyncio

import time
from secret import scopus_api_key, scopus_inst_token

scopus_backend = ScopusBackend(scopus_api_key, scopus_inst_token)
paper_search = scopus_backend.paper_search_engine()
author_search = scopus_backend.author_search_engine()

auth1_query = AuthorSearchQuery.parse_obj({
    'query':{
        'tag': 'institutionid',
        'operator':{
            'tag': 'equal',
            'value': '60113298'
        }
    },
    'selector': {
        'id': True,
        'preferred_name':{'surname': True, 'given_names': True}
    }
})

auth2_query = AuthorSearchQuery.parse_obj({
    'query':{
        'tag': 'institutionid',
        'operator':{
            'tag': 'equal',
            'value': '60116936'
        }
    },
    'selector': {
        'id': True,
        'preferred_name':{'surname': True, 'given_names': True}
    }
})

def get_author_abstracts(id, papers):
    abstracts = []
    for paper in papers:
        if id in  [a.id for a in paper.authors]:
            abstracts.append(paper.abstract)
    return abstracts
async def main():
    auth1_res = await author_search(auth1_query)
    auth2_res = await author_search(auth2_query)
    
    auth1_paper_query = PaperSearchQuery.parse_obj({
        'query':{
            'tag':'or',
            'fields_': [
                {
                    'tag': 'authorid',
                    'operator': {
                        'tag': 'equal',
                        'value': i.id
                    }
                } async for i in auth1_res
            ]
        },
        'selector': {'authors':{'id': True}, 'abstract': True}
    })

    auth2_paper_query = PaperSearchQuery.parse_obj({
        'query':{
            'tag':'or',
            'fields_': [
                {
                    'tag': 'authorid',
                    'operator': {
                        'tag': 'equal',
                        'value': i.id
                    }
                } async for i in auth2_res
            ]
        },
        'selector': {'authors':{'id': True}, 'abstract': True}
    })

    pap1_res = await paper_search(auth1_paper_query)
    author1_dict = {}
    async for author in auth1_res:
        abstracts = get_author_abstracts(author.id, pap1_res)
        if author.preferred_name.given_names is not None:
            name = author.preferred_name.given_names + ' ' + author.preferred_name.surname
        else:
            name = author.preferred_name.surname
        author1_dict[name] = abstracts
    pap2_res = await paper_search(auth2_paper_query)
    author2_dict = {}
    async for author in auth2_res:
        abstracts = get_author_abstracts(author.id, pap2_res)
        if author.preferred_name.given_names is not None:
            name = author.preferred_name.given_names + ' ' + author.preferred_name.surname
        else:
            name = author.preferred_name.surname
        author2_dict[name] = abstracts
    #return proc_result
results = asyncio.run(main())

