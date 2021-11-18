from matchmaker.matching_engine import MatchingEngine, AuthorGetter, AbstractToAbstractCorrelationFunction, display_matches
from matchmaker.query_engine.types.data import InstitutionData
from matchmaker.query_engine.types.query import PaperSearchQuery, AuthorSearchQuery
from matchmaker.query_engine.types.selector import AuthorDataSelector, InstitutionDataSelector
from matchmaker.query_engine.backends.optimised_scopus_meta import OptimisedScopusBackend
from matchmaker.query_engine.backends.pubmed import PubmedBackend
from matchmaker.query_engine.backends.scopus import ScopusBackend
from secret import pubmed_api_key, scopus_api_key, scopus_inst_token
from typing import List
import asyncio
from tabulate import tabulate #type:ignore

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

def choose_institution_callback(institution_data: List[InstitutionData]) -> str:
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


matching_engine = MatchingEngine(
    author_getter=AuthorGetter(
        op_scopus_inst,
        op_scopus_author,
        choose_institution_callback,
        InstitutionDataSelector.parse_obj({
            'id': {'scopus_id': True}, 
            'name': True
        }),
        AuthorDataSelector.parse_obj({
            'id': {'scopus_id': True}, 
            'preferred_name': True
        })
    ),
    correlation_functions=[
        AbstractToAbstractCorrelationFunction(op_scopus_paper)
    ]
)

name1 = 'IBM Ireland Limited'
name2 = 'Limerick Institute of Technology'


async def main():
    return await matching_engine(name1, name2)

results = asyncio.run(main())
display_matches(results)
#print(results)
