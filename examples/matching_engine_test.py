from matchmaker.matching_engine import MatchingEngine, AuthorGetter, AbstractToAbstractCorrelationFunction, AbstractToAbstractNonElementWise
from matchmaker.query_engine.data_types import InstitutionData
from matchmaker.query_engine.query_types import PaperSearchQuery, AuthorSearchQuery
from matchmaker.query_engine.selector_types import AuthorDataSelector, InstitutionDataSelector
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
        inner_list.append(inst.id)
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
    return institution_data[relevant_no].id


matching_engine = MatchingEngine(
    author_getter=AuthorGetter(
        op_scopus_inst,
        op_scopus_author,
        choose_institution_callback,
        InstitutionDataSelector(id = True, name= True),
        AuthorDataSelector(id= True, preferred_name=True)
    ),
    correlation_functions=[
        AbstractToAbstractNonElementWise(op_scopus_paper)
    ]
)

name1 = 'IBM Ireland Limited'
name2 = 'Limerick Institute of Technology'


async def main():
    return await matching_engine(name1, name2)

results = asyncio.run(main())
import numpy as np
dtype = [('Author1', '<U32'), ('Author2', '<U32'), ('Match', float)]
test = np.array(results)
final = np.sort(np.array(results, dtype = dtype),order='Match')
print(tabulate(final, headers=['Author1', 'Author2', 'Match Rating']))

#print(results)