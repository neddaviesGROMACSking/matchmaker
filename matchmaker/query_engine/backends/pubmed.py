from pydantic import BaseModel, Field
from typing import List, Union, Literal, Optional, Any

from matchmaker.query_engine.query_types import PaperSearchQuery, \
        AuthorSearchQuery, PaperDetailsQuery, AuthorDetailsQuery, CoauthorQuery
from matchmaker.query_engine.data_types import PaperData, AuthorData
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.backend import Backend
from matchmaker.query_engine.backends.pubmed_api import PubMedPaperData, get_linked_paper_ids, papers_from_id_list, get_id_list_from_query



from matchmaker.query_engine.query_types import And, Or, Title, AuthorName, Journal, Abstract, Institution, Keyword, Year
from typing import Annotated
from pprint import pprint
and_int = And['PubMedPaperSearchQuery']
or_int = Or['PubMedPaperSearchQuery']
    
class PubMedPaperSearchQuery(BaseModel):
    __root__: Annotated[  # type: ignore[misc]
    Union[
        and_int,  # type: ignore[misc]
        or_int,  # type: ignore[misc]
        Title,
        AuthorName,
        Journal,
        Abstract,
        Institution,
        Keyword,
        Year],
    Field(discriminator='tag')]

and_int.update_forward_refs()
or_int.update_forward_refs()
PubMedPaperSearchQuery.update_forward_refs()

#class PubMedPaperSearchQuery(BaseModel):
#    term: str


class PubMedAuthorSearchQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedPaperDetailsQuery(BaseModel):
    pubmed_ids: List[str]


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
            List[PaperData], PubMedPaperSearchQuery, List[PubMedPaperData]]):
    def _query_to_native(self, query: PaperSearchQuery) -> PubMedPaperSearchQuery:
        query = query.dict()['__root__']
        return PubMedPaperSearchQuery.parse_obj(query)


    def _run_native_query(self, query: PubMedPaperSearchQuery) -> List[PubMedPaperData]:        
        def get_linked_papers_given_url(id_list, linkname):
            unique_ref_fetch_list, id_mapper = get_linked_paper_ids(id_list, linkname)

            ref_papers = papers_from_id_list(unique_ref_fetch_list)
            ref_paper_index = {i.pubmed_id: i for i in ref_papers}

            id_mapper_papers = {}
            for search_id, id_list in id_mapper.items():
                if id_list is not None:
                    sub_papers = []
                    for sub_id in id_list:
                        paper = ref_paper_index[sub_id]
                        sub_papers.append(paper)
                    id_mapper_papers[search_id] = sub_papers
                else:
                    id_mapper_papers[search_id] = None
            return id_mapper_papers


        id_list = get_id_list_from_query(query)
        print(len(id_list))
        papers = papers_from_id_list(id_list)
        references_set = get_linked_papers_given_url(id_list, 'pubmed_pubmed_refs')
        cited_by_set = get_linked_papers_given_url(id_list, 'pubmed_pubmed_citedin')

        for paper in papers:
            pubmed_id = paper.pubmed_id
            paper.references = references_set[pubmed_id]
            paper.cited_by = cited_by_set[pubmed_id]
            #pprint(paper.dict())

        return papers

    def _post_process(self, query: PaperSearchQuery, data: List[PubMedPaperData]) -> List[PubMedPaperData]:
        # TODO: implement this
        pass

    def _data_from_native(self, data: List[PubMedPaperData]) -> List[PaperData]:
        return [paper_from_native(datum) for datum in data]


class AuthorSearchQueryEngine(
        SlightlyLessAbstractQueryEngine[AuthorSearchQuery,
            List[AuthorData], PubMedAuthorSearchQuery, List[PubMedAuthorData]]):
    def _query_to_native(self, query: AuthorSearchQuery) -> PubMedAuthorSearchQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedAuthorSearchQuery) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _post_process(self, query: AuthorSearchQuery, data: List[PubMedAuthorData]) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _data_from_native(self, data: List[PubMedAuthorData]) -> List[AuthorData]:
        # TODO: implement this
        pass


class PaperDetailsQueryEngine(
        SlightlyLessAbstractQueryEngine[PaperDetailsQuery,
            PaperData, PubMedPaperDetailsQuery, PubMedPaperData]):
    def _query_to_native(self, query: PaperDetailsQuery) -> PubMedPaperDetailsQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedPaperDetailsQuery) -> PubMedPaperData:
        # TODO: implement this
        pass

    def _post_process(self, query: PaperDetailsQuery, data: PubMedPaperData) -> PubMedPaperData:
        # TODO: implement this
        pass

    def _data_from_native(self, data: PubMedPaperData) -> PaperData:
        return paper_from_native(data)


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
