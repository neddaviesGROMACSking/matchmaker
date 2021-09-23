from pydantic import BaseModel, Field
from typing import List, Union, Literal, Optional, Any

from matchmaker.query_engine.query_types import PaperSearchQuery, \
        AuthorSearchQuery, PaperDetailsQuery, AuthorDetailsQuery, CoauthorQuery
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


class PubMedCoauthorsQuery(BaseModel):
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
    def _query_to_native(self, query: PaperSearchQuery) -> PubmedESearchQuery:
        query = query.dict()['__root__']
        return PubmedESearchQuery.parse_obj(query)


    def _run_native_query(self, query: PubmedESearchQuery) -> List[PubmedEFetchData]:   
        def efetch_on_elink(id_list, linkname):
            def id_mapper_to_unique_list(id_mapper):
                unique_ids = []
                for start_id, linked_ids in id_mapper.items():
                    if linked_ids is not None:
                        for linked_id in linked_ids:
                            if linked_id not in unique_ids:
                                unique_ids.append(linked_id)
                return unique_ids
            id_mapper = elink_on_id_list(PubmedELinkQuery(pubmed_id_list = id_list, linkname = linkname)).id_mapper
            unique_fetch_list = id_mapper_to_unique_list(id_mapper)
            sub_papers = efetch_on_id_list(PubmedEFetchQuery(pubmed_id_list = unique_fetch_list))
            sub_paper_index = {i.paper_id.pubmed: i for i in sub_papers}

            id_mapper_papers = {}
            for search_id, id_list in id_mapper.items():
                if id_list is not None:
                    id_mapper_papers[search_id] = [sub_paper_index[sub_id] for sub_id in id_list]
                else:
                    id_mapper_papers[search_id] = None
            return id_mapper_papers
            
        id_list = esearch_on_query(query).pubmed_id_list
        print(len(id_list))
        papers = efetch_on_id_list(PubmedEFetchQuery(pubmed_id_list = id_list))
        references_set = efetch_on_elink(id_list, 'pubmed_pubmed_refs')
        cited_by_set = efetch_on_elink(id_list, 'pubmed_pubmed_citedin')

        for paper in papers:
            pubmed_id = paper.paper_id.pubmed
            paper.references = references_set[pubmed_id]
            paper.cited_by = cited_by_set[pubmed_id]
            #pprint(paper.dict())

        return papers

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


class CoauthorQueryEngine(
        SlightlyLessAbstractQueryEngine[CoauthorQuery,
            List[AuthorData], PubMedCoauthorsQuery, List[PubMedAuthorData]]):
    def _query_to_native(self, query: CoauthorQuery) -> PubMedCoauthorsQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedCoauthorsQuery) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _post_process(self, query: CoauthorQuery, data: List[PubMedAuthorData]) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _data_from_native(self, data: List[PubMedAuthorData]) -> List[AuthorData]:
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

    def coauthorsEngine(self) -> CoauthorQueryEngine:
        return CoauthorQueryEngine()
