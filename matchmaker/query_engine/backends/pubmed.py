from pydantic import BaseModel, Field
from typing import List, Union, Literal, Optional, Any

from matchmaker.query_engine.query_types import PaperSearchQuery, \
        AuthorSearchQuery, PaperDetailsQuery, AuthorDetailsQuery
from matchmaker.query_engine.data_types import PaperData, AuthorData
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.backend import Backend
from matchmaker.query_engine.backends.pubmed_api import (
    PubmedESearchQuery, 
    MeshTopic, 
    PubmedEFetchQuery, 
    PubmedEFetchData,
    PubmedELinkQuery,
    PubmedAuthor, 
    elink_on_id_list, 
    efetch_on_id_list, 
    esearch_on_query
)

from matchmaker.query_engine.query_types import And, Or, Title, AuthorName, Journal, Abstract, Institution, Keyword, Year, StringPredicate
from typing import Annotated, Literal
from pprint import pprint
from asyncio import Future, get_running_loop, gather, create_task
from httpx import AsyncClient
from copy import copy
class PubMedPaperDetailsQuery(BaseModel):
    pubmed_ids: List[str]


class PubmedAuthorID(PubmedAuthor):
    pass

and_int = And['PubMedAuthorSearchQuery']
or_int = Or['PubMedAuthorSearchQuery']

class PubMedAuthorSearchQuery(BaseModel):
    __root__: Annotated[
    Union[
        and_int,
        or_int,
        AuthorName,
        Institution,
        MeshTopic
    ],
    Field(discriminator='tag')]

and_int.update_forward_refs()
or_int.update_forward_refs()
PubMedAuthorSearchQuery.update_forward_refs()


class PubMedAuthorDetailsQuery(BaseModel):
    # TODO: implement this
    pass




class PubMedAuthorData(BaseModel):
    # TODO: implement this
    pass

def paper_from_native(data):
    raise NotImplementedError('TODO')


def make_doi_search_term(doi_list):
    new_doi_list = [doi + '[Location ID]' for doi in doi_list]
    return ' OR '.join(new_doi_list)


class PaperSearchQueryEngine(
        SlightlyLessAbstractQueryEngine[PaperSearchQuery,
            List[PaperData], PubmedESearchQuery, List[PubmedEFetchData]]):
    api_key:str
    def __init__(self, api_key, *args, **kwargs):
        self.api_key = api_key
        super().__init__(*args, **kwargs)
    def _query_to_native(self, query: PaperSearchQuery) -> PubmedESearchQuery:
        query = query.dict()['__root__']
        return PubmedESearchQuery.parse_obj(query)


    def _query_to_awaitable(self, query: PubmedESearchQuery) -> List[PubmedEFetchData]:
        split_factor = 10
        async def make_coroutine(client: AsyncClient):
            async def esearch_on_query_set_future(id_list_future, query, client):
                output = await esearch_on_query(query, client, api_key=self.api_key)
                id_list = output.pubmed_id_list
                id_list_future.set_result(id_list)
                return id_list_future
            
            async def efetch_on_id_list_resolve_id(id_list_future, client):
                await id_list_future
                id_list = id_list_future.result()
                result = await efetch_on_id_list(PubmedEFetchQuery(pubmed_id_list = id_list), client, api_key=self.api_key)
                return result

            async def efetch_on_elink_resolve_id(id_list_future, fetch_list_future, linkname, client):
                def id_mapper_to_unique_list(id_mapper):
                    unique_ids = []
                    for start_id, linked_ids in id_mapper.items():
                        if linked_ids is not None:
                            for linked_id in linked_ids:
                                if linked_id not in unique_ids:
                                    unique_ids.append(linked_id)
                    return unique_ids
                
                await id_list_future
                id_list = id_list_future.result()

                output = await elink_on_id_list(PubmedELinkQuery(pubmed_id_list = id_list, linkname = linkname), client, api_key=self.api_key)
                
                id_mapper = output.id_mapper
                unique_fetch_list = id_mapper_to_unique_list(id_mapper)
                fetch_list_future.set_result(unique_fetch_list)
                return id_mapper

            async def redistribute_fetches(*list_futures, bin_futures = None, split_factor = None):
                if bin_futures is None:
                    raise ValueError( 'No bin_futures')
                if split_factor is None:
                    raise ValueError('No split factor')
                
                total_fetch_list = []
                for i in list_futures:
                    await i
                    fetch_list = i.result()
                    total_fetch_list += fetch_list
                unique_total_fetch_list = list(set(total_fetch_list))
                fetch_length = len(unique_total_fetch_list)
                bin_size = fetch_length // split_factor
                bins = []
                for i in range(split_factor):
                    if i == split_factor -1:
                        bins.append(unique_total_fetch_list[bin_size*i:len(unique_total_fetch_list)])
                    else:
                        bins.append(unique_total_fetch_list[bin_size*i:bin_size*(i+1)])

                for counter, j in enumerate(bin_futures):
                    bin_item = bins[counter]
                    j.set_result(bin_item)
            
            async def get_papers_from_index(id_mapper, sub_paper_index):
                id_mapper_papers = {}
                for search_id, id_list in id_mapper.items():
                    if id_list is not None:
                        id_mapper_papers[search_id] = [sub_paper_index[sub_id] for sub_id in id_list]
                    else:
                        id_mapper_papers[search_id] = None
                return id_mapper_papers
            
            original_fetch_ids_future = get_running_loop().create_future()
            ref_fetch_list_future = get_running_loop().create_future()
            cited_fetch_list_future = get_running_loop().create_future()
            unique_total_fetch_list_future = get_running_loop().create_future()

            bin_futures = []
            for j in range(split_factor):
                bin_futures.append(get_running_loop().create_future())
            
            awaitables = []

            esearch_await = esearch_on_query_set_future(original_fetch_ids_future, query, client)
            efetch_await = efetch_on_id_list_resolve_id(original_fetch_ids_future, client)

            references_set_await = efetch_on_elink_resolve_id(
                original_fetch_ids_future,
                ref_fetch_list_future,
                'pubmed_pubmed_refs', 
                client
            )
            cited_by_set_await = efetch_on_elink_resolve_id(
                original_fetch_ids_future, 
                cited_fetch_list_future, 
                'pubmed_pubmed_citedin', 
                client
            )

            redistribute_await = redistribute_fetches(
                ref_fetch_list_future, 
                cited_fetch_list_future, 
                bin_futures = bin_futures,
                split_factor=split_factor
            )
            awaitables += [esearch_await, efetch_await, references_set_await, cited_by_set_await, redistribute_await]
            for i in bin_futures:
                awaitables.append(efetch_on_id_list_resolve_id(i,client))

            gather_output = await gather(
                *awaitables
            )
            listed_gather_out = list(gather_output)
            esearch_out, papers, references_mapper, cited_by_mapper, redist_out = listed_gather_out[0:5]
            sub_papers = listed_gather_out[5: len(listed_gather_out)]
            new_sub_papers = []
            for i in sub_papers:
                new_sub_papers += i
            sub_paper_index = {i.paper_id.pubmed: i for i in new_sub_papers}
            references_set, cited_by_set = await gather(
                get_papers_from_index(references_mapper, sub_paper_index),
                get_papers_from_index(cited_by_mapper, sub_paper_index)
            )
            for paper in papers:
                pubmed_id = paper.paper_id.pubmed
                paper.references = references_set[pubmed_id]
                paper.cited_by = cited_by_set[pubmed_id]

            return papers
        metadata = {
            'efetch': 1+split_factor,
            'esearch': 1,
            'elink': 2
        }
        return make_coroutine, metadata

    def _post_process(self, query: PaperSearchQuery, data: List[PubmedEFetchData]) -> List[PubmedEFetchData]:
        # TODO: implement this
        pass

    def _data_from_native(self, data: List[PubmedEFetchData]) -> List[PaperData]:
        return [paper_from_native(datum) for datum in data]


