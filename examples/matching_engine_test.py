import asyncio
from typing import List

from tabulate import tabulate #type:ignore

from matchmaker.matching_engine import (
    AbstractToAbstractCorrelationFunction,
    MatchingEngine,
    display_matches,
    process_matches,
)
from matchmaker.query_engine.backends.optimised_scopus_meta import (
    OptimisedScopusBackend,
)
from matchmaker.query_engine.backends.pubmed import PubmedBackend
from matchmaker.query_engine.backends.scopus import ScopusBackend
from matchmaker.query_engine.types.data import InstitutionData
from matchmaker.query_engine.types.query import (
    AuthorSearchQuery,
    AuthorSearchQueryInner,
    InstitutionSearchQuery,
    PaperSearchQuery,
)
from matchmaker.query_engine.types.selector import (
    AuthorDataSelector,
    InstitutionDataSelector,
)
from secret import pubmed_api_key, scopus_api_key, scopus_inst_token

op_scopus_backend = OptimisedScopusBackend(
    ScopusBackend(
        scopus_api_key,
        scopus_inst_token
    ),
    PubmedBackend(
        pubmed_api_key
    )
)

op_scopus_paper = op_scopus_backend.paper_search_engine()
op_scopus_author = op_scopus_backend.author_search_engine()
op_scopus_inst = op_scopus_backend.institution_search_engine()

def choose_institution(institution_data: List[InstitutionData]) -> str:
    def choose_institution_inner(institution_data: List[InstitutionData]) -> str:
        total_list = []
        for i, inst in enumerate(institution_data):
            inner_list = []
            inner_list.append(i)
            inner_list.append(inst.id.scopus_id)
            inner_list.append(inst.name)
            total_list.append(inner_list)
        print('Choose an institution:')
        print(tabulate(total_list, headers=['No', 'ID', 'Name']))
        while True:
            out_string = input('Please select the number of the institution you require: ')
            try:
                relevant_no = int(out_string)
            except ValueError:
                print('Make sure you choose an integer!')
                continue
            if relevant_no > len(total_list)-1 or relevant_no < 0:
                print('Number outside range')
                continue
            else:
                break
        return institution_data[relevant_no].id.scopus_id
    
    if len(institution_data) == 0:
        raise ValueError('Institution not found')
    elif len(institution_data) == 1:
        relevant_institution = institution_data[0]
        return relevant_institution.id.scopus_id
    else:
        return choose_institution_inner(institution_data)

async def get_institution_data_from_name(name:str):
    return await op_scopus_inst(
        InstitutionSearchQuery.parse_obj({
            'query':{
                'tag': 'institution',
                'operator': {
                    'tag': 'equal',
                    'value': name
                },
            },
            'selector': {
                'id': {'scopus_id': True}, 
                'name': True
            }
        })
    )

def get_author_query_from_id(id_string:str):
    return AuthorSearchQuery.parse_obj({
        'query':{
            'tag': 'and',
            'fields_': [
                {
                    'tag': 'institutionid',
                    'operator': {
                        'tag': 'equal',
                        'value': {
                            'scopus_id': id_string
                        }
                    }
                },
                {
                    'tag': 'year',
                    'operator': {
                        'tag': 'range',
                        'lower_bound': '2018',
                        'upper_bound': '2022'
                    }
                }
            ]
        },
        'selector': {
            'preferred_name': True
        }
    })

name1 = 'IBM Ireland Limited'
name2 = 'Limerick Institute of Technology'



matching_engine = MatchingEngine(
    author_engine = op_scopus_author,
    correlation_functions=[
        AbstractToAbstractCorrelationFunction(op_scopus_paper)
    ]
)




async def main():
    inst_data1 = await get_institution_data_from_name(name1)
    inst_data2 = await get_institution_data_from_name(name2)
    inst_id1 = choose_institution(inst_data1)
    inst_id2 = choose_institution(inst_data2)
    author_query1 = get_author_query_from_id(inst_id1)
    author_query2 = get_author_query_from_id(inst_id2)

    out = await matching_engine(author_query1, author_query2)
    stacked_m, author_data1, author_data2 = out
    # TODO Note:  change, can be author queries *with* selectors as additional data may be required for other reasons.
    # such as displaying the authors names
    # Generates superset with this and those required for the correlation functions
    return process_matches(stacked_m, author_data1, author_data2)


results = asyncio.run(main())
display_matches(results)
#print(results)