class PaperDetailsQueryEngine(
        SlightlyLessAbstractQueryEngine[PaperDetailsQuery,
            PaperData, PubMedPaperDetailsQuery, PubmedEFetchData]):
    def _query_to_native(self, query: PaperDetailsQuery) -> PubMedPaperDetailsQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedPaperDetailsQuery) -> PubmedEFetchData:
        # TODO: implement this
        pass

    def _post_process(self, query: PaperDetailsQuery, data: PubmedEFetchData) -> PubmedEFetchData:
        # TODO: implement this
        pass

    def _data_from_native(self, data: PubmedEFetchData) -> PaperData:
        return paper_from_native(data)


class AuthorSearchQueryEngine(
        SlightlyLessAbstractQueryEngine[AuthorSearchQuery,
            List[AuthorData], PubMedAuthorSearchQuery, List[PubMedAuthorData]]):
    def _query_to_native(self, query: AuthorSearchQuery) -> PubMedAuthorSearchQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedAuthorSearchQuery) -> List[PubMedAuthorData]:
        id_list = esearch_on_query(query).pubmed_id_list
        print(len(id_list))
        papers = efetch_on_id_list(id_list)
        # TODO: implement this
        pass

    def _post_process(self, query: AuthorSearchQuery, data: List[PubMedAuthorData]) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _data_from_native(self, data: List[PubMedAuthorData]) -> List[AuthorData]:
        # TODO: implement this
        pass

class AuthorDetailsQueryEngine(
        SlightlyLessAbstractQueryEngine[AuthorDetailsQuery,
            AuthorData, PubMedAuthorDetailsQuery, PubMedAuthorData]):
    def _query_to_native(self, query: AuthorDetailsQuery) -> PubMedAuthorDetailsQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedAuthorDetailsQuery) -> PubMedAuthorData:
        # TODO: implement this
        pass

    def _post_process(self, query: AuthorDetailsQuery, data: PubMedAuthorData) -> PubMedAuthorData:
        # TODO: implement this
        pass

    def _data_from_native(self, data: PubMedAuthorData) -> AuthorData:
        # TODO: implement this
        pass


class PubMedBackend(Backend):
    def paperSearchEngine(self) -> PaperSearchQueryEngine:
        return PaperSearchQueryEngine()

    def authorSearchEngine(self) -> AuthorSearchQueryEngine:
        return AuthorSearchQueryEngine()

    def paperDetailsEngine(self) -> PaperDetailsQueryEngine:
        return PaperDetailsQueryEngine()

    def authorDetailsEngine(self) -> AuthorDetailsQueryEngine:
        return AuthorDetailsQueryEngine()
